"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Plus, Search, Filter, FolderKanban, Loader2, ArrowLeft } from "lucide-react"
import { ProjectTable } from "@/components/projects/ProjectTable"
import { ProjectModal } from "@/components/projects/ProjectModal"
import { DeleteConfirmation } from "@/components/projects/DeleteConfirmation"
import { StatusCard } from "@/components/projects/StatusCard"
import type { Project, CreateProjectData, UpdateProjectData, ProjectStatus } from "@/types/project"
import { useAuth } from "@/contexts/AuthContext"
import { useClient } from "@/contexts/ClientContext"
import { useProject } from "@/contexts/ProjectContext"
import { useToast } from "@/hooks/use-toast"
import { getProjects, addProject, updateProject, deleteProject } from "@/lib/supabase"

export function ProjectManagement() {
  const router = useRouter()
  const { user } = useAuth()
  const { selectedClient } = useClient()
  const { setSelectedProject: setContextProject } = useProject()
  const { toast } = useToast()
  const [projects, setProjects] = useState<Project[]>([])
  const [filteredProjects, setFilteredProjects] = useState<Project[]>([])
  const [searchTerm, setSearchTerm] = useState("")
  const [statusFilter, setStatusFilter] = useState<"all" | ProjectStatus>("all")
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false)
  const [selectedProject, setSelectedProject] = useState<Project | null>(null)
  const [projectToDelete, setProjectToDelete] = useState<Project | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchProjects = async () => {
    if (!selectedClient?.id) return

    setLoading(true)
    try {
      const { data, error } = await getProjects(selectedClient.id, {
        search: searchTerm || undefined,
        status: statusFilter !== "all" ? statusFilter : undefined,
      })

      if (error) {
        toast({
          title: "Error",
          description: error.message,
          variant: "destructive",
        })
        setProjects([])
        setFilteredProjects([])
      } else {
        setProjects(data)
        filterProjectsLocally(data, searchTerm, statusFilter)
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to fetch projects",
        variant: "destructive",
      })
      setProjects([])
      setFilteredProjects([])
    } finally {
      setLoading(false)
    }
  }

  const filterProjectsLocally = (
    projectList: Project[],
    search: string,
    status: "all" | ProjectStatus
  ) => {
    let filtered = projectList

    if (search) {
      filtered = filtered.filter(
        (project) =>
          project.name.toLowerCase().includes(search.toLowerCase()) ||
          project.description?.toLowerCase().includes(search.toLowerCase())
      )
    }

    if (status !== "all") {
      filtered = filtered.filter((project) => project.status === status)
    }

    setFilteredProjects(filtered)
  }

  useEffect(() => {
    if (selectedClient?.id) {
      fetchProjects()
    }
  }, [selectedClient?.id])

  useEffect(() => {
    filterProjectsLocally(projects, searchTerm, statusFilter)
  }, [searchTerm, statusFilter, projects])

  const handleSearch = (term: string) => {
    setSearchTerm(term)
  }

  const handleStatusFilter = (status: "all" | ProjectStatus) => {
    setStatusFilter(status)
  }

  const handleAddProject = () => {
    setSelectedProject(null)
    setIsModalOpen(true)
  }

  const handleEditProject = (project: Project) => {
    setSelectedProject(project)
    setIsModalOpen(true)
  }

  const handleDeleteProject = (project: Project) => {
    setProjectToDelete(project)
    setIsDeleteModalOpen(true)
  }

  const handleViewProject = (project: Project) => {
    setContextProject(project)
    router.push(`/clients/${selectedClient?.id}/projects/${project.id}/assessment`)
  }

  const handleSaveProject = async (formData: CreateProjectData | UpdateProjectData) => {
    if (!user?.id || !selectedClient?.id) return

    try {
      if (selectedProject) {
        // Update existing project
        const { data: updatedProject, error } = await updateProject(selectedProject.id, formData)
        if (error) {
          toast({
            title: "Error",
            description: error.message,
            variant: "destructive",
          })
        } else if (updatedProject) {
          toast({
            title: "Success",
            description: "Project updated successfully",
          })
          setIsModalOpen(false)
          setSelectedProject(null)
          fetchProjects()
        }
      } else {
        // Create new project
        const { data: newProject, error } = await addProject(
          selectedClient.id,
          user.id,
          formData as CreateProjectData
        )
        if (error) {
          toast({
            title: "Error",
            description: error.message,
            variant: "destructive",
          })
        } else if (newProject) {
          toast({
            title: "Success",
            description: "Project created successfully",
          })
          setIsModalOpen(false)
          fetchProjects()
        }
      }
    } catch (error) {
      toast({
        title: "Error",
        description: selectedProject ? "Failed to update project" : "Failed to create project",
        variant: "destructive",
      })
    }
  }

  const confirmDelete = async () => {
    if (!projectToDelete) return

    try {
      const { error } = await deleteProject(projectToDelete.id)
      if (error) {
        toast({
          title: "Error",
          description: error.message,
          variant: "destructive",
        })
      } else {
        toast({
          title: "Success",
          description: "Project deleted successfully",
        })
        setIsDeleteModalOpen(false)
        setProjectToDelete(null)
        fetchProjects()
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to delete project",
        variant: "destructive",
      })
    }
  }

  const stats = {
    total: projects.length,
    started: projects.filter((p) => p.status === "started").length,
    onGoing: projects.filter((p) => p.status === "on-going").length,
    completed: projects.filter((p) => p.status === "completed").length,
  }

  if (!selectedClient) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <FolderKanban className="h-12 w-12 text-slate-400 mb-4" />
        <p className="text-slate-400 text-lg">No client selected</p>
        <button
          onClick={() => router.push("/clients")}
          className="mt-4 flex items-center gap-2 text-purple-400 hover:text-purple-300 hover:underline transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Go to Clients</span>
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Back Button */}
      <button
        onClick={() => router.push("/clients")}
        className="flex items-center gap-2 px-4 py-2.5 bg-[#0f1016]/80 backdrop-blur-md border border-white/10 rounded-lg text-slate-300 hover:text-white hover:bg-white/10 transition-all shadow-lg hover:shadow-xl hover:border-purple-500/30 group w-fit"
        title="Back to Clients"
      >
        <ArrowLeft className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" />
        <span className="text-sm font-medium">Back</span>
      </button>

      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">
            Projects
          </h1>
          <p className="text-slate-400 mt-1">
            Manage projects for <span className="font-medium text-white">{selectedClient.name}</span>
          </p>
        </div>
        <button
          onClick={handleAddProject}
          className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white rounded-lg font-medium transition-all shadow-lg shadow-purple-500/20"
        >
          <Plus className="w-5 h-5" />
          <span>Add Project</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
        <StatusCard label="Total Projects" value={loading ? 0 : stats.total} color="cyan" />
        <StatusCard label="Started" value={loading ? 0 : stats.started} color="orange" />
        <StatusCard label="On-going" value={loading ? 0 : stats.onGoing} color="blue" />
        <StatusCard label="Completed" value={loading ? 0 : stats.completed} color="green" />
      </div>

      {loading ? (
        <div className="flex justify-center items-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
        </div>
      ) : (
        <ProjectTable
          projects={filteredProjects}
          onView={handleViewProject}
          onEdit={handleEditProject}
          onDelete={handleDeleteProject}
          searchTerm={searchTerm}
          onSearchChange={handleSearch}
          statusFilter={statusFilter}
          onStatusFilterChange={handleStatusFilter}
        />
      )}

      <ProjectModal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false)
          setSelectedProject(null)
        }}
        onSave={handleSaveProject}
        project={selectedProject}
      />

      <DeleteConfirmation
        isOpen={isDeleteModalOpen}
        onClose={() => {
          setIsDeleteModalOpen(false)
          setProjectToDelete(null)
        }}
        onConfirm={confirmDelete}
        project={projectToDelete}
      />
    </div>
  )
}
