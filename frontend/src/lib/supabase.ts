import { createClient } from '@supabase/supabase-js'
import type { Client, CreateClientData, UpdateClientData, ClientFilters } from '@/types/client'
import type { Project, CreateProjectData, UpdateProjectData, ProjectFilters } from '@/types/project'
import type { ProjectDocument, CreateDocumentData } from '@/types/document'
import type { ClientMemberRole } from '@/types/client-member'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
  || process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY!

if (!supabaseUrl || !supabaseKey) {
  console.error('Missing Supabase environment variables!')
  console.error('NEXT_PUBLIC_SUPABASE_URL:', supabaseUrl ? 'Set' : 'Missing')
  console.error('NEXT_PUBLIC_SUPABASE_ANON_KEY or NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY:', supabaseKey ? 'Set' : 'Missing')
}

export const supabase = createClient(supabaseUrl, supabaseKey)

/**
 * Sanitize user input for use in PostgREST filter expressions.
 * Strips characters that are meaningful in the filter DSL (commas, dots, parens)
 * to prevent filter injection.
 */
function sanitizeFilterInput(input: string): string {
  return input.replace(/[.,()]/g, '')
}

/**
 * Extended Client type that includes the user's role (from membership)
 */
export interface ClientWithRole extends Client {
  my_role?: ClientMemberRole
}

// Profile types
export interface Profile {
  id: string
  email: string
  full_name: string | null
  organization: string | null
  phone: string | null
  job_title: string | null
  role: string
  created_at: string
  updated_at: string
}

// Profile helper functions
export async function getProfile(userId: string): Promise<Profile | null> {
  const { data, error } = await supabase
    .from('profiles')
    .select('*')
    .eq('id', userId)
    .single()

  if (error) {
    console.error('Error fetching profile:', error)
    return null
  }

  return data
}

export async function updateProfile(
  userId: string,
  updates: Partial<Omit<Profile, 'id' | 'email' | 'created_at' | 'updated_at'>>
): Promise<{ data: Profile | null; error: Error | null }> {
  const { data, error } = await supabase
    .from('profiles')
    .update(updates)
    .eq('id', userId)
    .select()
    .single()

  return {
    data,
    error: error ? new Error(error.message) : null,
  }
}

// Client helper functions
// Note: RLS now handles visibility via client_members table
// Users see clients they are members of (any role)
export async function getClients(
  userId: string,
  filters?: ClientFilters
): Promise<{ data: ClientWithRole[]; error: Error | null }> {
  // Query clients - RLS will filter to only those user is a member of
  // We also fetch the user's membership to include their role
  let query = supabase
    .from('clients')
    .select(`
      *,
      client_members!inner (
        role,
        user_id
      )
    `)
    .eq('client_members.user_id', userId)
    .order('created_at', { ascending: false })

  // Apply search filter (sanitize to prevent PostgREST filter injection)
  if (filters?.search) {
    const s = sanitizeFilterInput(filters.search)
    query = query.or(`name.ilike.%${s}%,company.ilike.%${s}%,email.ilike.%${s}%`)
  }

  // Apply status filter
  if (filters?.status && filters.status !== 'all') {
    query = query.eq('status', filters.status)
  }

  const { data, error } = await query

  if (error) {
    return {
      data: [],
      error: new Error(error.message),
    }
  }

  // Transform to include my_role at top level
  const clientsWithRole: ClientWithRole[] = (data || []).map((item: Record<string, unknown>) => {
    const { client_members, ...clientData } = item
    const membership = Array.isArray(client_members) ? client_members[0] : client_members
    return {
      ...clientData,
      my_role: membership?.role as ClientMemberRole,
    } as ClientWithRole
  })

  return {
    data: clientsWithRole,
    error: null,
  }
}

/**
 * Get clients the user owns (for backwards compatibility)
 * Use this when you specifically need only owned clients
 */
export async function getOwnedClients(
  userId: string,
  filters?: ClientFilters
): Promise<{ data: Client[]; error: Error | null }> {
  let query = supabase
    .from('clients')
    .select(`
      *,
      client_members!inner (
        role,
        user_id
      )
    `)
    .eq('client_members.user_id', userId)
    .eq('client_members.role', 'owner')
    .order('created_at', { ascending: false })

  // Apply search filter (sanitize to prevent PostgREST filter injection)
  if (filters?.search) {
    const s = sanitizeFilterInput(filters.search)
    query = query.or(`name.ilike.%${s}%,company.ilike.%${s}%,email.ilike.%${s}%`)
  }

  // Apply status filter
  if (filters?.status && filters.status !== 'all') {
    query = query.eq('status', filters.status)
  }

  const { data, error } = await query

  if (error) {
    return {
      data: [],
      error: new Error(error.message),
    }
  }

  // Strip out client_members from response
  const clients: Client[] = (data || []).map((item: Record<string, unknown>) => {
    const { client_members, ...clientData } = item
    return clientData as unknown as Client
  })

  return {
    data: clients,
    error: null,
  }
}

