"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { supabase } from "@/lib/supabase";
import type {
  AgentQuestion,
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

interface UseQuestionnaireAgentReturn {
  state: AgentState;
  currentQuestion: AgentQuestion | null;
  answeredQuestions: QAEntry[];
  result: QuestionnaireComplete | null;
  error: string | null;
  startSession: (projectId: string, assessmentId?: string) => Promise<void>;
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
    sessionIdRef.current = null;
  }, []);

  return {
    state,
    currentQuestion,
    answeredQuestions,
    result,
    error,
    startSession,
    submitAnswer,
    retry,
    reset,
  };
}
