"use client"

import { useEffect, useState, useMemo, useRef, useCallback } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { supabase } from "@/lib/supabase"
import { useToast } from "@/hooks/use-toast"
import {
  Shield,
  ClipboardList,
  ChevronDown,
  ChevronRight,
  Loader2,
  FileQuestion,
  AlertCircle,
  Search,
  Trash2,
  RefreshCw,
} from "lucide-react"
import type { Project } from "@/types/project"
import type { FrameworkQuestion, ControlItem, SectionWithControls, QuestionScope } from "@/types/questionnaire"
import { ISO_SECTION_FILTERS, BNM_SECTION_FILTERS } from "@/types/framework"

const FRAMEWORK_KEYS: Record<string, string> = {
  "ISO 27001:2022": "iso_27001",
  "BNM RMIT": "bnm_rmit",
}

interface QuestionnaireContentProps {
  clientId: string
  projectId: string
  project: Project
  onQuestionsGenerated?: () => void
}

export function QuestionnaireContent({ clientId, projectId, project, onQuestionsGenerated }: QuestionnaireContentProps) {
  const router = useRouter()
  const { toast } = useToast()

  const [questions, setQuestions] = useState<FrameworkQuestion[]>([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [generationProgress, setGenerationProgress] = useState<{
    current: number
    total: number
    currentFramework: string
  } | null>(null)
  const autoGenerateAttempted = useRef(false)
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set())

  // New state for filtering
  const [activeFramework, setActiveFramework] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState("")
  const [activeSection, setActiveSection] = useState<string | null>(null)

  // Fetch questions from database
  const fetchQuestions = useCallback(async () => {
    setLoading(true)
    const { data: questionsData, error: questionsError } = await supabase
      .from("framework_questions")
      .select("*")
      .eq("project_id", projectId)
      .order("framework")
      .order("section_id")

    if (questionsError) {
      console.error("Error fetching questions:", questionsError)
    }

    setQuestions(questionsData || [])
    setLoading(false)
  }, [projectId])

  // Generate questions via backend API — one call per (framework, section) pair
  const handleGenerateQuestions = useCallback(async () => {
    if (!project?.framework || project.framework.length === 0) {
      toast({
        title: "No frameworks selected",
        description: "Please select compliance frameworks in project settings first.",
        variant: "destructive",
      })
      return
    }

    setGenerating(true)

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"
      const { data: { session } } = await supabase.auth.getSession()

      if (!session?.access_token) {
        toast({
          title: "Authentication required",
          description: "Please log in again to generate questions.",
          variant: "destructive",
        })
        router.push("/login")
        return
      }

      // Build list of frameworks to process (one call per framework)
      const jobs: { frameworkKey: string; displayName: string }[] = []
      for (const fw of project.framework) {
        const key = FRAMEWORK_KEYS[fw]
        if (!key) {
          console.warn(`Unknown framework "${fw}", skipping`)
          continue
        }
        jobs.push({ frameworkKey: key, displayName: fw })
      }

      if (jobs.length === 0) {
        toast({
          title: "No frameworks found",
          description: "Could not determine keys for the selected frameworks.",
          variant: "destructive",
        })
        setGenerating(false)
        return
      }

      setGenerationProgress({ current: 0, total: jobs.length, currentFramework: jobs[0].displayName })

      let totalQuestions = 0
      const errors: string[] = []

      for (let i = 0; i < jobs.length; i++) {
        const job = jobs[i]
        setGenerationProgress({ current: i, total: jobs.length, currentFramework: job.displayName })

        try {
          const response = await fetch(`${apiUrl}/questions/generate`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "Authorization": `Bearer ${session.access_token}`,
            },
            body: JSON.stringify({
              project_id: projectId,
              client_id: clientId,
              framework: job.frameworkKey,
            }),
          })

          if (!response.ok) {
            const errorData = await response.json().catch(() => ({}))
            const msg = errorData.detail || `HTTP ${response.status}`
            console.error(`Failed framework ${job.displayName}: ${msg}`)
            errors.push(job.displayName)
            continue
          }

          const result = await response.json()
          totalQuestions += result.question_count ?? 0
        } catch (frameworkError) {
          console.error(`Error generating ${job.displayName}:`, frameworkError)
          errors.push(job.displayName)
        }
      }

      setGenerationProgress({ current: jobs.length, total: jobs.length, currentFramework: "Done" })

      if (errors.length > 0 && errors.length === jobs.length) {
        throw new Error("All frameworks failed to generate. Check the backend logs.")
      }

      toast({
        title: "Questions generated",
        description: errors.length > 0
          ? `Generated ${totalQuestions} questions. ${errors.length} framework(s) failed.`
          : `Generated ${totalQuestions} compliance questions successfully.`,
      })

      // Refresh questions from database
      await fetchQuestions()

      // Notify parent
      onQuestionsGenerated?.()
    } catch (error) {
      console.error("Error generating questions:", error)
      toast({
        title: "Generation failed",
        description: error instanceof Error ? error.message : "Failed to generate questions. Please try again.",
        variant: "destructive",
      })
    } finally {
      setGenerating(false)
      setGenerationProgress(null)
    }
  }, [clientId, projectId, project, router, toast, fetchQuestions, onQuestionsGenerated])

  // Load questions on mount
  useEffect(() => {
    fetchQuestions()
  }, [fetchQuestions])

  // Auto-generate questions when page loads with no existing questions
  useEffect(() => {
    if (
      !loading &&
      !generating &&
      questions.length === 0 &&
      !autoGenerateAttempted.current &&
      project?.framework &&
      project.framework.length > 0
    ) {
      autoGenerateAttempted.current = true
      handleGenerateQuestions()
    }
  }, [loading, generating, questions.length, project, handleGenerateQuestions])

  // Delete questions via backend API
  async function handleDeleteQuestions() {
    if (!confirm("Are you sure you want to delete all questions? This action cannot be undone.")) {
      return
    }

    setDeleting(true)

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"
      const { data: { session } } = await supabase.auth.getSession()

      if (!session?.access_token) {
        toast({
          title: "Authentication required",
          description: "Please log in again.",
          variant: "destructive",
        })
        return
      }

      const response = await fetch(`${apiUrl}/questionnaire/${projectId}`, {
        method: "DELETE",
        headers: {
          "Authorization": `Bearer ${session.access_token}`,
        },
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `Failed to delete questions: ${response.status}`)
      }

      const result = await response.json()

      toast({
        title: "Questions deleted",
        description: result.message,
      })

      // Clear local state
      setQuestions([])
      setExpandedSections(new Set())
      setActiveFramework(null)
      setActiveSection(null)
      setSearchQuery("")
    } catch (error) {
      console.error("Error deleting questions:", error)
      toast({
        title: "Deletion failed",
        description: error instanceof Error ? error.message : "Failed to delete questions.",
        variant: "destructive",
      })
    } finally {
      setDeleting(false)
    }
  }

  // Toggle section expansion
  function toggleSection(sectionKey: string) {
    setExpandedSections((prev) => {
      const next = new Set(prev)
      if (next.has(sectionKey)) {
        next.delete(sectionKey)
      } else {
        next.add(sectionKey)
      }
      return next
    })
  }

  // Get unique frameworks
  const frameworks = useMemo(() => {
    return [...new Set(questions.map(q => q.framework))]
  }, [questions])

  // Derive available section filters based on active framework
  const sectionFilters = useMemo(() => {
    if (activeFramework === "ISO 27001:2022") return ISO_SECTION_FILTERS
    if (activeFramework === "BNM RMIT") return BNM_SECTION_FILTERS
    return null // No section filter when "All Frameworks" is active
  }, [activeFramework])

  // Filter questions by framework, section, and search
  const filteredQuestions = useMemo(() => {
    let filtered = questions

    // Filter by framework
    if (activeFramework) {
      filtered = filtered.filter(q => q.framework === activeFramework)
    }

    // Filter by section/control category
    if (activeSection && activeSection !== "all") {
      if (activeSection === "management") {
        // Management clauses: section_ids "4" through "10" (pure numeric)
        filtered = filtered.filter(q => {
          const sid = q.section_id || ""
          return /^\d+$/.test(sid)
        })
      } else if (activeSection === "12-18") {
        // BNM sections 12 through 18
        filtered = filtered.filter(q => {
          const sid = q.section_id || ""
          const num = parseInt(sid, 10)
          return /^\d+$/.test(sid) && num >= 12 && num <= 18
        })
      } else {
        filtered = filtered.filter(q => q.section_id === activeSection)
      }
    }

    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter(q => {
        const questionTexts = q.questions?.map(qq => qq.question_text.toLowerCase()) || []
        const matchesQuestion = questionTexts.some(t => t.includes(query))
        const matchesSection = q.section_title?.toLowerCase().includes(query)
        const matchesControl = q.control_id?.toLowerCase().includes(query) || q.control_title?.toLowerCase().includes(query)
        const matchesControls = q.referenced_controls?.some(c => c.toLowerCase().includes(query))
        return matchesQuestion || matchesSection || matchesControl || matchesControls
      })
    }

    return filtered
  }, [questions, activeFramework, activeSection, searchQuery])

  // Sort control IDs naturally: "4" < "4.1" < "4.2" < "4.10" < "5"
  function compareControlIds(a: string, b: string): number {
    const partsA = a.split('.').map(Number)
    const partsB = b.split('.').map(Number)
    for (let i = 0; i < Math.max(partsA.length, partsB.length); i++) {
      const numA = partsA[i] ?? -1
      const numB = partsB[i] ?? -1
      if (numA !== numB) return numA - numB
    }
    return 0
  }

  // Group controls by section, sorted numerically
  function groupControlsBySection(): SectionWithControls[] {
    const sectionMap = new Map<string, SectionWithControls>()

    for (const q of filteredQuestions) {
      const sectionKey = `${q.framework}-${q.section_id || "overview"}`

      if (!sectionMap.has(sectionKey)) {
        sectionMap.set(sectionKey, {
          section_id: q.section_id || "overview",
          section_title: q.section_title || "Framework Overview",
          framework: q.framework,
          controls: [],
        })
      }

      sectionMap.get(sectionKey)!.controls.push({
        control_id: q.control_id || q.section_id || "overview",
        control_title: q.control_title || q.section_title || "Framework Overview",
        framework: q.framework,
        question_scope: q.question_scope,
        frameworkQuestion: q,
      })
    }

    // Sort controls within each section
    for (const section of sectionMap.values()) {
      section.controls.sort((a, b) => compareControlIds(a.control_id, b.control_id))
    }

    // Sort sections themselves
    const sections = Array.from(sectionMap.values())
    sections.sort((a, b) => compareControlIds(a.section_id, b.section_id))

    return sections
  }

  // Loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <Loader2 className="h-8 w-8 animate-spin text-cyan-400" />
      </div>
    )
  }

  const sectionGroups = groupControlsBySection()
  const allControlKeys = sectionGroups.flatMap(s =>
    s.controls.map(c => `${c.framework}-${c.control_id}`)
  )
  const totalControls = allControlKeys.length
  const hasQuestions = questions.length > 0
  const totalQuestionCount = filteredQuestions.reduce((acc, q) => acc + (q.questions?.length || 0), 0)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <ClipboardList className="h-6 w-6 text-cyan-400" />
          <div>
            <h2 className="text-xl font-bold text-white">Compliance Questionnaires</h2>
            <p className="text-slate-400 text-sm">Generate and review compliance questions</p>
          </div>
        </div>

        {/* Actions when questions exist */}
        {hasQuestions && !generating && (
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleDeleteQuestions}
              disabled={deleting}
              className="text-red-400 border-red-500/30 hover:bg-red-500/10 hover:border-red-500/50"
            >
              {deleting ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Trash2 className="h-4 w-4 mr-2" />
              )}
              Delete All
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleDeleteQuestions}
              disabled={generating || deleting}
              className="text-cyan-400 border-cyan-500/30 hover:bg-cyan-500/10 hover:border-cyan-500/50"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Regenerate
            </Button>
          </div>
        )}
      </div>

      {/* Generating State */}
      {generating && (
        <div className="flex flex-col items-center justify-center py-16">
          <div className="relative">
            <Loader2 className="h-16 w-16 text-cyan-400 animate-spin" />
            <ClipboardList className="h-6 w-6 text-cyan-400 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
          </div>
          <h3 className="text-xl font-semibold text-white mt-6 mb-2">Generating Questions</h3>
          {generationProgress ? (
            <>
              <p className="text-slate-400 text-center max-w-md">
                Processing framework: {generationProgress.currentFramework}
              </p>
              <p className="text-slate-500 text-sm mt-1">
                {generationProgress.current} / {generationProgress.total} frameworks
              </p>
              <div className="mt-4 w-64 h-2 bg-slate-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-cyan-500 rounded-full transition-all duration-300"
                  style={{ width: `${(generationProgress.current / generationProgress.total) * 100}%` }}
                />
              </div>
            </>
          ) : (
            <p className="text-slate-400 text-center max-w-md">
              Preparing question generation...
            </p>
          )}
          <div className="mt-4 flex items-center gap-2 text-sm text-slate-500">
            <Shield className="h-4 w-4" />
            <span>Questions are grounded in actual control text for accuracy</span>
          </div>
        </div>
      )}

      {/* Empty State - No questions yet */}
      {!generating && !hasQuestions && (
        <div className="flex flex-col items-center justify-center py-16">
          <div className="p-4 rounded-full bg-slate-800/50 mb-6">
            <FileQuestion className="h-12 w-12 text-slate-400" />
          </div>
          <h3 className="text-xl font-semibold text-white mb-2">No Questions Generated</h3>
          <p className="text-slate-400 text-center max-w-md mb-6">
            Generate 100+ compliance assessment questions per framework based on your selected frameworks.
          </p>

          {/* Selected frameworks */}
          {project.framework && project.framework.length > 0 ? (
            <>
              <div className="flex flex-wrap justify-center gap-2 mb-6">
                {project.framework.map((fw) => (
                  <span
                    key={fw}
                    className="inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium bg-cyan-500/10 text-cyan-400 border border-cyan-500/20"
                  >
                    <Shield className="h-4 w-4 mr-2" />
                    {fw}
                  </span>
                ))}
              </div>
              <Button variant="cyber" onClick={handleGenerateQuestions}>
                <ClipboardList className="h-4 w-4 mr-2" />
                Generate 100+ Questions
              </Button>
              <p className="mt-4 text-sm text-slate-500">
                Approximately {project.framework.length * 100} questions will be generated
              </p>
            </>
          ) : (
            <div className="flex items-center gap-2 text-amber-400 bg-amber-500/10 px-4 py-3 rounded-lg border border-amber-500/20">
              <AlertCircle className="h-5 w-5" />
              <span>No compliance frameworks selected. Please update project settings.</span>
            </div>
          )}
        </div>
      )}

      {/* Questions View */}
      {!generating && hasQuestions && (
        <div className="space-y-4">
          {/* Framework Tabs */}
          {frameworks.length > 1 && (
            <div className="flex flex-wrap gap-2 mb-4">
              <Button
                variant={!activeFramework ? "cyber" : "outline"}
                size="sm"
                onClick={() => { setActiveFramework(null); setActiveSection(null) }}
                className={!activeFramework ? "" : "text-slate-400 border-slate-700 hover:bg-slate-800"}
              >
                All Frameworks ({questions.length})
              </Button>
              {frameworks.map(fw => {
                const count = questions.filter(q => q.framework === fw).length
                return (
                  <Button
                    key={fw}
                    variant={activeFramework === fw ? "cyber" : "outline"}
                    size="sm"
                    onClick={() => { setActiveFramework(fw); setActiveSection(null) }}
                    className={activeFramework === fw ? "" : "text-slate-400 border-slate-700 hover:bg-slate-800"}
                  >
                    {fw} ({count})
                  </Button>
                )
              })}
            </div>
          )}

          {/* Section / Control Category Filter */}
          {sectionFilters && (
            <div className="flex flex-wrap gap-2 mb-4">
              {sectionFilters.map(filter => {
                const isActive = (filter.value === "all" && !activeSection) || activeSection === filter.value
                const count = questions.filter(q => {
                  if (filter.value === "all") return q.framework === activeFramework
                  if (filter.value === "management") return q.framework === activeFramework && /^\d+$/.test(q.section_id || "")
                  if (filter.value === "12-18") {
                    const sid = q.section_id || ""
                    const num = parseInt(sid, 10)
                    return q.framework === activeFramework && /^\d+$/.test(sid) && num >= 12 && num <= 18
                  }
                  return q.section_id === filter.value
                }).length
                return (
                  <Button
                    key={filter.value}
                    variant={isActive ? "cyber" : "outline"}
                    size="sm"
                    onClick={() => setActiveSection(filter.value === "all" ? null : filter.value)}
                    className={isActive ? "" : "text-slate-400 border-slate-700 hover:bg-slate-800"}
                  >
                    {filter.label} ({count})
                  </Button>
                )
              })}
            </div>
          )}

          {/* Search Bar */}
          <div className="relative mb-4">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search questions, sections, or control IDs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-slate-800/50 border border-slate-700 rounded-lg text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
              >
                &times;
              </button>
            )}
          </div>

          {/* Summary */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-4">
              <span className="text-slate-400">
                {totalControls} controls &bull; {totalQuestionCount} questions
                {searchQuery && ` (filtered from ${questions.reduce((acc, q) => acc + (q.questions?.length || 0), 0)})`}
              </span>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                if (expandedSections.size === allControlKeys.length) {
                  setExpandedSections(new Set())
                } else {
                  setExpandedSections(new Set(allControlKeys))
                }
              }}
              className="text-slate-400 border-slate-700 hover:bg-slate-800"
            >
              {expandedSections.size === allControlKeys.length ? "Collapse All" : "Expand All"}
            </Button>
          </div>

          {/* No Results */}
          {sectionGroups.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 text-slate-400">
              <Search className="h-8 w-8 mb-4" />
              <p>No questions match your search criteria.</p>
              <button
                onClick={() => {
                  setSearchQuery("")
                  setActiveFramework(null)
                  setActiveSection(null)
                }}
                className="mt-2 text-cyan-400 hover:underline"
              >
                Clear filters
              </button>
            </div>
          )}

          {/* Section Groups with Control Accordions */}
          {sectionGroups.map((section) => (
            <div key={`${section.framework}-${section.section_id}`} className="space-y-2">
              {/* Section Divider Header */}
              <div className="flex items-center gap-3 pt-4 pb-2">
                <div className="h-px flex-1 bg-slate-700" />
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Section {section.section_id}: {section.section_title}
                </span>
                <div className="h-px flex-1 bg-slate-700" />
              </div>

              {/* Control Accordions */}
              {section.controls.map((control) => {
                const controlKey = `${control.framework}-${control.control_id}`
                const isExpanded = expandedSections.has(controlKey)
                const questionCount = control.frameworkQuestion.questions?.length || 0

                return (
                  <div
                    key={controlKey}
                    className="bg-slate-800/50 rounded-lg border border-slate-700 overflow-hidden"
                  >
                    {/* Control Header */}
                    <button
                      onClick={() => toggleSection(controlKey)}
                      className="w-full flex items-center justify-between p-4 hover:bg-slate-800/80 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        {isExpanded ? (
                          <ChevronDown className="h-5 w-5 text-cyan-400" />
                        ) : (
                          <ChevronRight className="h-5 w-5 text-slate-400" />
                        )}
                        <div className="text-left">
                          <div className="flex items-center gap-2">
                            <span className="text-cyan-400 font-mono text-sm">{control.control_id}</span>
                            <h4 className="text-white font-medium">{control.control_title}</h4>
                            <ScopeBadge scope={control.question_scope} />
                          </div>
                          <p className="text-slate-400 text-sm">{control.framework}</p>
                        </div>
                      </div>
                      <span className="text-slate-400 text-sm">
                        {questionCount} question{questionCount !== 1 ? "s" : ""}
                      </span>
                    </button>

                    {/* Control Content */}
                    {isExpanded && (
                      <div className="border-t border-slate-700 p-4 space-y-4">
                        {control.frameworkQuestion.questions?.map((q, idx) => (
                          <QuestionCard
                            key={`${control.frameworkQuestion.id}-${idx}`}
                            questionNumber={q.question_number}
                            questionText={q.question_text}
                            questionType={q.question_type}
                            expectedEvidence={q.expected_evidence}
                            referencedControls={control.frameworkQuestion.referenced_controls}
                            groundingSource={control.frameworkQuestion.grounding_source}
                            searchQuery={searchQuery}
                          />
                        ))}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// Scope Badge Component
function ScopeBadge({ scope }: { scope: QuestionScope | null }) {
  if (!scope) return null

  const config: Record<string, { label: string; className: string }> = {
    framework_overview: {
      label: "Overview",
      className: "bg-purple-500/10 text-purple-400 border-purple-500/20",
    },
    section_deep_dive: {
      label: "Deep Dive",
      className: "bg-cyan-500/10 text-cyan-400 border-cyan-500/20",
    },
  }

  const scopeConfig = config[scope]
  if (!scopeConfig) return null

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${scopeConfig.className}`}>
      {scopeConfig.label}
    </span>
  )
}

// Highlight matching text
function highlightText(text: string, query: string): React.ReactNode {
  if (!query.trim()) return text

  const parts = text.split(new RegExp(`(${query})`, "gi"))
  return (
    <>
      {parts.map((part, i) =>
        part.toLowerCase() === query.toLowerCase() ? (
          <mark key={i} className="bg-cyan-500/30 text-white rounded px-0.5">
            {part}
          </mark>
        ) : (
          part
        )
      )}
    </>
  )
}

// Question Card Component
function QuestionCard({
  questionNumber,
  questionText,
  questionType,
  expectedEvidence,
  referencedControls,
  groundingSource,
  searchQuery = "",
}: {
  questionNumber: number
  questionText: string
  questionType: string
  expectedEvidence: string
  referencedControls?: string[]
  groundingSource?: string | null
  searchQuery?: string
}) {
  const typeConfig: Record<string, { label: string; className: string }> = {
    policy: {
      label: "Policy",
      className: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    },
    implementation: {
      label: "Implementation",
      className: "bg-green-500/10 text-green-400 border-green-500/20",
    },
    evidence: {
      label: "Evidence",
      className: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    },
    control_specific: {
      label: "Control Specific",
      className: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    },
    practice_based: {
      label: "Practice Based",
      className: "bg-green-500/10 text-green-400 border-green-500/20",
    },
    evidence_focused: {
      label: "Evidence Focused",
      className: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    },
    maturity_assessment: {
      label: "Maturity",
      className: "bg-purple-500/10 text-purple-400 border-purple-500/20",
    },
  }

  const config = typeConfig[questionType] || typeConfig.policy

  return (
    <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-700/50">
      <div className="flex items-start gap-4">
        {/* Question Number */}
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center">
          <span className="text-cyan-400 text-sm font-medium">{questionNumber}</span>
        </div>

        <div className="flex-1 min-w-0">
          {/* Question Text */}
          <p className="text-white mb-3">{highlightText(questionText, searchQuery)}</p>

          {/* Badges */}
          <div className="flex flex-wrap items-center gap-2 mb-3">
            <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${config.className}`}>
              {config.label}
            </span>
            {referencedControls?.map((control) => (
              <span
                key={control}
                className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-700/50 text-slate-300 border border-slate-600"
              >
                {highlightText(control, searchQuery)}
              </span>
            ))}
          </div>

          {/* Expected Evidence */}
          {expectedEvidence && (
            <div className="text-sm mb-2">
              <span className="text-slate-500">Expected Evidence: </span>
              <span className="text-slate-400">{expectedEvidence}</span>
            </div>
          )}

          {/* Grounding Source (Anti-hallucination) */}
          {groundingSource && (
            <div className="text-sm mt-2 pt-2 border-t border-slate-700/50">
              <span className="text-slate-500">Grounded in: </span>
              <span className="text-slate-400 italic">&quot;{groundingSource}&quot;</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