export async function getClient(
  clientId: string
): Promise<{ data: Client | null; error: Error | null }> {
  const { data, error } = await supabase
    .from('clients')
    .select('*')
    .eq('id', clientId)
    .single()

  return {
    data,
    error: error ? new Error(error.message) : null,
  }
}

export async function addClient(
  userId: string,
  clientData: CreateClientData
): Promise<{ data: Client | null; error: Error | null }> {
  const { data, error } = await supabase
    .from('clients')
    .insert({
      user_id: userId,
      ...clientData,
    })
    .select()
    .single()

  return {
    data,
    error: error ? new Error(error.message) : null,
  }
}

export async function updateClient(
  clientId: string,
  updates: UpdateClientData
): Promise<{ data: Client | null; error: Error | null }> {
  const { data, error } = await supabase
    .from('clients')
    .update(updates)
    .eq('id', clientId)
    .select()
    .single()

  return {
    data,
    error: error ? new Error(error.message) : null,
  }
}

export async function deleteClient(
  clientId: string
): Promise<{ error: Error | null }> {
  const { error } = await supabase
    .from('clients')
    .delete()
    .eq('id', clientId)

  return {
    error: error ? new Error(error.message) : null,
  }
}

// Project helper functions
export async function getProject(
  projectId: string
): Promise<{ data: Project | null; error: Error | null }> {
  const { data, error } = await supabase
    .from('projects')
    .select('*')
    .eq('id', projectId)
    .single()

  return {
    data,
    error: error ? new Error(error.message) : null,
  }
}

export async function getProjects(
  clientId: string,
  filters?: ProjectFilters
): Promise<{ data: Project[]; error: Error | null }> {
  let query = supabase
    .from('projects')
    .select('*')
    .eq('client_id', clientId)
    .order('created_at', { ascending: false })

  // Apply search filter (sanitize to prevent PostgREST filter injection)
  if (filters?.search) {
    const s = sanitizeFilterInput(filters.search)
    query = query.or(`name.ilike.%${s}%,description.ilike.%${s}%`)
  }

  // Apply status filter
  if (filters?.status && filters.status !== 'all') {
    query = query.eq('status', filters.status)
  }

  const { data, error } = await query

  return {
    data: data || [],
    error: error ? new Error(error.message) : null,
  }
}

export async function addProject(
  clientId: string,
  userId: string,
  projectData: CreateProjectData
): Promise<{ data: Project | null; error: Error | null }> {
  const { data, error } = await supabase
    .from('projects')
    .insert({
      client_id: clientId,
      user_id: userId,
      ...projectData,
    })
    .select()
    .single()

  return {
    data,
    error: error ? new Error(error.message) : null,
  }
}

export async function updateProject(
  projectId: string,
  updates: UpdateProjectData
): Promise<{ data: Project | null; error: Error | null }> {
  const { data, error } = await supabase
    .from('projects')
    .update(updates)
    .eq('id', projectId)
    .select()
    .single()

  return {
    data,
    error: error ? new Error(error.message) : null,
  }
}

export async function deleteProject(
  projectId: string
): Promise<{ error: Error | null }> {
  const { error } = await supabase
    .from('projects')
    .delete()
    .eq('id', projectId)

  return {
    error: error ? new Error(error.message) : null,
  }
}

// Project Document helper functions
export async function getProjectDocuments(
  projectId: string
): Promise<{ data: ProjectDocument[]; error: Error | null }> {
  const { data, error } = await supabase
    .from('project_documents')
    .select('*')
    .eq('project_id', projectId)
    .order('created_at', { ascending: false })

  return {
    data: data || [],
    error: error ? new Error(error.message) : null,
  }
}

export async function addProjectDocument(
  projectId: string,
  clientId: string,
  userId: string,
  documentData: CreateDocumentData
): Promise<{ data: ProjectDocument | null; error: Error | null }> {
  const { data, error } = await supabase
    .from('project_documents')
    .insert({
      project_id: projectId,
      client_id: clientId,
      user_id: userId,
      ...documentData,
    })
    .select()
    .single()

  return {
    data,
    error: error ? new Error(error.message) : null,
  }
}

export async function deleteProjectDocument(
  documentId: string
): Promise<{ error: Error | null }> {
  const { error } = await supabase
    .from('project_documents')
    .delete()
    .eq('id', documentId)

  return {
    error: error ? new Error(error.message) : null,
  }
}
