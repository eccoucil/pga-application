"use client";

import React, { useEffect, useRef } from "react";
import { Loader2, Sparkles, AlertCircle, RefreshCw, CheckCircle2, ChevronDown, ChevronUp, Tag, FileText } from "lucide-react";
import { cn } from "@/lib/utils";
import { useQuestionnaireAgent } from "@/hooks/use-questionnaire-agent";
import type { AgentStatus } from "@/hooks/use-questionnaire-agent";
import type { QuestionnaireComplete, ControlQuestions } from "@/types/questionnaire";
import { QuestionCard } from "./QuestionCard";
import { AnsweredQuestionCard } from "./AnsweredQuestionCard";
import { QuestionnaireProgress } from "./QuestionnaireProgress";

interface ConversationalFlowProps {
  projectId: string;
  assessmentId?: string;
  onComplete: (result: QuestionnaireComplete) => void;
  previousResult?: QuestionnaireComplete | null;
}

export function ConversationalFlow({
  projectId,
  assessmentId,
  onComplete,
  previousResult,
}: ConversationalFlowProps) {
  const {
    state,
    currentQuestion,
    answeredQuestions,
    result,
    error,
    progress,
    agentProgress,
    streamingControls,
    startSession,
    submitAnswer,
    retry,
  } = useQuestionnaireAgent();

  const bottomRef = useRef<HTMLDivElement>(null);
  const questionCardRef = useRef<HTMLDivElement>(null);

  // Auto-start session on mount (skip if previous result already loaded)
  useEffect(() => {
    if (previousResult) return;
    startSession(projectId, assessmentId);
  }, [projectId, assessmentId, startSession, previousResult]);

  // Notify parent when generation completes
  useEffect(() => {
    if (result) onComplete(result);
  }, [result, onComplete]);

  // Auto-scroll to the active question or generation status
  useEffect(() => {
    if (currentQuestion) {
      questionCardRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    } else if (state === "generating") {
      bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [currentQuestion, state]);

  const isLoading = state === "starting" || state === "generating";

  // Helper to determine priority color
  const getPriorityColor = (priority: string) => {
    switch (priority.toLowerCase()) {
      case "high":
        return "bg-red-500/10 text-red-400 border-red-500/20";
      case "medium":
        return "bg-amber-500/10 text-amber-400 border-amber-500/20";
      case "low":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
      default:
        return "bg-slate-500/10 text-slate-400 border-slate-500/20";
    }
  };

  // Use previousResult if available, otherwise use the result from the current session
  const displayResult = previousResult || result;

  return (
    <div className="space-y-6">
      {/* Streaming Questions Panel - shows controls as each agent completes */}
      {state === "generating" && streamingControls.length > 0 && (
        <GeneratedQuestionsPanel
          controls={streamingControls}
          getPriorityColor={getPriorityColor}
          showCompletionBanner={false}
          isStreaming
        />
      )}

      {/* Generated Questions Panel - shown first if we have a previous result or early completion */}
      {displayResult && displayResult.controls && displayResult.controls.length > 0 && (state === "idle" || state === "complete") && (
        <GeneratedQuestionsPanel
          controls={displayResult.controls}
          getPriorityColor={getPriorityColor}
          showCompletionBanner={state === "complete"}
          totalQuestions={displayResult.total_questions}
          totalControls={displayResult.total_controls}
          generationTimeMs={displayResult.generation_time_ms}
        />
      )}

      {/* Conversation Panel */}
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
            <div ref={questionCardRef}>
              <QuestionCard
                question={currentQuestion}
                questionNumber={answeredQuestions.length + 1}
                onSubmit={submitAnswer}
              />
            </div>
          )}

          {/* Generating state (between questions or final generation) */}
          {state === "generating" && (
            <div className="py-8 space-y-4">
              <div className="flex items-center justify-center text-slate-400 gap-3">
                <Loader2 className="h-5 w-5 animate-spin text-purple-400" />
                <span className="text-sm">
                  {!progress
                    ? answeredQuestions.length < 2
                      ? "Processing your response..."
                      : "Generating tailored compliance questions..."
                    : progress.totalAgents
                      ? `Generating questions... ${progress.agentsComplete ?? 0}/${progress.totalAgents} agents complete (${progress.controlsDone} controls)`
                      : `Generating questions... Batch ${progress.batch}/${progress.total} (${progress.controlsDone} controls processed)`}
                </span>
              </div>

              {/* Overall progress bar */}
              {progress && progress.total > 0 && (
                <div className="mx-auto max-w-md space-y-2">
                  <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-purple-500 to-cyan-500 rounded-full transition-all duration-500 ease-out"
                      style={{
                        width: `${Math.round((progress.batch / progress.total) * 100)}%`,
                      }}
                    />
                  </div>
                  <p className="text-xs text-slate-500 text-center">
                    {progress.controlsDone} / {progress.totalControls} controls
                  </p>
                </div>
              )}

              {/* Per-agent progress grid */}
              {agentProgress.size > 0 && (
                <div className="mx-auto max-w-lg grid grid-cols-2 gap-2 mt-3">
                  {Array.from(agentProgress.values()).map((agent) => (
                    <div
                      key={agent.agentId}
                      className="flex items-center gap-2 px-3 py-2 bg-white/[0.03] border border-white/[0.06] rounded-lg"
                    >
                      {agent.status === "complete" ? (
                        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 flex-shrink-0" />
                      ) : agent.status === "failed" ? (
                        <AlertCircle className="h-3.5 w-3.5 text-red-400 flex-shrink-0" />
                      ) : (
                        <Loader2 className="h-3.5 w-3.5 animate-spin text-cyan-400 flex-shrink-0" />
                      )}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-medium text-slate-300 truncate">
                            {agent.label}
                          </span>
                          {agent.status === "complete" && (
                            <span className="text-[10px] text-slate-500 ml-1">
                              {agent.questionsGenerated}q
                            </span>
                          )}
                        </div>
                        <div className="h-1 bg-white/5 rounded-full overflow-hidden mt-1">
                          <div
                            className={`h-full rounded-full transition-all duration-500 ease-out ${
                              agent.status === "complete"
                                ? "bg-emerald-500"
                                : agent.status === "failed"
                                  ? "bg-red-500"
                                  : "bg-cyan-500/60 animate-pulse"
                            }`}
                            style={{
                              width: agent.status === "complete" ? "100%" : agent.status === "failed" ? "100%" : "60%",
                            }}
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
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

    </div>
  );
}

// Classify a control into a tab category based on control_id and framework
type TabKey = "annex-a" | "management" | "bnm-rmit";

function classifyControl(control: ControlQuestions): TabKey {
  if (control.framework.includes("BNM RMIT")) return "bnm-rmit";
  if (control.control_id.startsWith("A.")) return "annex-a";
  return "management";
}

const TAB_CONFIG: { key: TabKey; label: string }[] = [
  { key: "annex-a", label: "Annex A" },
  { key: "management", label: "Management Clauses" },
  { key: "bnm-rmit", label: "BNM RMIT" },
];

// New sub-component for displaying generated questions
function GeneratedQuestionsPanel({
  controls,
  getPriorityColor,
  showCompletionBanner = false,
  isStreaming = false,
  totalQuestions,
  totalControls,
  generationTimeMs,
}: {
  controls: ControlQuestions[];
  getPriorityColor: (priority: string) => string;
  showCompletionBanner?: boolean;
  isStreaming?: boolean;
  totalQuestions?: number;
  totalControls?: number;
  generationTimeMs?: number;
}) {
  const [expandedControls, setExpandedControls] = React.useState<Set<string>>(
    new Set(),
  );

  // Group controls by category
  const grouped = React.useMemo(() => {
    const groups: Record<TabKey, ControlQuestions[]> = {
      "annex-a": [],
      "management": [],
      "bnm-rmit": [],
    };
    for (const control of controls) {
      groups[classifyControl(control)].push(control);
    }
    return groups;
  }, [controls]);

  // Tabs that have controls
  const visibleTabs = React.useMemo(
    () => TAB_CONFIG.filter((t) => grouped[t.key].length > 0),
    [grouped],
  );

  const showTabs = visibleTabs.length >= 2;

  const [activeTab, setActiveTab] = React.useState<TabKey | null>(null);

  // Set default tab to first visible tab (only once, or when tabs first appear)
  React.useEffect(() => {
    if (visibleTabs.length > 0 && (activeTab === null || !visibleTabs.some((t) => t.key === activeTab))) {
      setActiveTab(visibleTabs[0].key);
    }
  }, [visibleTabs, activeTab]);

  const displayedControls = showTabs && activeTab ? grouped[activeTab] : controls;

  React.useEffect(() => {
    // Auto-expand first few controls on initial render
    if (controls.length > 0 && expandedControls.size === 0) {
      const firstFew = new Set(controls.slice(0, Math.min(2, controls.length)).map((c) => c.control_id));
      setExpandedControls(firstFew);
    }
  }, [controls, expandedControls.size]);

  const toggleControl = (controlId: string) => {
    setExpandedControls((prev) => {
      const next = new Set(prev);
      if (next.has(controlId)) next.delete(controlId);
      else next.add(controlId);
      return next;
    });
  };

  return (
    <div className="space-y-6">
      {/* Summary banner */}
      {showCompletionBanner && totalQuestions && totalControls && generationTimeMs && (
        <div className="bg-[#0f1016]/60 backdrop-blur-md border border-emerald-500/20 rounded-2xl p-6">
          <div className="flex items-start gap-4">
            <div className="p-3 bg-emerald-500/10 rounded-lg">
              <CheckCircle2 className="h-6 w-6 text-emerald-400" />
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-white mb-1">
                Questionnaire Complete
              </h3>
              <p className="text-sm text-slate-400 mb-2">
                Generated {totalQuestions} questions across {totalControls} controls in{" "}
                {(generationTimeMs / 1000).toFixed(1)}s
              </p>
            </div>
          </div>
        </div>
      )}

      {isStreaming && (
        <div className="flex items-center gap-3 px-4 py-3 bg-cyan-500/5 border border-cyan-500/20 rounded-xl">
          <Loader2 className="h-4 w-4 animate-spin text-cyan-400 flex-shrink-0" />
          <span className="text-sm text-slate-400">
            Showing {controls.length} controls so far — more generating...
          </span>
        </div>
      )}

      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-white px-2 py-1">
          {showCompletionBanner ? "Compliance Questions" : "Generated Compliance Questions"}
        </h3>

        {/* Framework category tabs */}
        {showTabs && (
          <div className="flex gap-2 px-2">
            {visibleTabs.map((tab) => (
              <button
                key={tab.key}
                type="button"
                onClick={() => setActiveTab(tab.key)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === tab.key
                    ? "bg-purple-500/20 text-purple-300 border border-purple-500/30"
                    : "text-slate-400 hover:text-white hover:bg-slate-800 border border-transparent"
                }`}
              >
                {tab.label}
                <span className="ml-2 px-1.5 py-0.5 text-xs rounded-full bg-white/10">
                  {grouped[tab.key].length}
                </span>
              </button>
            ))}
          </div>
        )}

        {displayedControls.map((control) => (
          <ControlCard
            key={control.control_id}
            control={control}
            expanded={expandedControls.has(control.control_id)}
            onToggle={() => toggleControl(control.control_id)}
            getPriorityColor={getPriorityColor}
          />
        ))}
      </div>
    </div>
  );
}

function ControlCard({
  control,
  expanded,
  onToggle,
  getPriorityColor,
}: {
  control: ControlQuestions;
  expanded: boolean;
  onToggle: () => void;
  getPriorityColor: (priority: string) => string;
}) {
  return (
    <div className="bg-[#0f1016]/60 backdrop-blur-md border border-white/10 rounded-2xl overflow-hidden">
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex items-center justify-between px-6 py-4 hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-3 text-left">
          <FileText className="w-4 h-4 text-purple-400 flex-shrink-0" />
          <div>
            <span className="text-sm font-medium text-white">
              {control.control_id}
            </span>
            <span className="text-sm text-slate-400 ml-2">
              {control.control_title}
            </span>
          </div>
          <span className="px-2 py-0.5 bg-purple-500/10 text-purple-300 text-xs rounded-full border border-purple-500/20">
            {control.framework}
          </span>
          <span className="px-2 py-0.5 bg-slate-500/10 text-slate-400 text-xs rounded-full border border-slate-500/20">
            {control.questions.length} Q
          </span>
        </div>
        {expanded ? (
          <ChevronUp className="w-4 h-4 text-slate-400 flex-shrink-0" />
        ) : (
          <ChevronDown className="w-4 h-4 text-slate-400 flex-shrink-0" />
        )}
      </button>

      {expanded && (
        <div className="px-6 pb-4 space-y-3 border-t border-white/10 pt-4">
          {control.questions.map((q) => (
            <div
              key={q.id}
              className="p-4 bg-black/30 rounded-lg border border-white/5 space-y-2"
            >
              <p className="text-sm text-white leading-relaxed">
                {q.question}
              </p>
              <div className="flex flex-wrap gap-2">
                <span
                  className={cn(
                    "px-2 py-0.5 text-xs rounded border font-medium",
                    getPriorityColor(q.priority),
                  )}
                >
                  {q.priority}
                </span>
                <span className="px-2 py-0.5 bg-slate-500/10 text-slate-400 text-xs rounded border border-slate-500/20 flex items-center gap-1">
                  <Tag className="w-3 h-3" />
                  {q.category}
                </span>
                {q.expected_evidence && (
                  <span className="px-2 py-0.5 bg-blue-500/10 text-blue-400 text-xs rounded border border-blue-500/20 flex items-center gap-1">
                    <FileText className="w-3 h-3" />
                    {q.expected_evidence}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
