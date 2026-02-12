"use client";

import { useEffect, useState } from "react";
import {
  Loader2,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Tag,
  FileText,
  ArrowRight,
  ArrowLeft,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { supabase } from "@/lib/supabase";
import { Checkbox } from "@/components/ui/checkbox";
import type {
  QuestionnaireComplete,
  QuestionnaireSessionDetail,
  ControlQuestions,
} from "@/types/questionnaire";

interface QuestionnaireContentProps {
  projectId: string;
  frameworks: string[];
  assessmentId?: string;
}

// ── Option definitions ───────────────────────────────────────────────

const MATURITY_OPTIONS = [
  {
    value: "first_time_audit",
    label: "First-time Audit",
    description: "Basic policy existence and documentation focus",
  },
  {
    value: "recurring_assessment",
    label: "Recurring Assessment",
    description: "Implementation effectiveness and monitoring",
  },
  {
    value: "mature_isms",
    label: "Mature ISMS",
    description: "Continuous improvement and advanced effectiveness",
  },
] as const;

const DEPTH_OPTIONS = [
  {
    value: "high_level_overview",
    label: "High-level Overview",
    description: "2 questions per control",
  },
  {
    value: "balanced",
    label: "Balanced",
    description: "3 questions per control",
  },
  {
    value: "detailed_technical",
    label: "Detailed Technical",
    description: "4-5 questions per control",
  },
] as const;

const DOMAIN_GROUPS = [
  {
    framework: "ISO 27001:2022",
    domains: [
      "A.5 Organizational Controls",
      "A.6 People Controls",
      "A.7 Physical Controls",
      "A.8 Technological Controls",
      "Clauses 4-10 (Management)",
    ],
  },
  {
    framework: "BNM RMIT",
    domains: [
      "Governance",
      "Technology Risk Management",
      "Technology Operations Management",
      "Cybersecurity Management",
      "Digital Services",
      "Technology Audits",
      "External Party Assurance",
      "Security Awareness and Education",
      "Notification for Technology-Related Applications",
      "Consultation and Notification Related to Cloud Services and Emerging Technology",
      "Assessment and Gap Analysis",
    ],
  },
];

// ── Main Component ───────────────────────────────────────────────────

type WizardStep = 1 | 2 | 3;

export function QuestionnaireContent({ projectId, frameworks, assessmentId }: QuestionnaireContentProps) {
  // Filter domain groups to only show frameworks the project uses
  const filteredDomainGroups = DOMAIN_GROUPS.filter(
    (g) => frameworks.length === 0 || frameworks.includes(g.framework),
  );
  // Wizard state
  const [wizardStep, setWizardStep] = useState<WizardStep>(1);
  const [maturityLevel, setMaturityLevel] = useState("");
  const [questionDepth, setQuestionDepth] = useState("");
  const [priorityDomains, setPriorityDomains] = useState<Set<string>>(
    new Set(),
  );
  const [complianceConcerns, setComplianceConcerns] = useState("");
  const [controlsToSkip, setControlsToSkip] = useState("");

  // Generation state
  const [isGenerating, setIsGenerating] = useState(false);
  const [isLoadingPrevious, setIsLoadingPrevious] = useState(false);
  const [error, setError] = useState<string | null>(null);
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
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
        const headers = await getAuthHeaders();
        const params = new URLSearchParams({
          project_id: projectId,
          assessment_id: assessmentId!,
        });
        const res = await fetch(`${apiUrl}/questionnaire/sessions?${params}`, {
          headers,
        });
        if (!res.ok) return;

        const sessions: Array<{ id: string; status: string }> = await res.json();
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
    return () => { cancelled = true; };
  }, [assessmentId, projectId]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Helpers ─────────────────────────────────────────────────────────

  async function getAuthHeaders(): Promise<Record<string, string>> {
    const {
      data: { session },
    } = await supabase.auth.getSession();
    if (!session?.access_token) return {};
    return { Authorization: `Bearer ${session.access_token}` };
  }

  function toggleDomain(domain: string) {
    setPriorityDomains((prev) => {
      const next = new Set(prev);
      if (next.has(domain)) next.delete(domain);
      else next.add(domain);
      return next;
    });
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

  const maturityLabel =
    MATURITY_OPTIONS.find((o) => o.value === maturityLevel)?.label ?? "";
  const depthLabel =
    DEPTH_OPTIONS.find((o) => o.value === questionDepth)?.label ?? "";

  // ── API call ────────────────────────────────────────────────────────

  async function handleGenerate() {
    setIsGenerating(true);
    setError(null);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 300_000); // 5 minutes

    try {
      const apiUrl =
        process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
      const headers = await getAuthHeaders();
      const res = await fetch(`${apiUrl}/questionnaire/generate-with-criteria`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...headers },
        body: JSON.stringify({
          project_id: projectId,
          assessment_id: assessmentId ?? null,
          maturity_level: maturityLevel,
          question_depth: questionDepth,
          priority_domains: Array.from(priorityDomains),
          compliance_concerns: complianceConcerns.trim() || null,
          controls_to_skip: controlsToSkip.trim() || null,
        }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(
          err.detail || `Failed to generate questions: ${res.status}`,
        );
      }

      const data: QuestionnaireComplete = await res.json();
      setResult(data);
    } catch (e) {
      clearTimeout(timeoutId);
      if (e instanceof DOMException && e.name === "AbortError") {
        setError(
          "Generation timed out after 5 minutes. Try high-level depth or fewer frameworks.",
        );
      } else {
        setError(
          e instanceof Error ? e.message : "Failed to generate questions",
        );
      }
    } finally {
      setIsGenerating(false);
    }
  }

  // ── Loading previous session ────────────────────────────────────────

  if (isLoadingPrevious) {
    return (
      <div className="flex items-center justify-center py-16 text-slate-400 gap-3">
        <Loader2 className="h-5 w-5 animate-spin" />
        <span className="text-sm">Checking for previous questionnaire...</span>
      </div>
    );
  }

  // ── Result view ─────────────────────────────────────────────────────

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

  // ── Generating overlay ──────────────────────────────────────────────

  if (isGenerating) {
    return (
      <div className="bg-[#0f1016]/60 backdrop-blur-md border border-white/10 rounded-2xl p-12 flex flex-col items-center justify-center gap-4">
        <Loader2 className="h-10 w-10 text-purple-400 animate-spin" />
        <div className="text-center">
          <p className="text-white font-medium">
            Generating compliance questions...
          </p>
          <p className="text-sm text-slate-400 mt-1">
            This may take 2-5 minutes depending on the number of controls
            and depth
          </p>
        </div>
      </div>
    );
  }

  // ── Wizard ──────────────────────────────────────────────────────────

  return (
    <div className="bg-[#0f1016]/60 backdrop-blur-md border border-white/10 rounded-2xl overflow-hidden">
      {/* Step indicator */}
      <div className="px-6 py-4 border-b border-white/10 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Sparkles className="w-5 h-5 text-purple-400" />
          <h3 className="text-sm font-semibold text-white">
            Questionnaire Criteria
          </h3>
        </div>
        <div className="flex items-center gap-2">
          {([1, 2, 3] as const).map((step) => (
            <div
              key={step}
              className={cn(
                "w-2.5 h-2.5 rounded-full transition-colors",
                step === wizardStep
                  ? "bg-purple-500"
                  : step < wizardStep
                    ? "bg-emerald-500"
                    : "bg-white/20",
              )}
            />
          ))}
        </div>
      </div>

      <div className="p-6">
        {/* ── Step 1: Assessment Profile ──────────────────────────── */}
        {wizardStep === 1 && (
          <div className="space-y-6">
            {/* Maturity Level */}
            <div>
              <label className="block text-sm font-medium text-white mb-3">
                Assessment Maturity Level
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {MATURITY_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setMaturityLevel(opt.value)}
                    className={cn(
                      "p-4 rounded-xl border text-left transition-all",
                      maturityLevel === opt.value
                        ? "border-purple-500/50 bg-purple-500/10 shadow-[0_0_15px_rgba(168,85,247,0.15)]"
                        : "border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/[0.07]",
                    )}
                  >
                    <p className="text-sm font-medium text-white">
                      {opt.label}
                    </p>
                    <p className="text-xs text-slate-400 mt-1">
                      {opt.description}
                    </p>
                  </button>
                ))}
              </div>
            </div>

            {/* Question Depth */}
            <div>
              <label className="block text-sm font-medium text-white mb-3">
                Question Depth
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {DEPTH_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setQuestionDepth(opt.value)}
                    className={cn(
                      "p-4 rounded-xl border text-left transition-all",
                      questionDepth === opt.value
                        ? "border-purple-500/50 bg-purple-500/10 shadow-[0_0_15px_rgba(168,85,247,0.15)]"
                        : "border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/[0.07]",
                    )}
                  >
                    <p className="text-sm font-medium text-white">
                      {opt.label}
                    </p>
                    <p className="text-xs text-slate-400 mt-1">
                      {opt.description}
                    </p>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ── Step 2: Focus & Priorities ──────────────────────────── */}
        {wizardStep === 2 && (
          <div className="space-y-6">
            {/* Priority Domains */}
            <div>
              <label className="block text-sm font-medium text-white mb-1">
                Priority Focus Areas
              </label>
              <p className="text-xs text-slate-400 mb-4">
                Select domains to emphasize. Leave empty to weight all equally.
              </p>
              <div className="space-y-5">
                {filteredDomainGroups.map((group) => (
                  <div key={group.framework}>
                    <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">
                      {group.framework}
                    </p>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {group.domains.map((domain) => (
                        <label
                          key={domain}
                          className={cn(
                            "flex items-center gap-3 px-3 py-2.5 rounded-lg border cursor-pointer transition-all",
                            priorityDomains.has(domain)
                              ? "border-purple-500/40 bg-purple-500/10"
                              : "border-white/10 bg-white/5 hover:border-white/20",
                          )}
                        >
                          <Checkbox
                            checked={priorityDomains.has(domain)}
                            onCheckedChange={() => toggleDomain(domain)}
                          />
                          <span className="text-sm text-slate-200">
                            {domain}
                          </span>
                        </label>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Compliance Concerns */}
            <div>
              <label className="block text-sm font-medium text-white mb-1">
                Specific Compliance Concerns
                <span className="text-slate-500 font-normal ml-1">
                  (optional)
                </span>
              </label>
              <textarea
                value={complianceConcerns}
                onChange={(e) => setComplianceConcerns(e.target.value)}
                placeholder="Any known gaps, risk areas, or specific concerns..."
                rows={3}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/25 resize-none transition-colors"
              />
            </div>

            {/* Controls to Skip */}
            <div>
              <label className="block text-sm font-medium text-white mb-1">
                Controls to De-emphasize
                <span className="text-slate-500 font-normal ml-1">
                  (optional)
                </span>
              </label>
              <textarea
                value={controlsToSkip}
                onChange={(e) => setControlsToSkip(e.target.value)}
                placeholder="Controls that are not applicable or already well-covered..."
                rows={2}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/25 resize-none transition-colors"
              />
            </div>
          </div>
        )}

        {/* ── Step 3: Review & Generate ───────────────────────────── */}
        {wizardStep === 3 && (
          <div className="space-y-4">
            <div>
              <h4 className="text-sm font-medium text-white mb-3">
                Review Your Criteria
              </h4>
              <div className="bg-black/30 rounded-xl border border-white/5 p-4 space-y-3">
                <SummaryRow label="Maturity Level" value={maturityLabel} />
                <SummaryRow label="Question Depth" value={depthLabel} />
                <SummaryRow
                  label="Priority Domains"
                  value={
                    priorityDomains.size > 0
                      ? Array.from(priorityDomains).join(", ")
                      : "All domains weighted equally"
                  }
                />
                {complianceConcerns.trim() && (
                  <SummaryRow
                    label="Concerns"
                    value={complianceConcerns.trim()}
                  />
                )}
                {controlsToSkip.trim() && (
                  <SummaryRow
                    label="De-emphasized"
                    value={controlsToSkip.trim()}
                  />
                )}
              </div>
            </div>

            {error && (
              <div className="px-4 py-3 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-300">
                {error}
              </div>
            )}
          </div>
        )}

        {/* ── Navigation ─────────────────────────────────────────── */}
        <div className="flex items-center justify-between mt-6 pt-4 border-t border-white/10">
          {wizardStep > 1 ? (
            <button
              type="button"
              onClick={() => setWizardStep((s) => (s - 1) as WizardStep)}
              className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-slate-300 hover:text-white transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              Back
            </button>
          ) : (
            <div />
          )}

          {wizardStep < 3 ? (
            <button
              type="button"
              onClick={() => setWizardStep((s) => (s + 1) as WizardStep)}
              disabled={wizardStep === 1 && (!maturityLevel || !questionDepth)}
              className="flex items-center gap-2 px-5 py-2.5 text-sm font-medium bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white rounded-xl disabled:opacity-40 disabled:cursor-not-allowed transition-all"
            >
              Next
              <ArrowRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              type="button"
              onClick={handleGenerate}
              className="flex items-center gap-2 px-5 py-2.5 text-sm font-medium bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white rounded-xl transition-all"
            >
              <Sparkles className="w-4 h-4" />
              Generate Questions
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Sub-components ───────────────────────────────────────────────────

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-3">
      <span className="text-xs font-medium text-slate-400 w-32 flex-shrink-0">
        {label}
      </span>
      <span className="text-sm text-slate-200">{value}</span>
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
              <p className="text-sm text-white leading-relaxed">{q.question}</p>
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
                  <span className="text-slate-400 font-medium">Guidance:</span>{" "}
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
