"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { supabase } from "@/lib/supabase";
import type {
  AgentQuestion,
  GenerateWithCriteriaRequest,
  QuestionnaireComplete,
  QuestionnaireResponse,
} from "@/types/questionnaire";

// ── Types ────────────────────────────────────────────────────────────

export type AgentState =
  | "idle"
  | "starting"
  | "conversing"
  | "generating"
  | "complete"
  | "error";

export interface QAEntry {
  question: string;
  context?: string | null;
  options?: string[] | null;
  answer: string;
}

export interface GenerationProgress {
  batch: number;
  total: number;
  controlsDone: number;
  totalControls: number;
}

interface UseQuestionnaireAgentReturn {
  state: AgentState;
  currentQuestion: AgentQuestion | null;
  answeredQuestions: QAEntry[];
  result: QuestionnaireComplete | null;
  error: string | null;
  progress: GenerationProgress | null;
  startSession: (projectId: string, assessmentId?: string) => Promise<void>;
  generateWithCriteria: (
    criteria: GenerateWithCriteriaRequest,
  ) => Promise<void>;
  submitAnswer: (answer: string) => Promise<void>;
  retry: () => void;
  reset: () => void;
}

// ── Helpers ──────────────────────────────────────────────────────────

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

async function getAuthHeaders(): Promise<Record<string, string>> {
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session?.access_token) return {};
  return { Authorization: `Bearer ${session.access_token}` };
}

async function post<T>(
  path: string,
  body: Record<string, unknown>,
  signal?: AbortSignal,
): Promise<T> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify(body),
    signal,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Request failed: ${res.status}`);
  }

  return res.json();
}

// ── Hook ─────────────────────────────────────────────────────────────

export function useQuestionnaireAgent(): UseQuestionnaireAgentReturn {
  const [state, setState] = useState<AgentState>("idle");
  const [currentQuestion, setCurrentQuestion] = useState<AgentQuestion | null>(
    null,
  );
  const [answeredQuestions, setAnsweredQuestions] = useState<QAEntry[]>([]);
  const [result, setResult] = useState<QuestionnaireComplete | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<GenerationProgress | null>(null);

  // Track the session_id returned by the agent
  const sessionIdRef = useRef<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  // Store params for retry
  const paramsRef = useRef<{ projectId: string; assessmentId?: string } | null>(
    null,
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  // Handle a response from the agent (either question or complete)
  const handleResponse = useCallback((data: QuestionnaireResponse) => {
    if (data.type === "question") {
      sessionIdRef.current = data.session_id;
      setCurrentQuestion(data);
      setState("conversing");
    } else {
      sessionIdRef.current = data.session_id;
      setResult(data);
      setCurrentQuestion(null);
      setState("complete");
    }
  }, []);

  const startSession = useCallback(
    async (projectId: string, assessmentId?: string) => {
      paramsRef.current = { projectId, assessmentId };
      setState("starting");
      setError(null);
      setCurrentQuestion(null);
      setAnsweredQuestions([]);
      setResult(null);
      sessionIdRef.current = null;

      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const data = await post<QuestionnaireResponse>(
          "/questionnaire/generate-question",
          {
            project_id: projectId,
            assessment_id: assessmentId ?? null,
          },
          controller.signal,
        );
        handleResponse(data);
      } catch (e) {
        if (controller.signal.aborted) return; // cancelled by unmount or new request
        setError(
          e instanceof Error ? e.message : "Failed to start session",
        );
        setState("error");
      }
    },
    [handleResponse],
  );

  const submitAnswer = useCallback(
    async (answer: string) => {
      if (!sessionIdRef.current || !currentQuestion) return;

      // Archive current Q&A
      setAnsweredQuestions((prev) => [
        ...prev,
        {
          question: currentQuestion.question,
          context: currentQuestion.context,
          options: currentQuestion.options,
          answer,
        },
      ]);
      setCurrentQuestion(null);
      setState("generating");

      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const data = await post<QuestionnaireResponse>(
          "/questionnaire/respond",
          {
            session_id: sessionIdRef.current,
            answer,
          },
          controller.signal,
        );
        handleResponse(data);
      } catch (e) {
        if (controller.signal.aborted) return; // cancelled by unmount or new request
        setError(e instanceof Error ? e.message : "Failed to submit answer");
        setState("error");
      }
    },
    [currentQuestion, handleResponse],
  );

  const generateWithCriteria = useCallback(
    async (criteria: GenerateWithCriteriaRequest) => {
      setState("generating");
      setError(null);
      setResult(null);
      setProgress(null);

      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const headers = await getAuthHeaders();
        const res = await fetch(
          `${API_URL}/questionnaire/generate-with-criteria-stream`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json", ...headers },
            body: JSON.stringify(criteria),
            signal: controller.signal,
          },
        );

        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(
            err.detail || `Request failed: ${res.status}`,
          );
        }

        const reader = res.body?.getReader();
        if (!reader) throw new Error("No response stream");

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          // Keep incomplete last line in buffer
          buffer = lines.pop() ?? "";

          let currentEvent = "";
          for (const line of lines) {
            if (line.startsWith("event: ")) {
              currentEvent = line.slice(7).trim();
            } else if (line.startsWith("data: ")) {
              const data = JSON.parse(line.slice(6));
              if (currentEvent === "progress") {
                setProgress({
                  batch: data.batch,
                  total: data.total,
                  controlsDone: data.controls_done,
                  totalControls: data.total_controls,
                });
              } else if (currentEvent === "complete") {
                setResult(data);
                setProgress(null);
                setState("complete");
              } else if (currentEvent === "error") {
                throw new Error(data.error || "Generation failed");
              }
              currentEvent = "";
            }
          }
        }
      } catch (e) {
        if (controller.signal.aborted) return;
        setError(
          e instanceof Error ? e.message : "Failed to generate questions",
        );
        setState("error");
      }
    },
    [],
  );

  const retry = useCallback(() => {
    if (paramsRef.current) {
      startSession(
        paramsRef.current.projectId,
        paramsRef.current.assessmentId,
      );
    }
  }, [startSession]);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setState("idle");
    setCurrentQuestion(null);
    setAnsweredQuestions([]);
    setResult(null);
    setError(null);
    setProgress(null);
    sessionIdRef.current = null;
  }, []);

  return {
    state,
    currentQuestion,
    answeredQuestions,
    result,
    error,
    progress,
    startSession,
    generateWithCriteria,
    submitAnswer,
    retry,
    reset,
  };
}
