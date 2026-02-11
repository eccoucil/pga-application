"use client"

import { useEffect, useState, useMemo } from "react"
import { useParams, useRouter } from "next/navigation"
import { DashboardLayout } from "@/components/layout/DashboardLayout"
import { useClient } from "@/contexts/ClientContext"
import { useProject } from "@/contexts/ProjectContext"
import { useAuth } from "@/contexts/AuthContext"
import { getClient, getProject } from "@/lib/supabase"
import { Loader2, Search, ChevronDown, ChevronRight, ScrollText, Pencil, Check, X } from "lucide-react"
import { Button } from "@/components/ui/button"

interface SubClause {
  sub_clause_id: string
  title: string
  content: string
}

interface ManagementClause {
  clause_id: string
  title: string
  sub_clauses: SubClause[]
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"

export default function ManagementClausesPage() {
  const params = useParams()
  const router = useRouter()
  const { user, loading: authLoading } = useAuth()
  const { selectedClient, setSelectedClient } = useClient()
  const { selectedProject, setSelectedProject } = useProject()
  const clientId = params.id as string
  const projectId = params.projectId as string

  const [loading, setLoading] = useState(true)
  const [clauses, setClauses] = useState<ManagementClause[]>([])
  const [expandedClauses, setExpandedClauses] = useState<Set<string>>(new Set())
  const [searchQuery, setSearchQuery] = useState("")
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editContent, setEditContent] = useState("")
  const [saving, setSaving] = useState(false)
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

