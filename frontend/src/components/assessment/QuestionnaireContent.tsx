"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { supabase } from "@/lib/supabase";
import type {
  QuestionnaireComplete,
  QuestionnaireSessionDetail,
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

  // ── Unified view: Conversational flow + inline results ──────────────

  return (
    <ConversationalFlow
      projectId={projectId}
      assessmentId={assessmentId}
      onComplete={setResult}
      previousResult={result}
    />
  );
}

