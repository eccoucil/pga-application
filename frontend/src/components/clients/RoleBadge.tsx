"use client"

import { Crown, Shield, User, Eye } from "lucide-react"
import type { ClientMemberRole } from "@/types/client-member"
import { getRoleDisplayName, getRoleDescription } from "@/types/client-member"

interface RoleBadgeProps {
  role: ClientMemberRole
  size?: "sm" | "md"
  showLabel?: boolean
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

export function RoleBadge({ role, size = "sm", showLabel = true }: RoleBadgeProps) {
  const Icon = roleIcons[role]
  const iconSize = size === "sm" ? "h-3 w-3" : "h-4 w-4"
  const textSize = size === "sm" ? "text-xs" : "text-sm"
  const padding = size === "sm" ? "px-2 py-0.5" : "px-2.5 py-1"

  if (!showLabel) {
    return (
      <span
        className={`inline-flex items-center justify-center ${roleColors[role]} rounded-full p-1 border`}
        title={`${getRoleDisplayName(role)}: ${getRoleDescription(role)}`}
      >
        <Icon className={iconSize} />
      </span>
    )
  }

  return (
    <span
      className={`inline-flex items-center gap-1 ${padding} rounded-full ${textSize} font-medium border ${roleColors[role]}`}
      title={getRoleDescription(role)}
    >
      <Icon className={iconSize} />
      {getRoleDisplayName(role)}
    </span>
  )
}
