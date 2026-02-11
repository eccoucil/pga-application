export interface Client {
  id: string
  user_id: string
  name: string
  company: string | null
  email: string | null
  phone: string | null
  address: string | null
  industry: string | null
  status: 'active' | 'inactive'
  created_at: string
  updated_at: string
}

export interface CreateClientData {
  name: string
  company?: string
  email?: string
  phone?: string
  address?: string
  industry?: string
  status?: 'active' | 'inactive'
}

export interface UpdateClientData {
  name?: string
  company?: string | null
  email?: string | null
  phone?: string | null
  address?: string | null
  industry?: string | null
  status?: 'active' | 'inactive'
}

export interface ClientFilters {
  search?: string
  status?: 'all' | 'active' | 'inactive'
}
