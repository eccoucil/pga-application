"use client"

import React, { createContext, useContext, useState, useCallback, useEffect } from "react"
import { useAuth } from "./AuthContext"
import { useClient } from "./ClientContext"
import { supabase } from "@/lib/supabase"
import type {
  ClientMember,
  ClientMemberRole,
  ClientMemberPermissions,
  ListMembersResponse,
  InviteMemberRequest,
  InviteMemberResponse,
  UpdateMemberRoleResponse,
  RemoveMemberResponse,
} from "@/types/client-member"

interface ClientMembershipContextType {
  // Current user's role and permissions for the selected client
  currentRole: ClientMemberRole | null
  permissions: ClientMemberPermissions | null
  isLoadingRole: boolean

  // Team members
  teamMembers: ClientMember[]
  isLoadingMembers: boolean

  // Permission convenience methods
  canView: boolean
  canWrite: boolean
  canManage: boolean
  isOwner: boolean

  // Actions
  fetchMyRole: (clientId: string) => Promise<void>
  fetchTeamMembers: (clientId: string) => Promise<void>
  inviteMember: (clientId: string, request: InviteMemberRequest) => Promise<InviteMemberResponse>
  updateMemberRole: (clientId: string, memberId: string, role: ClientMemberRole) => Promise<UpdateMemberRoleResponse>
  removeMember: (clientId: string, memberId: string) => Promise<RemoveMemberResponse>
  acceptInvitation: (clientId: string) => Promise<{ success: boolean; message: string }>

  // Clear state
  clearMembership: () => void
}

const ClientMembershipContext = createContext<ClientMembershipContextType | undefined>(undefined)

