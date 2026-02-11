/**
 * Client Member types for multi-tenant team management.
 */

export type ClientMemberRole = 'owner' | 'admin' | 'member' | 'viewer'

export interface ClientMember {
  id: string
  client_id: string
  user_id: string
  role: ClientMemberRole
  email: string | null
  full_name: string | null
  invited_by: string | null
  invited_at: string | null
  accepted_at: string | null
  created_at: string
}

export interface ClientMemberPermissions {
  can_view: boolean
  can_write: boolean
  can_manage: boolean
  is_owner: boolean
}

export interface MyRoleResponse {
  client_id: string
  user_id: string
  role: ClientMemberRole
  permissions: ClientMemberPermissions
}

export interface ListMembersResponse {
  client_id: string
  members: ClientMember[]
  total: number
  current_user_role: ClientMemberRole
}

export interface InviteMemberRequest {
  email: string
  role: Exclude<ClientMemberRole, 'owner'>  // Cannot invite as owner
}

export interface InviteMemberResponse {
  success: boolean
  membership_id: string | null
  message: string
  invited_email: string
  assigned_role: ClientMemberRole
}

export interface UpdateMemberRoleRequest {
  role: ClientMemberRole
}

export interface UpdateMemberRoleResponse {
  success: boolean
  membership_id: string
  old_role: ClientMemberRole
  new_role: ClientMemberRole
  message: string
}

export interface RemoveMemberResponse {
  success: boolean
  message: string
}

/**
 * Helper to get role display name
 */
export function getRoleDisplayName(role: ClientMemberRole): string {
  const displayNames: Record<ClientMemberRole, string> = {
    owner: 'Owner',
    admin: 'Admin',
    member: 'Member',
    viewer: 'Viewer',
  }
  return displayNames[role] || role
}

/**
 * Helper to get role description
 */
export function getRoleDescription(role: ClientMemberRole): string {
  const descriptions: Record<ClientMemberRole, string> = {
    owner: 'Full control over the client and team',
    admin: 'Can manage team members and delete content',
    member: 'Can create and edit projects and documents',
    viewer: 'Read-only access to all content',
  }
  return descriptions[role] || ''
}

/**
 * Role hierarchy for comparison
 */
export const ROLE_HIERARCHY: Record<ClientMemberRole, number> = {
  viewer: 0,
  member: 1,
  admin: 2,
  owner: 3,
}

/**
 * Check if a role meets minimum requirement
 */
export function hasMinimumRole(
  userRole: ClientMemberRole,
  requiredRole: ClientMemberRole
): boolean {
  return ROLE_HIERARCHY[userRole] >= ROLE_HIERARCHY[requiredRole]
}
