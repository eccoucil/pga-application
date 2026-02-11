"use client"

import { useState, useEffect } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Users,
  UserPlus,
  Crown,
  Shield,
  User,
  Eye,
  MoreVertical,
  Trash2,
  Loader2,
} from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu"
import { useToast } from "@/hooks/use-toast"
import { useClientMembership } from "@/contexts/ClientMembershipContext"
import type { Client } from "@/types/client"
import type { ClientMember, ClientMemberRole } from "@/types/client-member"
import { getRoleDisplayName, getRoleDescription } from "@/types/client-member"

interface TeamMembersDialogProps {
  client: Client | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

const roleIcons: Record<ClientMemberRole, React.ElementType> = {
  owner: Crown,
  admin: Shield,
  member: User,
  viewer: Eye,
}

const roleColors: Record<ClientMemberRole, string> = {
  owner: "text-yellow-400 bg-yellow-400/10 border-yellow-500/20",
  admin: "text-purple-400 bg-purple-400/10 border-purple-500/20",
  member: "text-cyan-400 bg-cyan-400/10 border-cyan-500/20",
  viewer: "text-slate-400 bg-slate-400/10 border-slate-500/20",
}

export function TeamMembersDialog({
  client,
  open,
  onOpenChange,
}: TeamMembersDialogProps) {
  const { toast } = useToast()
  const {
    teamMembers,
    isLoadingMembers,
    currentRole,
    canManage,
    isOwner,
    fetchTeamMembers,
    inviteMember,
    updateMemberRole,
    removeMember,
  } = useClientMembership()

  const [showInviteForm, setShowInviteForm] = useState(false)
  const [inviteEmail, setInviteEmail] = useState("")
  const [inviteRole, setInviteRole] = useState<Exclude<ClientMemberRole, 'owner'>>("member")
  const [isInviting, setIsInviting] = useState(false)
  const [isUpdating, setIsUpdating] = useState<string | null>(null)

  // Fetch team members when dialog opens
  useEffect(() => {
    if (open && client) {
      fetchTeamMembers(client.id)
    }
  }, [open, client, fetchTeamMembers])

  // Reset invite form when dialog closes
  useEffect(() => {
    if (!open) {
      setShowInviteForm(false)
      setInviteEmail("")
      setInviteRole("member")
    }
  }, [open])

  if (!client) return null

  const handleInvite = async () => {
    if (!inviteEmail.trim()) {
      toast({
        title: "Error",
        description: "Please enter an email address",
        variant: "destructive",
      })
      return
    }

    setIsInviting(true)
    try {
      const result = await inviteMember(client.id, {
        email: inviteEmail.trim(),
        role: inviteRole,
      })

      toast({
        title: "Member Invited",
        description: result.message,
      })

      setShowInviteForm(false)
      setInviteEmail("")
      setInviteRole("member")
    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to invite member",
        variant: "destructive",
      })
    } finally {
      setIsInviting(false)
    }
  }

  const handleRoleChange = async (memberId: string, newRole: ClientMemberRole) => {
    setIsUpdating(memberId)
    try {
      const result = await updateMemberRole(client.id, memberId, newRole)

      toast({
        title: "Role Updated",
        description: result.message,
      })
    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to update role",
        variant: "destructive",
      })
    } finally {
      setIsUpdating(null)
    }
  }

  const handleRemoveMember = async (member: ClientMember) => {
    const isMe = member.user_id === teamMembers.find(m => m.role === currentRole)?.user_id

    setIsUpdating(member.id)
    try {
      const result = await removeMember(client.id, member.id)

      toast({
        title: isMe ? "Left Client" : "Member Removed",
        description: result.message,
      })

      if (isMe) {
        onOpenChange(false)
      }
    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to remove member",
        variant: "destructive",
      })
    } finally {
      setIsUpdating(null)
    }
  }

  const RoleBadge = ({ role }: { role: ClientMemberRole }) => {
    const Icon = roleIcons[role]
    return (
      <span
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${roleColors[role]}`}
        title={getRoleDescription(role)}
      >
        <Icon className="h-3 w-3" />
        {getRoleDisplayName(role)}
      </span>
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Users className="h-5 w-5 text-cyan-400" />
            Team Members
          </DialogTitle>
          <DialogDescription>
            Manage who has access to {client.name}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Invite Button / Form */}
          {canManage && (
            <div className="border border-slate-700 rounded-lg p-4">
              {!showInviteForm ? (
                <Button
                  variant="outline"
                  className="w-full border-dashed border-slate-600 text-slate-400 hover:text-white hover:border-cyan-500/50"
                  onClick={() => setShowInviteForm(true)}
                >
                  <UserPlus className="h-4 w-4 mr-2" />
                  Invite Team Member
                </Button>
              ) : (
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="invite-email">Email Address</Label>
                    <Input
                      id="invite-email"
                      type="email"
                      placeholder="colleague@company.com"
                      value={inviteEmail}
                      onChange={(e) => setInviteEmail(e.target.value)}
                      className="bg-slate-800 border-slate-700"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="invite-role">Role</Label>
                    <Select
                      value={inviteRole}
                      onValueChange={(value) => setInviteRole(value as Exclude<ClientMemberRole, 'owner'>)}
                    >
                      <SelectTrigger className="bg-slate-800 border-slate-700">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="viewer">
                          <div className="flex items-center gap-2">
                            <Eye className="h-4 w-4 text-slate-400" />
                            <span>Viewer</span>
                            <span className="text-xs text-slate-500">- Read only</span>
                          </div>
                        </SelectItem>
                        <SelectItem value="member">
                          <div className="flex items-center gap-2">
                            <User className="h-4 w-4 text-cyan-400" />
                            <span>Member</span>
                            <span className="text-xs text-slate-500">- Can edit</span>
                          </div>
                        </SelectItem>
                        <SelectItem value="admin">
                          <div className="flex items-center gap-2">
                            <Shield className="h-4 w-4 text-purple-400" />
                            <span>Admin</span>
                            <span className="text-xs text-slate-500">- Can manage team</span>
                          </div>
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="flex gap-2 justify-end">
                    <Button
                      variant="outline"
                      onClick={() => {
                        setShowInviteForm(false)
                        setInviteEmail("")
                        setInviteRole("member")
                      }}
                      className="border-slate-700"
                    >
                      Cancel
                    </Button>
                    <Button
                      variant="cyber"
                      onClick={handleInvite}
                      disabled={isInviting || !inviteEmail.trim()}
                    >
                      {isInviting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                      Send Invite
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Members List */}
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-slate-400">
              {teamMembers.length} {teamMembers.length === 1 ? "Member" : "Members"}
            </h4>

            {isLoadingMembers ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
              </div>
            ) : teamMembers.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                No team members found
              </div>
            ) : (
              <div className="space-y-2">
                {teamMembers.map((member) => {
                  const isSelf = member.role === currentRole && teamMembers.filter(m => m.role === currentRole).length === 1
                  const canModify = isOwner || (canManage && member.role !== "owner")

                  return (
                    <div
                      key={member.id}
                      className="flex items-center justify-between p-3 rounded-lg bg-slate-800/50 border border-slate-700"
                    >
                      <div className="flex items-center gap-3">
                        <div className="h-10 w-10 rounded-full bg-slate-700 flex items-center justify-center">
                          <User className="h-5 w-5 text-slate-400" />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-white">
                            {member.full_name || member.email || "Unknown User"}
                          </p>
                          {member.full_name && member.email && (
                            <p className="text-xs text-slate-500">{member.email}</p>
                          )}
                          {!member.accepted_at && member.role !== "owner" && (
                            <p className="text-xs text-yellow-500">Pending invitation</p>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <RoleBadge role={member.role} />

                        {canModify && (
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 w-8 p-0 text-slate-400 hover:text-white"
                                disabled={isUpdating === member.id}
                              >
                                {isUpdating === member.id ? (
                                  <Loader2 className="h-4 w-4 animate-spin" />
                                ) : (
                                  <MoreVertical className="h-4 w-4" />
                                )}
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end" className="bg-slate-800 border-slate-700">
                              {member.role !== "owner" && (
                                <>
                                  <DropdownMenuItem
                                    onClick={() => handleRoleChange(member.id, "viewer")}
                                    disabled={member.role === "viewer"}
                                    className="text-slate-300 focus:text-white"
                                  >
                                    <Eye className="h-4 w-4 mr-2 text-slate-400" />
                                    Set as Viewer
                                  </DropdownMenuItem>
                                  <DropdownMenuItem
                                    onClick={() => handleRoleChange(member.id, "member")}
                                    disabled={member.role === "member"}
                                    className="text-slate-300 focus:text-white"
                                  >
                                    <User className="h-4 w-4 mr-2 text-cyan-400" />
                                    Set as Member
                                  </DropdownMenuItem>
                                  <DropdownMenuItem
                                    onClick={() => handleRoleChange(member.id, "admin")}
                                    disabled={member.role === "admin"}
                                    className="text-slate-300 focus:text-white"
                                  >
                                    <Shield className="h-4 w-4 mr-2 text-purple-400" />
                                    Set as Admin
                                  </DropdownMenuItem>
                                  {isOwner && (
                                    <DropdownMenuItem
                                      onClick={() => handleRoleChange(member.id, "owner")}
                                      className="text-yellow-400 focus:text-yellow-300"
                                    >
                                      <Crown className="h-4 w-4 mr-2" />
                                      Transfer Ownership
                                    </DropdownMenuItem>
                                  )}
                                  <DropdownMenuSeparator className="bg-slate-700" />
                                </>
                              )}
                              {member.role !== "owner" && (
                                <DropdownMenuItem
                                  onClick={() => handleRemoveMember(member)}
                                  className="text-red-400 focus:text-red-300"
                                >
                                  <Trash2 className="h-4 w-4 mr-2" />
                                  Remove Member
                                </DropdownMenuItem>
                              )}
                            </DropdownMenuContent>
                          </DropdownMenu>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Role Legend */}
          <div className="border-t border-slate-700 pt-4">
            <h4 className="text-xs font-medium text-slate-500 mb-2">ROLE PERMISSIONS</h4>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="flex items-center gap-2 text-slate-400">
                <Crown className="h-3 w-3 text-yellow-400" />
                <span>Owner: Full control</span>
              </div>
              <div className="flex items-center gap-2 text-slate-400">
                <Shield className="h-3 w-3 text-purple-400" />
                <span>Admin: Manage team</span>
              </div>
              <div className="flex items-center gap-2 text-slate-400">
                <User className="h-3 w-3 text-cyan-400" />
                <span>Member: Create & edit</span>
              </div>
              <div className="flex items-center gap-2 text-slate-400">
                <Eye className="h-3 w-3 text-slate-400" />
                <span>Viewer: Read only</span>
              </div>
            </div>
          </div>
        </div>

        <div className="flex justify-end">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            className="border-slate-700 text-slate-300 hover:bg-slate-800 hover:text-white"
          >
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
