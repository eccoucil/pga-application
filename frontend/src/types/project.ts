export type ProjectStatus = 'started' | 'on-going' | 'completed'

export interface Project {
  id: string
  client_id: string
  user_id: string
  name: string
  description: string | null
  framework: string[] | null  // Array of frameworks, e.g., ["BNM RMIT", "ISO 27001:2022"]
  start_date: string | null
  end_date: string | null
  status: ProjectStatus
  created_at: string
  updated_at: string
}

export interface CreateProjectData {
  name: string
  description?: string
  framework?: string[]
  start_date?: string
  end_date?: string
  status?: ProjectStatus
}

export interface UpdateProjectData {
  name?: string
  description?: string | null
  framework?: string[] | null
  start_date?: string | null
  end_date?: string | null
  status?: ProjectStatus
}

export interface ProjectFilters {
  search?: string
  status?: 'all' | ProjectStatus
}

// Predefined framework options (without "Other" - handled separately)
export const FRAMEWORK_OPTIONS = [
  { value: 'BNM RMIT', label: 'BNM RMIT' },
  { value: 'ISO 27001:2022', label: 'ISO 27001:2022' },
] as const
