"use client"

import { useEffect, useState, useMemo } from "react"
import { useParams, useRouter } from "next/navigation"
import { DashboardLayout } from "@/components/layout/DashboardLayout"
import { useClient } from "@/contexts/ClientContext"
import { useProject } from "@/contexts/ProjectContext"
import { useAuth } from "@/contexts/AuthContext"
import { getClient, getProject } from "@/lib/supabase"
import { Loader2, Search, ChevronDown, ChevronRight, Landmark } from "lucide-react"

interface BnmRmitRequirement {
  reference_id: string
  requirement_type: string
  content: string
  notes: string | null
}

interface BnmRmitSection {
  section_id: string
  title: string
  subsection_title: string | null
  requirement_count: number
  requirements: BnmRmitRequirement[]
}

interface SectionGroup {
  section_id: string
  title: string
  subsections: BnmRmitSection[]
  total_requirements: number
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"

function renderContent(content: string) {
  return content.split(/(\*\*[^*]+?\*\*)/g).map((part, i) =>
    part.startsWith("**") && part.endsWith("**") ? (
      <strong key={i} className="text-slate-200 font-medium">
        {part.slice(2, -2)}
      </strong>
    ) : (
      part
    )
  )
}

export default function BnmRmitPage() {
  const params = useParams()
  const router = useRouter()
  const { user, loading: authLoading } = useAuth()
  const { selectedClient, setSelectedClient } = useClient()
  const { selectedProject, setSelectedProject } = useProject()
  const clientId = params.id as string
  const projectId = params.projectId as string

  const [loading, setLoading] = useState(true)
  const [sections, setSections] = useState<BnmRmitSection[]>([])
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set())
  const [searchQuery, setSearchQuery] = useState("")
  const [error, setError] = useState<string | null>(null)

  // Hydrate client/project context if navigated directly
  useEffect(() => {
    const fetchData = async () => {
      if (!authLoading && user) {
        try {
          if (!selectedClient && clientId) {
            const { data: client, error: clientError } = await getClient(clientId)
            if (clientError || !client) { router.push("/clients"); return }
            setSelectedClient(client)
          }
          if (!selectedProject && projectId) {
            const { data: project, error: projectError } = await getProject(projectId)
            if (projectError || !project) { router.push(`/clients/${clientId}/projects`); return }
            setSelectedProject(project)
          }
        } catch (err) {
          console.error("Error loading project data:", err)
        }
      }
    }
    fetchData()
  }, [clientId, projectId, selectedClient, selectedProject, authLoading, user, setSelectedClient, setSelectedProject, router])

  // Fetch BNM RMIT data
  useEffect(() => {
    const fetchBnmRmit = async () => {
      setLoading(true)
      setError(null)
      try {
        const res = await fetch(`${API_URL}/framework-docs/bnm-rmit`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        setSections(data.sections)
        const sectionIds = new Set<string>()
        for (const s of data.sections as BnmRmitSection[]) {
          sectionIds.add(s.section_id)
        }
        setExpandedSections(sectionIds)
      } catch (err) {
        setError("Failed to load BNM RMIT requirements")
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    fetchBnmRmit()
  }, [])

  const toggleSection = (sectionId: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev)
      if (next.has(sectionId)) next.delete(sectionId)
      else next.add(sectionId)
      return next
    })
  }

  // Filter requirements by search query, then group by section
  const groupedSections = useMemo(() => {
    const q = searchQuery.toLowerCase().trim()
    const filtered = q
      ? sections
          .map((section) => ({
            ...section,
            requirements: section.requirements.filter(
              (r) =>
                r.reference_id.toLowerCase().includes(q) ||
                r.content.toLowerCase().includes(q) ||
                (r.notes && r.notes.toLowerCase().includes(q)) ||
                section.title.toLowerCase().includes(q) ||
                (section.subsection_title && section.subsection_title.toLowerCase().includes(q))
            ),
          }))
          .filter((s) => s.requirements.length > 0)
      : sections

    const groups = new Map<string, SectionGroup>()
    for (const section of filtered) {
      const existing = groups.get(section.section_id)
      if (existing) {
        existing.subsections.push(section)
        existing.total_requirements += section.requirements.length
      } else {
        groups.set(section.section_id, {
          section_id: section.section_id,
          title: section.title,
          subsections: [section],
          total_requirements: section.requirements.length,
        })
      }
    }

    return Array.from(groups.values())
  }, [sections, searchQuery])