export function ClientMembershipProvider({ children }: { children: React.ReactNode }) {
  const { session } = useAuth()
  const { selectedClient } = useClient()

  const [currentRole, setCurrentRole] = useState<ClientMemberRole | null>(null)
  const [permissions, setPermissions] = useState<ClientMemberPermissions | null>(null)
  const [isLoadingRole, setIsLoadingRole] = useState(false)

  const [teamMembers, setTeamMembers] = useState<ClientMember[]>([])
  const [isLoadingMembers, setIsLoadingMembers] = useState(false)

  // Helper function to calculate permissions from role
  const getPermissionsFromRole = useCallback((role: ClientMemberRole | null): ClientMemberPermissions | null => {
    if (!role) return null
    
    return {
      can_view: true, // All roles can view
      can_write: role === "owner" || role === "admin" || role === "member",
      can_manage: role === "owner" || role === "admin",
      is_owner: role === "owner",
    }
  }, [])

  // Fetch current user's role for a client
  const fetchMyRole = useCallback(async (clientId: string) => {
    if (!session?.user?.id) {
      setCurrentRole(null)
      setPermissions(null)
      return
    }

    setIsLoadingRole(true)
    try {
      const { data, error } = await supabase
        .from("client_members")
        .select("*")
        .eq("client_id", clientId)
        .eq("user_id", session.user.id)
        .maybeSingle()

      if (error) {
        console.error("Error fetching role:", error)
        setCurrentRole(null)
        setPermissions(null)
        return
      }

      if (!data) {
        // Not a member
        setCurrentRole(null)
        setPermissions(null)
        return
      }

      const role = data.role as ClientMemberRole
      setCurrentRole(role)
      setPermissions(getPermissionsFromRole(role))
    } catch (error) {
      console.error("Error fetching role:", error)
      setCurrentRole(null)
      setPermissions(null)
    } finally {
      setIsLoadingRole(false)
    }
  }, [session, getPermissionsFromRole])

  // Fetch team members for a client
  const fetchTeamMembers = useCallback(async (clientId: string) => {
    if (!session?.user?.id) {
      setTeamMembers([])
      return
    }

    setIsLoadingMembers(true)
    try {
      // Fetch members
      const { data: membersData, error: membersError } = await supabase
        .from("client_members")
        .select("*")
        .eq("client_id", clientId)
        .order("created_at", { ascending: false })

      if (membersError) {
        throw new Error(membersError.message)
      }

      // Get current user's role
      const { data: myMembership } = await supabase
        .from("client_members")
        .select("role")
        .eq("client_id", clientId)
        .eq("user_id", session.user.id)
        .maybeSingle()

      // Fetch profile data for all members
      const userIds = (membersData || []).map((m: any) => m.user_id)
      const { data: profilesData } = await supabase
        .from("profiles")
        .select("id, email, full_name")
        .in("id", userIds)

      // Create a map of user_id -> profile
      const profilesMap = new Map(
        (profilesData || []).map((p: any) => [p.id, p])
      )

      // Transform data to match ClientMember interface
      const members: ClientMember[] = (membersData || []).map((item: any) => {
        const profile = profilesMap.get(item.user_id)
        return {
          id: item.id,
          client_id: item.client_id,
          user_id: item.user_id,
          role: item.role as ClientMemberRole,
          email: profile?.email || null,
          full_name: profile?.full_name || null,
          invited_by: item.invited_by,
          invited_at: item.invited_at,
          accepted_at: item.accepted_at,
          created_at: item.created_at,
        }
      })

      setTeamMembers(members)
      
      if (myMembership) {
        const role = myMembership.role as ClientMemberRole
        setCurrentRole(role)
        setPermissions(getPermissionsFromRole(role))
      }
    } catch (error) {
      console.error("Error fetching team members:", error)
      setTeamMembers([])
    } finally {
      setIsLoadingMembers(false)
    }
  }, [session, getPermissionsFromRole])

  // Invite a new member
  const inviteMember = useCallback(async (
    clientId: string,
    request: InviteMemberRequest
  ): Promise<InviteMemberResponse> => {
    if (!session?.user?.id) {
      throw new Error("Not authenticated")
    }

    // First, find the user by email
    const { data: userData, error: userError } = await supabase
      .from("profiles")
      .select("id")
      .eq("email", request.email)
      .maybeSingle()

    if (userError || !userData) {
      throw new Error(`User with email ${request.email} not found`)
    }

    // Check if user is already a member
    const { data: existingMember } = await supabase
      .from("client_members")
      .select("id")
      .eq("client_id", clientId)
      .eq("user_id", userData.id)
      .maybeSingle()

    if (existingMember) {
      throw new Error("User is already a member of this client")
    }

    // Insert new membership
    const { data: membershipData, error: insertError } = await supabase
      .from("client_members")
      .insert({
        client_id: clientId,
        user_id: userData.id,
        role: request.role,
        invited_by: session.user.id,
      })
      .select()
      .single()

    if (insertError) {
      throw new Error(insertError.message || "Failed to invite member")
    }

    // Refresh team members
    await fetchTeamMembers(clientId)

    return {
      success: true,
      membership_id: membershipData.id,
      message: `Successfully invited ${request.email} as ${request.role}`,
      invited_email: request.email,
      assigned_role: request.role,
    }
  }, [session, fetchTeamMembers])

  // Update a member's role
  const updateMemberRole = useCallback(async (
    clientId: string,
    memberId: string,
    role: ClientMemberRole
  ): Promise<UpdateMemberRoleResponse> => {
    // Get current membership to check old role
    const { data: currentMember, error: fetchError } = await supabase
      .from("client_members")
      .select("role")
      .eq("id", memberId)
      .eq("client_id", clientId)
      .single()

    if (fetchError || !currentMember) {
      throw new Error("Member not found")
    }

    const oldRole = currentMember.role as ClientMemberRole

    // Update role
    const { data: updatedMember, error: updateError } = await supabase
      .from("client_members")
      .update({ role })
      .eq("id", memberId)
      .eq("client_id", clientId)
      .select()
      .single()

    if (updateError) {
      throw new Error(updateError.message || "Failed to update member role")
    }

    // Refresh team members
    await fetchTeamMembers(clientId)

    return {
      success: true,
      membership_id: updatedMember.id,
      old_role: oldRole,
      new_role: role,
      message: `Successfully updated role from ${oldRole} to ${role}`,
    }
  }, [fetchTeamMembers])

  // Remove a member
  const removeMember = useCallback(async (
    clientId: string,
    memberId: string
  ): Promise<RemoveMemberResponse> => {
    const { error } = await supabase
      .from("client_members")
      .delete()
      .eq("id", memberId)
      .eq("client_id", clientId)

    if (error) {
      throw new Error(error.message || "Failed to remove member")
    }

    // Refresh team members
    await fetchTeamMembers(clientId)

    return {
      success: true,
      message: "Member removed successfully",
    }
  }, [fetchTeamMembers])

  // Accept an invitation
  const acceptInvitation = useCallback(async (
    clientId: string
  ): Promise<{ success: boolean; message: string }> => {
    if (!session?.user?.id) {
      throw new Error("Not authenticated")
    }

    const { error } = await supabase
      .from("client_members")
      .update({ accepted_at: new Date().toISOString() })
      .eq("client_id", clientId)
      .eq("user_id", session.user.id)
      .is("accepted_at", null)

    if (error) {
      throw new Error(error.message || "Failed to accept invitation")
    }

    // Refresh role
    await fetchMyRole(clientId)

    return {
      success: true,
      message: "Invitation accepted successfully",
    }
  }, [session, fetchMyRole])

  // Clear membership state
  const clearMembership = useCallback(() => {
    setCurrentRole(null)
    setPermissions(null)
    setTeamMembers([])
  }, [])

  // Auto-fetch role when selected client changes
  useEffect(() => {
    if (selectedClient && session) {
      fetchMyRole(selectedClient.id)
    } else {
      clearMembership()
    }
  }, [selectedClient, session, fetchMyRole, clearMembership])

  // Convenience permission flags
  const canView = permissions?.can_view ?? false
  const canWrite = permissions?.can_write ?? false
  const canManage = permissions?.can_manage ?? false
  const isOwner = permissions?.is_owner ?? false

  return (
    <ClientMembershipContext.Provider
      value={{
        currentRole,
        permissions,
        isLoadingRole,
        teamMembers,
        isLoadingMembers,
        canView,
        canWrite,
        canManage,
        isOwner,
        fetchMyRole,
        fetchTeamMembers,
        inviteMember,
        updateMemberRole,
        removeMember,
        acceptInvitation,
        clearMembership,
      }}
    >
      {children}
    </ClientMembershipContext.Provider>
  )
}

export function useClientMembership() {
  const context = useContext(ClientMembershipContext)
  if (context === undefined) {
    throw new Error("useClientMembership must be used within a ClientMembershipProvider")
  }
  return context
}
