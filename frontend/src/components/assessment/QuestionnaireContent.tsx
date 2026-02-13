"use client";

import { useEffect, useState } from "react";
import {
  Loader2,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Tag,
  FileText,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { supabase } from "@/lib/supabase";
import type {
  QuestionnaireComplete,
  QuestionnaireSessionDetail,
  ControlQuestions,
} from "@/types/questionnaire";
import { ConversationalFlow } from "./questionnaire";

interface QuestionnaireContentProps {
  projectId: string;
  frameworks: string[];
  assessmentId?: string;
}

// ── Main Component ───────────────────────────────────────────────────

export function QuestionnaireContent({
  projectId,
  // frameworks is resolved server-side by the conversational agent
  assessmentId,
}: QuestionnaireContentProps) {
  const [isLoadingPrevious, setIsLoadingPrevious] = useState(false);
  const [result, setResult] = useState<QuestionnaireComplete | null>(null);
  const [expandedControls, setExpandedControls] = useState<Set<string>>(
    new Set(),
  );

  // Load previous session on mount if assessment has one
  useEffect(() => {
    if (!assessmentId) return;

    let cancelled = false;
    async function loadPreviousSession() {
      setIsLoadingPrevious(true);
      try {
        const apiUrl =
          process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
        const headers = await getAuthHeaders();
        const params = new URLSearchParams({
          project_id: projectId,
          assessment_id: assessmentId!,
        });
        const res = await fetch(
          `${apiUrl}/questionnaire/sessions?${params}`,
          { headers },
        );
        if (!res.ok) return;

        const sessions: Array<{ id: string; status: string }> =
          await res.json();
        const completed = sessions.find((s) => s.status === "completed");
        if (!completed || cancelled) return;

        // Fetch full session with generated questions
        const detailRes = await fetch(
          `${apiUrl}/questionnaire/sessions/${completed.id}`,
          { headers },
        );
        if (!detailRes.ok || cancelled) return;

        const detail: QuestionnaireSessionDetail = await detailRes.json();
        setResult({
          session_id: detail.id,
          type: "complete",
          controls: detail.generated_questions,
          total_controls: detail.total_controls,
          total_questions: detail.total_questions,
          generation_time_ms: detail.generation_time_ms,
          criteria_summary: detail.agent_criteria?.summary ?? "",
        });
      } catch {
        // Silently fail — user can still generate fresh questions
      } finally {
        if (!cancelled) setIsLoadingPrevious(false);
      }
    }

    loadPreviousSession();
    return () => {
      cancelled = true;
    };
  }, [assessmentId, projectId]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Helpers ─────────────────────────────────────────────────────────

  async function getAuthHeaders(): Promise<Record<string, string>> {
    const {
      data: { session },
    } = await supabase.auth.getSession();
    if (!session?.access_token) return {};
    return { Authorization: `Bearer ${session.access_token}` };
  }

  function toggleControl(controlId: string) {
    setExpandedControls((prev) => {
      const next = new Set(prev);
      if (next.has(controlId)) next.delete(controlId);
      else next.add(controlId);
      return next;
    });
  }

  function getPriorityColor(priority: string) {
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
  }

  // ── Loading previous session ──────────────────────────────────────

  if (isLoadingPrevious) {
    return (
      <div className="flex items-center justify-center py-16 text-slate-400 gap-3">
        <Loader2 className="h-5 w-5 animate-spin" />
        <span className="text-sm">
          Checking for previous questionnaire...
        </span>
      </div>
    );
  }

  // ── Result view ───────────────────────────────────────────────────

  if (result) {
    return (
      <div className="space-y-6">
        {/* Summary banner */}
        <div className="bg-[#0f1016]/60 backdrop-blur-md border border-emerald-500/20 rounded-2xl p-6">
          <div className="flex items-start gap-4">
            <div className="p-3 bg-emerald-500/10 rounded-lg">
              <CheckCircle2 className="h-6 w-6 text-emerald-400" />
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-white mb-1">
                Questionnaire Complete
              </h3>
              <p className="text-sm text-slate-400 mb-3">
                Generated {result.total_questions} questions across{" "}
                {result.total_controls} controls in{" "}
                {(result.generation_time_ms / 1000).toFixed(1)}s
              </p>
              <p className="text-sm text-slate-300">
                {result.criteria_summary}
              </p>
            </div>
          </div>
        </div>

        {/* Controls accordion */}
        <div className="space-y-3">
          {result.controls.map((control) => (
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

  // ── Conversational flow (replaces the old wizard) ─────────────────

  return (
    <ConversationalFlow
      projectId={projectId}
      assessmentId={assessmentId}
      onComplete={setResult}
    />
  );
}

// ── Sub-components ───────────────────────────────────────────────────

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
              </div>
              {q.expected_evidence && (
                <p className="text-xs text-slate-500">
                  <span className="text-slate-400 font-medium">
                    Expected evidence:
                  </span>{" "}
                  {q.expected_evidence}
                </p>
              )}
              {q.guidance_notes && (
                <p className="text-xs text-slate-500">
                  <span className="text-slate-400 font-medium">
                    Guidance:
                  </span>{" "}
                  {q.guidance_notes}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