  const totalRequirements = sections.reduce((sum, s) => sum + s.requirement_count, 0)
  const sectionCount = new Set(sections.map((s) => s.section_id)).size

  if (authLoading || loading) {
    return (
      <DashboardLayout>
        <div className="flex justify-center items-center min-h-[400px]">
          <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
        </div>
      </DashboardLayout>
    )
  }

  if (!user) return null

  return (
    <DashboardLayout>
      <div className="max-w-6xl mx-auto pb-10">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-amber-500/10 rounded-lg">
              <Landmark className="w-6 h-6 text-amber-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">BNM RMIT — Policy Requirements</h1>
              <p className="text-slate-400 text-sm mt-1">
                {totalRequirements} requirements across {sectionCount} sections
              </p>
            </div>
          </div>
        </div>

        {/* Search Bar */}
        <div className="relative mb-6">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search by reference ID, content, or section title..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-slate-800/50 text-white rounded-lg border border-slate-700 focus:border-amber-500 focus:outline-none placeholder-slate-500 text-sm"
          />
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg p-4 mb-6">
            {error}
          </div>
        )}

        {/* Sections */}
        <div className="space-y-4">
          {groupedSections.map((group) => {
            const isExpanded = expandedSections.has(group.section_id)
            return (
              <div key={group.section_id} className="bg-slate-900/50 rounded-xl border border-slate-800">
                {/* Section Header */}
                <button
                  onClick={() => toggleSection(group.section_id)}
                  className="w-full flex items-center justify-between p-4 hover:bg-slate-800/30 transition-colors rounded-xl"
                >
                  <div className="flex items-center gap-3">
                    {isExpanded ? (
                      <ChevronDown className="w-5 h-5 text-slate-400" />
                    ) : (
                      <ChevronRight className="w-5 h-5 text-slate-400" />
                    )}
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
                      {group.section_id}
                    </span>
                    <h2 className="text-white font-semibold text-lg">{group.title}</h2>
                  </div>
                  <span className="text-slate-500 text-sm">
                    {group.total_requirements} requirements
                  </span>
                </button>

                {/* Requirements grouped by subsection */}
                {isExpanded && (
                  <div className="px-4 pb-4 space-y-4">
                    {group.subsections.map((sub, subIdx) => (
                      <div key={subIdx}>
                        {sub.subsection_title && (
                          <div className="mb-3 ml-8">
                            <h3 className="text-sm font-semibold text-amber-300/80 uppercase tracking-wide">
                              {sub.subsection_title}
                            </h3>
                          </div>
                        )}
                        <div className="space-y-3">
                          {sub.requirements.map((req) => (
                            <div
                              key={req.reference_id}
                              className="ml-8 p-4 bg-slate-800/40 rounded-lg border border-slate-700/50 hover:border-slate-600/50 transition-colors"
                            >
                              <div className="flex items-start gap-3">
                                <span
                                  className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-medium shrink-0 mt-0.5 ${
                                    req.requirement_type === "standard"
                                      ? "bg-amber-500/15 text-amber-400 border border-amber-500/30"
                                      : "bg-amber-500/5 text-amber-300/60 border border-dashed border-amber-500/20"
                                  }`}
                                >
                                  {req.reference_id}
                                </span>
                                <div className="flex-1 min-w-0">
                                  <div className="text-slate-300 text-sm whitespace-pre-line leading-relaxed">
                                    {renderContent(req.content)}
                                  </div>
                                  {req.notes && (
                                    <div className="mt-3 pl-3 border-l-2 border-amber-500/30 bg-amber-950/20 rounded-r-md py-2 pr-3">
                                      <p className="text-xs text-amber-200/60 font-medium mb-1">Note</p>
                                      <p className="text-slate-400 text-xs whitespace-pre-line leading-relaxed">
                                        {req.notes.replace(/\*\*Notes?:\*\*\s?/i, "")}
                                      </p>
                                    </div>
                                  )}
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {groupedSections.length === 0 && !loading && (
          <div className="text-center py-12 text-slate-500">
            No requirements match your search.
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}
