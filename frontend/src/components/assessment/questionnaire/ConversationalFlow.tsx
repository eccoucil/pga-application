"use client";

import { useEffect, useRef } from "react";
import { Loader2, Sparkles, AlertCircle, RefreshCw } from "lucide-react";
import { useQuestionnaireAgent } from "@/hooks/use-questionnaire-agent";
import type { QuestionnaireComplete } from "@/types/questionnaire";
import { QuestionCard } from "./QuestionCard";
import { AnsweredQuestionCard } from "./AnsweredQuestionCard";
import { QuestionnaireProgress } from "./QuestionnaireProgress";

interface ConversationalFlowProps {
  projectId: string;
  assessmentId?: string;
  onComplete: (result: QuestionnaireComplete) => void;
}

export function ConversationalFlow({
  projectId,
  assessmentId,
  onComplete,
}: ConversationalFlowProps) {
  const {
    state,
    currentQuestion,
    answeredQuestions,
    result,
    error,
    startSession,
    submitAnswer,
    retry,
  } = useQuestionnaireAgent();

  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-start session on mount
  useEffect(() => {
    startSession(projectId, assessmentId);
  }, [projectId, assessmentId, startSession]);

  // Notify parent when generation completes
  useEffect(() => {
    if (result) onComplete(result);
  }, [result, onComplete]);

  // Auto-scroll to the latest question
  useEffect(() => {
    if (currentQuestion || state === "generating") {
      bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [currentQuestion, state]);

  const isLoading = state === "starting" || state === "generating";

  return (
    <div className="bg-[#0f1016]/60 backdrop-blur-md border border-white/10 rounded-2xl overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-white/10 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Sparkles className="w-5 h-5 text-purple-400" />
          <h3 className="text-sm font-semibold text-white">
            AI Questionnaire Assistant
          </h3>
        </div>
        <QuestionnaireProgress
          answeredCount={answeredQuestions.length}
          isComplete={state === "complete"}
          state={state}
        />
      </div>

      <div className="p-6 space-y-3">
        {/* Starting state */}
        {state === "starting" && answeredQuestions.length === 0 && (
          <div className="flex items-center justify-center py-12 text-slate-400 gap-3">
            <Loader2 className="h-5 w-5 animate-spin text-purple-400" />
            <span className="text-sm">
              Analyzing project context and preparing questions...
            </span>
          </div>
        )}

        {/* Answered question cards */}
        {answeredQuestions.map((entry, i) => (
          <AnsweredQuestionCard key={i} entry={entry} index={i} />
        ))}

        {/* Active question card */}
        {currentQuestion && state === "conversing" && (
          <QuestionCard
            question={currentQuestion}
            questionNumber={answeredQuestions.length + 1}
            onSubmit={submitAnswer}
          />
        )}

        {/* Generating state (between questions or final generation) */}
        {state === "generating" && (
          <div className="flex items-center justify-center py-8 text-slate-400 gap-3">
            <Loader2 className="h-5 w-5 animate-spin text-purple-400" />
            <span className="text-sm">
              {answeredQuestions.length < 2
                ? "Processing your response..."
                : "Generating tailored compliance questions..."}
            </span>
          </div>
        )}

        {/* Error state */}
        {state === "error" && error && (
          <div className="bg-red-500/5 border border-red-500/20 rounded-xl p-5">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-400 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <p className="text-sm text-red-300">{error}</p>
                <button
                  type="button"
                  onClick={retry}
                  className="mt-3 flex items-center gap-2 px-4 py-2 text-sm font-medium bg-white/5 border border-white/10 rounded-lg text-slate-300 hover:bg-white/10 hover:text-white transition-colors"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  Try Again
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Scroll anchor */}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