  // Fetch management clauses
  useEffect(() => {
    const fetchClauses = async () => {
      setLoading(true)
      setError(null)
      try {
        const res = await fetch(`${API_URL}/framework-docs/management-clauses`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        setClauses(data.clauses)
        setExpandedClauses(new Set(data.clauses.map((c: ManagementClause) => c.clause_id)))
      } catch (err) {
        setError("Failed to load management clauses")
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    fetchClauses()
  }, [])

  const toggleClause = (clauseId: string) => {
    setExpandedClauses((prev) => {
      const next = new Set(prev)
      if (next.has(clauseId)) next.delete(clauseId)
      else next.add(clauseId)
      return next
    })
  }

  const startEdit = (subClause: SubClause) => {
    setEditingId(subClause.sub_clause_id)
    setEditContent(subClause.content)
  }

  const cancelEdit = () => {
    setEditingId(null)
    setEditContent("")
  }

  const handleSave = async (subClauseId: string) => {
    setSaving(true)
    try {
      const res = await fetch(`${API_URL}/framework-docs/management-clauses/${subClauseId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: editContent }),
      })
      if (!res.ok) throw new Error("Failed to save")
      // Update local state
      setClauses((prev) =>
        prev.map((clause) => ({
          ...clause,
          sub_clauses: clause.sub_clauses.map((sc) =>
            sc.sub_clause_id === subClauseId ? { ...sc, content: editContent } : sc
          ),
        }))
      )
      setEditingId(null)
    } catch (err) {
      console.error("Save failed:", err)
    } finally {
      setSaving(false)
    }
  }

  // Filter by search
  const filteredClauses = useMemo(() => {
    if (!searchQuery.trim()) return clauses
    const q = searchQuery.toLowerCase()
    return clauses
      .map((clause) => ({
        ...clause,
        sub_clauses: clause.sub_clauses.filter(
          (sc) =>
            sc.sub_clause_id.toLowerCase().includes(q) ||
            sc.title.toLowerCase().includes(q) ||
            sc.content.toLowerCase().includes(q)
        ),
      }))
      .filter((clause) => clause.sub_clauses.length > 0)
  }, [clauses, searchQuery])

  const totalSubClauses = clauses.reduce((sum, c) => sum + c.sub_clauses.length, 0)

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
            <div className="p-2 bg-purple-500/10 rounded-lg">
              <ScrollText className="w-6 h-6 text-purple-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">ISO 27001:2022 — Management Clauses</h1>
              <p className="text-slate-400 text-sm mt-1">
                Clauses 4–10: {totalSubClauses} requirements across {clauses.length} management areas
              </p>
            </div>
          </div>
        </div>

        {/* Search Bar */}
        <div className="relative mb-6">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search clauses by ID, title, or content..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-slate-800/50 text-white rounded-lg border border-slate-700 focus:border-purple-500 focus:outline-none placeholder-slate-500 text-sm"
          />
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg p-4 mb-6">
            {error}
          </div>
        )}

        {/* Clauses */}
        <div className="space-y-4">
          {filteredClauses.map((clause) => {
            const isExpanded = expandedClauses.has(clause.clause_id)
            return (
              <div key={clause.clause_id} className="bg-slate-900/50 rounded-xl border border-slate-800">
                {/* Clause Header */}
                <button
                  onClick={() => toggleClause(clause.clause_id)}
                  className="w-full flex items-center justify-between p-4 hover:bg-slate-800/30 transition-colors rounded-xl"
                >
                  <div className="flex items-center gap-3">
                    {isExpanded ? (
                      <ChevronDown className="w-5 h-5 text-slate-400" />
                    ) : (
                      <ChevronRight className="w-5 h-5 text-slate-400" />
                    )}
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-medium bg-purple-500/10 text-purple-400 border border-purple-500/20">
                      {clause.clause_id}
                    </span>
                    <h2 className="text-white font-semibold text-lg">
                      Clause {clause.clause_id}: {clause.title}
                    </h2>
                  </div>
                  <span className="text-slate-500 text-sm">{clause.sub_clauses.length} sub-clauses</span>
                </button>

                {/* Sub-clauses */}
                {isExpanded && (
                  <div className="px-4 pb-4 space-y-3">
                    {clause.sub_clauses.map((sc) => {
                      const isEditing = editingId === sc.sub_clause_id
                      return (
                        <div
                          key={sc.sub_clause_id}
                          className="bg-slate-800/50 rounded-lg border border-slate-700 p-4 hover:border-slate-600 transition-colors"
                        >
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex-1 min-w-0">
                              {/* Identifier Badge & Title */}
                              <div className="flex items-start gap-3 mb-3">
                                <span className="inline-flex items-center px-2.5 py-1 rounded text-xs font-mono font-medium bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 whitespace-nowrap">
                                  {sc.sub_clause_id}
                                </span>
                                <h3 className="text-white font-medium leading-tight">{sc.title}</h3>
                              </div>

                              {/* Content */}
                              {isEditing ? (
                                <textarea
                                  value={editContent}
                                  onChange={(e) => setEditContent(e.target.value)}
                                  rows={8}
                                  className="w-full bg-slate-700 text-slate-300 rounded px-3 py-2 text-sm border border-slate-600 focus:border-purple-500 focus:outline-none resize-y font-mono"
                                />
                              ) : (
                                <div className="text-slate-400 text-sm whitespace-pre-wrap leading-relaxed">
                                  {sc.content}
                                </div>
                              )}

                              {/* Category */}
                              <p className="text-slate-500 text-xs mt-2">
                                Clause {clause.clause_id}: {clause.title}
                              </p>
                            </div>

                            {/* Action Buttons */}
                            <div className="flex items-center gap-1 flex-shrink-0">
                              {isEditing ? (
                                <>
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    onClick={() => handleSave(sc.sub_clause_id)}
                                    disabled={saving}
                                    className="text-green-400 hover:text-green-300 hover:bg-slate-700"
                                  >
                                    <Check className="h-4 w-4" />
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    onClick={cancelEdit}
                                    disabled={saving}
                                    className="text-slate-400 hover:text-red-400 hover:bg-slate-700"
                                  >
                                    <X className="h-4 w-4" />
                                  </Button>
                                </>
                              ) : (
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  onClick={() => startEdit(sc)}
                                  className="text-slate-400 hover:text-cyan-400 hover:bg-slate-700"
                                >
                                  <Pencil className="h-4 w-4" />
                                </Button>
                              )}
                            </div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {filteredClauses.length === 0 && !loading && (
          <div className="text-center py-12 text-slate-500">
            No clauses match your search.
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}
