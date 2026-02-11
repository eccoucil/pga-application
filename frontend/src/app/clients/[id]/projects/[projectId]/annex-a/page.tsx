"use client"

import { useEffect, useState, useMemo } from "react"
import { useParams, useRouter } from "next/navigation"
import { DashboardLayout } from "@/components/layout/DashboardLayout"
import { useClient } from "@/contexts/ClientContext"
import { useProject } from "@/contexts/ProjectContext"
import { useAuth } from "@/contexts/AuthContext"
import { getClient, getProject } from "@/lib/supabase"
import { EditableControlCard } from "@/components/framework/EditableControlCard"
import { Loader2, Search, ChevronDown, ChevronRight, BookOpen } from "lucide-react"

interface AnnexAControl {
  control_id: string
  title: string
  description: string
}

interface AnnexASection {
  section_id: string
  title: string
  control_count: number
  controls: AnnexAControl[]
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"

export default function AnnexAPage() {
  const params = useParams()
  const router = useRouter()
  const { user, loading: authLoading } = useAuth()
  const { selectedClient, setSelectedClient } = useClient()
  const { selectedProject, setSelectedProject } = useProject()
  const clientId = params.id as string
  const projectId = params.projectId as string

  const [loading, setLoading] = useState(true)
  const [sections, setSections] = useState<AnnexASection[]>([])
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

  // Fetch Annex A data
  useEffect(() => {
    const fetchAnnexA = async () => {
      setLoading(true)
      setError(null)
      try {
        const res = await fetch(`${API_URL}/framework-docs/annex-a`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        setSections(data.sections)
        // Expand all sections by default
        setExpandedSections(new Set(data.sections.map((s: AnnexASection) => s.section_id)))
      } catch (err) {
        setError("Failed to load Annex A controls")
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    fetchAnnexA()
  }, [])

  const toggleSection = (sectionId: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev)
      if (next.has(sectionId)) next.delete(sectionId)
      else next.add(sectionId)
      return next
    })
  }

  const handleSave = async (controlId: string, title: string, description: string) => {
    const res = await fetch(`${API_URL}/framework-docs/annex-a/${controlId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, description }),
    })
    if (!res.ok) throw new Error("Failed to save")
    // Update local state
    setSections((prev) =>
      prev.map((section) => ({
        ...section,
        controls: section.controls.map((c) =>
          c.control_id === controlId ? { ...c, title, description } : c
        ),
      }))
    )
  }

  // Filter controls by search query
  const filteredSections = useMemo(() => {
    if (!searchQuery.trim()) return sections
    const q = searchQuery.toLowerCase()
    return sections
      .map((section) => ({
        ...section,
        controls: section.controls.filter(
          (c) =>
            c.control_id.toLowerCase().includes(q) ||
            c.title.toLowerCase().includes(q) ||
            c.description.toLowerCase().includes(q)
        ),
      }))
      .filter((section) => section.controls.length > 0)
  }, [sections, searchQuery])

  const totalControls = sections.reduce((sum, s) => sum + s.control_count, 0)

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
            <div className="p-2 bg-cyan-500/10 rounded-lg">
              <BookOpen className="w-6 h-6 text-cyan-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">ISO 27001:2022 — Annex A Controls</h1>
              <p className="text-slate-400 text-sm mt-1">
                {totalControls} information security controls across {sections.length} domains
              </p>
            </div>
          </div>
        </div>

        {/* Search Bar */}
        <div className="relative mb-6">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search controls by ID, title, or description..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-slate-800/50 text-white rounded-lg border border-slate-700 focus:border-cyan-500 focus:outline-none placeholder-slate-500 text-sm"
          />
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg p-4 mb-6">
            {error}
          </div>
        )}

        {/* Sections */}
        <div className="space-y-4">
          {filteredSections.map((section) => {
            const isExpanded = expandedSections.has(section.section_id)
            return (
              <div key={section.section_id} className="bg-slate-900/50 rounded-xl border border-slate-800">
                {/* Section Header */}
                <button
                  onClick={() => toggleSection(section.section_id)}
                  className="w-full flex items-center justify-between p-4 hover:bg-slate-800/30 transition-colors rounded-xl"
                >
                  <div className="flex items-center gap-3">
                    {isExpanded ? (
                      <ChevronDown className="w-5 h-5 text-slate-400" />
                    ) : (
                      <ChevronRight className="w-5 h-5 text-slate-400" />
                    )}
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-medium bg-purple-500/10 text-purple-400 border border-purple-500/20">
                      {section.section_id}
                    </span>
                    <h2 className="text-white font-semibold text-lg">{section.title}</h2>
                  </div>
                  <span className="text-slate-500 text-sm">{section.controls.length} controls</span>
                </button>

                {/* Controls List */}
                {isExpanded && (
                  <div className="px-4 pb-4 space-y-3">
                    {section.controls.map((control) => (
                      <EditableControlCard
                        key={control.control_id}
                        controlId={control.control_id}
                        title={control.title}
                        description={control.description}
                        categoryLabel={`${section.section_id}. ${section.title}`}
                        onSave={handleSave}
                      />
                    ))}
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {filteredSections.length === 0 && !loading && (
          <div className="text-center py-12 text-slate-500">
            No controls match your search.
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}
