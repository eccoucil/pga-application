"use client"

import { createContext, useContext, useState, useEffect, ReactNode } from "react"
import { usePathname } from "next/navigation"
import type { Project } from "@/types/project"

interface ProjectContextType {
  selectedProject: Project | null
  setSelectedProject: (project: Project | null) => void
  clearSelectedProject: () => void
}

const ProjectContext = createContext<ProjectContextType | undefined>(undefined)

export function ProjectProvider({ children }: { children: ReactNode }) {
  const [selectedProject, setSelectedProject] = useState<Project | null>(null)
  const pathname = usePathname()

  // Clear selected project when navigating away from project-specific pages
  useEffect(() => {
    // Project pages follow pattern: /clients/[id]/projects/[projectId]
    // Check if we're on a specific project page (has 4+ path segments)
    const segments = pathname.split("/").filter(Boolean)
    const isProjectPage =
      segments.length >= 4 &&
      segments[0] === "clients" &&
      segments[2] === "projects" &&
      segments[3] !== undefined

    if (!isProjectPage) {
      setSelectedProject(null)
    }
  }, [pathname])

  const clearSelectedProject = () => {
    setSelectedProject(null)
  }

  return (
    <ProjectContext.Provider
      value={{
        selectedProject,
        setSelectedProject,
        clearSelectedProject,
      }}
    >
      {children}
    </ProjectContext.Provider>
  )
}

export function useProject() {
  const context = useContext(ProjectContext)
  if (context === undefined) {
    throw new Error("useProject must be used within a ProjectProvider")
  }
  return context
}
