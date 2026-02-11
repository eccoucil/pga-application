"use client"

import { Calendar, Eye, Edit2, Trash2, FolderKanban, ShieldCheck, Search, Filter, ChevronDown } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import type { Project, ProjectStatus } from "@/types/project"
import { useState, useEffect, useRef } from "react"

interface ProjectTableProps {
  projects: Project[]
  onView: (project: Project) => void
  onEdit: (project: Project) => void
  onDelete: (project: Project) => void
  searchTerm?: string
  onSearchChange?: (value: string) => void
  statusFilter?: "all" | ProjectStatus
  onStatusFilterChange?: (status: "all" | ProjectStatus) => void
}

const statusConfig = {
  planning: {
    label: "Planning",
    className: "bg-orange-500/10 text-orange-400 border-orange-500/20 shadow-orange-900/20",
  },
  "in-progress": {
    label: "In Progress",
    className: "bg-blue-500/10 text-blue-400 border-blue-500/20 shadow-blue-900/20",
  },
  completed: {
    label: "Completed",
    className: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20 shadow-emerald-900/20",
  },
  "on-hold": {
    label: "On Hold",
    className: "bg-slate-500/10 text-slate-400 border-slate-500/20 shadow-slate-900/20",
  },
}

export function ProjectTable({ 
  projects, 
  onView, 
  onEdit, 
  onDelete,
  searchTerm: externalSearchTerm = "",
  onSearchChange,
  statusFilter = "all",
  onStatusFilterChange,
}: ProjectTableProps) {
  const [internalSearchTerm, setInternalSearchTerm] = useState("")
  const [isFilterOpen, setIsFilterOpen] = useState(false)
  const filterRef = useRef<HTMLDivElement>(null)
  
  const searchTerm = externalSearchTerm || internalSearchTerm
  const handleSearchChange = onSearchChange || ((value: string) => setInternalSearchTerm(value))

  // Close filter dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (filterRef.current && !filterRef.current.contains(event.target as Node)) {
        setIsFilterOpen(false)
      }
    }

    if (isFilterOpen) {
      document.addEventListener("mousedown", handleClickOutside)
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside)
    }
  }, [isFilterOpen])

  const formatDate = (date: string | null) => {
    if (!date) return "—"
    return new Date(date).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    })
  }

  const filteredProjects = projects.filter((project) => {
    if (searchTerm) {
      const search = searchTerm.toLowerCase()
      const matchesSearch =
        project.name.toLowerCase().includes(search) ||
        project.description?.toLowerCase().includes(search) ||
        project.framework?.some((fw) => fw.toLowerCase().includes(search))
      if (!matchesSearch) return false
    }

    if (statusFilter !== "all" && project.status !== statusFilter) {
      return false
    }

    return true
  })

  const getStatusLabel = () => {
    if (statusFilter === "all") return "All Status"
    const status = statusConfig[statusFilter as keyof typeof statusConfig]
    return status ? status.label : statusFilter
  }

  return (
    <div className="bg-[#0f1016]/60 backdrop-blur-md border border-white/10 rounded-2xl overflow-hidden shadow-xl">
      {/* Toolbar */}
      <div className="p-5 border-b border-white/5 flex gap-4">
        <div className="flex-1 relative group">
          <div className="absolute -inset-0.5 bg-gradient-to-r from-purple-600 to-blue-600 rounded-lg blur opacity-0 group-focus-within:opacity-20 transition duration-1000 group-hover:duration-200"></div>
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 group-focus-within:text-purple-400 transition-colors" />
          <input
            type="text"
            placeholder="Search projects..."
            value={searchTerm}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="relative w-full bg-black/40 border border-white/10 rounded-lg pl-10 pr-4 py-2.5 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/50 transition-all"
          />
        </div>
        {onStatusFilterChange && (
          <div className="relative" ref={filterRef}>
            <button
              onClick={() => setIsFilterOpen(!isFilterOpen)}
              className="flex items-center gap-2 px-4 py-2.5 bg-black/40 border border-white/10 rounded-lg text-sm text-slate-300 hover:text-white hover:border-purple-500/30 hover:bg-purple-500/10 transition-all"
            >
              <span>{getStatusLabel()}</span>
              <ChevronDown className={`w-4 h-4 transition-transform ${isFilterOpen ? "rotate-180" : ""}`} />
            </button>
            {isFilterOpen && (
              <div className="absolute right-0 mt-2 w-40 bg-[#0f1016] border border-white/10 rounded-lg shadow-xl z-10 overflow-hidden">
                <button
                  onClick={() => {
                    onStatusFilterChange("all")
                    setIsFilterOpen(false)
                  }}
                  className={`w-full text-left px-4 py-2 text-sm transition-colors ${
                    statusFilter === "all"
                      ? "bg-purple-500/10 text-purple-300"
                      : "text-slate-300 hover:bg-white/5 hover:text-white"
                  }`}
                >
                  All Status
                </button>
                <button
                  onClick={() => {
                    onStatusFilterChange("planning")
                    setIsFilterOpen(false)
                  }}
                  className={`w-full text-left px-4 py-2 text-sm transition-colors ${
                    statusFilter === "planning"
                      ? "bg-purple-500/10 text-purple-300"
                      : "text-slate-300 hover:bg-white/5 hover:text-white"
                  }`}
                >
                  Planning
                </button>
                <button
                  onClick={() => {
                    onStatusFilterChange("in-progress")
                    setIsFilterOpen(false)
                  }}
                  className={`w-full text-left px-4 py-2 text-sm transition-colors ${
                    statusFilter === "in-progress"
                      ? "bg-purple-500/10 text-purple-300"
                      : "text-slate-300 hover:bg-white/5 hover:text-white"
                  }`}
                >
                  In Progress
                </button>
                <button
                  onClick={() => {
                    onStatusFilterChange("completed")
                    setIsFilterOpen(false)
                  }}
                  className={`w-full text-left px-4 py-2 text-sm transition-colors ${
                    statusFilter === "completed"
                      ? "bg-purple-500/10 text-purple-300"
                      : "text-slate-300 hover:bg-white/5 hover:text-white"
                  }`}
                >
                  Completed
                </button>
                <button
                  onClick={() => {
                    onStatusFilterChange("on-hold")
                    setIsFilterOpen(false)
                  }}
                  className={`w-full text-left px-4 py-2 text-sm transition-colors ${
                    statusFilter === "on-hold"
                      ? "bg-purple-500/10 text-purple-300"
                      : "text-slate-300 hover:bg-white/5 hover:text-white"
                  }`}
                >
                  On Hold
                </button>
              </div>
            )}
          </div>
        )}
        <button className="flex items-center gap-2 px-4 py-2.5 bg-black/40 border border-white/10 rounded-lg text-sm text-slate-300 hover:text-white hover:border-purple-500/30 hover:bg-purple-500/10 transition-all">
          <Filter className="w-4 h-4" />
          <span>Filters</span>
        </button>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-white/5 bg-white/[0.02]">
              <th className="px-6 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">Project</th>
              <th className="px-6 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">Framework</th>
              <th className="px-6 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">Timeline</th>
              <th className="px-6 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">Status</th>
              <th className="px-6 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">Last Updated</th>
              <th className="px-6 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {filteredProjects.map((project) => {
              const status = statusConfig[project.status as keyof typeof statusConfig] || statusConfig.planning

              return (
                <tr key={project.id} className="group hover:bg-white/[0.02] transition-colors">
                  {/* Project */}
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 text-white flex items-center justify-center shadow-lg shadow-cyan-900/20">
                        <ShieldCheck className="w-5 h-5" />
                      </div>
                      <div>
                        <div className="font-medium text-white group-hover:text-purple-300 transition-colors">{project.name}</div>
                        {project.description && (
                          <div className="text-xs text-slate-500 mt-0.5 truncate max-w-xs">{project.description}</div>
                        )}
                      </div>
                    </div>
                  </td>

                  {/* Framework */}
                  <td className="px-6 py-4">
                    <div className="flex flex-wrap gap-2">
                      {project.framework && project.framework.length > 0 ? (
                        project.framework.map((fw) => (
                          <span
                            key={fw}
                            className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-slate-800/50 text-slate-300 border border-white/10 backdrop-blur-sm"
                          >
                            {fw}
                          </span>
                        ))
                      ) : (
                        <span className="text-sm text-slate-500">—</span>
                      )}
                    </div>
                  </td>

                  {/* Timeline */}
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2 text-slate-400 group-hover:text-slate-300 transition-colors">
                      <Calendar className="w-4 h-4" />
                      <span className="text-sm">
                        {formatDate(project.start_date)} - {formatDate(project.end_date)}
                      </span>
                    </div>
                  </td>

                  {/* Status */}
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border backdrop-blur-sm shadow-sm ${status.className}`}>
                      <span
                        className={`w-1.5 h-1.5 rounded-full mr-1.5 ${
                          project.status === "completed"
                            ? "bg-emerald-400"
                            : project.status === "in-progress"
                            ? "bg-blue-400"
                            : project.status === "planning"
                            ? "bg-orange-400"
                            : "bg-slate-400"
                        }`}
                      ></span>
                      {status.label}
                    </span>
                  </td>

                  {/* Last Updated */}
                  <td className="px-6 py-4">
                    <span className="text-sm text-slate-400">{formatDate(project.updated_at)}</span>
                  </td>

                  {/* Actions */}
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-1 opacity-60 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={() => onView(project)}
                        className="p-2 text-purple-400 hover:bg-purple-500/20 rounded-lg transition-colors"
                        title="View Assessment"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => onEdit(project)}
                        className="p-2 text-blue-400 hover:bg-blue-500/20 rounded-lg transition-colors"
                        title="Edit"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => onDelete(project)}
                        className="p-2 text-rose-400 hover:bg-rose-500/20 rounded-lg transition-colors"
                        title="Delete"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {filteredProjects.length === 0 && (
        <div className="text-center py-12">
          <FolderKanban className="h-12 w-12 text-slate-600 mx-auto mb-4" />
          <p className="text-slate-400 text-lg">No projects found</p>
          <p className="text-slate-500 text-sm mt-2">Create your first project to get started</p>
        </div>
      )}
    </div>
  )
}
