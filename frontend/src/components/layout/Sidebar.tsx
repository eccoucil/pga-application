"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { Users, Briefcase, Sun, Moon, ChevronDown, ShieldCheck, Landmark } from "lucide-react"
import { cn } from "@/lib/utils"
import { useClient } from "@/contexts/ClientContext"
import { useProject } from "@/contexts/ProjectContext"
import { useTheme } from "@/contexts/ThemeContext"
import { useAuth } from "@/contexts/AuthContext"

export function Sidebar() {
  const pathname = usePathname()
  const { selectedClient } = useClient()
  const { selectedProject } = useProject()
  const { darkMode, toggleDarkMode, mounted } = useTheme()
  const { user } = useAuth()

  const menuItems = [
    { icon: Users, label: "Clients", href: "/clients" },
    ...(selectedClient
      ? [
          {
            icon: Briefcase,
            label: "Projects",
            href: `/clients/${selectedClient.id}/projects`,
          },
        ]
      : []),
    ...(selectedClient && selectedProject?.framework?.includes("ISO 27001:2022")
      ? [
          {
            icon: ShieldCheck,
            label: "Controls",
            href: `/clients/${selectedClient.id}/projects/${selectedProject.id}/controls`,
          },
        ]
      : []),
    ...(selectedClient && selectedProject?.framework?.includes("BNM RMIT")
      ? [
          {
            icon: Landmark,
            label: "BNM RMIT",
            href: `/clients/${selectedClient.id}/projects/${selectedProject.id}/bnm-rmit`,
          },
        ]
      : []),
  ]

  const getUserInitials = () => {
    if (user?.email) {
      return user.email.charAt(0).toUpperCase()
    }
    return "U"
  }

  const getUserName = () => {
    if (user?.email) {
      return user.email.split("@")[0].replace(/[._]/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())
    }
    return "User"
  }

  return (
    <div className="w-64 h-screen bg-black/40 backdrop-blur-xl border-r border-white/10 flex flex-col text-slate-300 font-sans overflow-y-auto">
      {/* Logo */}
      <div className="p-6 flex items-center gap-3">
        <div className="relative">
          <div className="absolute inset-0 bg-purple-500 blur-lg opacity-40"></div>
          <ShieldCheck className="relative w-8 h-8 text-purple-500" />
        </div>
        <div>
          <h1 className="text-white font-bold text-lg leading-tight tracking-wide">PGA Portal</h1>
          <p className="text-xs text-purple-400/80 font-medium">Security Platform</p>
        </div>
      </div>

      {/* Organization */}
      {selectedClient && (
        <div className="px-4 mb-6">
          <div className="p-3 bg-white/[0.03] hover:bg-white/[0.05] transition-colors rounded-lg border border-white/5 cursor-pointer group">
            <p className="text-[10px] uppercase tracking-wider text-slate-500 mb-1 font-semibold group-hover:text-purple-400 transition-colors">Organization</p>
            <div className="flex items-center justify-between text-white font-medium">
              <span className="truncate">{selectedClient.name}</span>
              <ChevronDown className="w-4 h-4 text-slate-500 flex-shrink-0" />
            </div>
          </div>
        </div>
      )}

      {/* Project indicator */}
      {selectedProject && (
        <div className="px-4 mb-6">
          <div className="p-3 bg-white/[0.03] hover:bg-white/[0.05] transition-colors rounded-lg border border-white/5 cursor-pointer group">
            <p className="text-[10px] uppercase tracking-wider text-slate-500 mb-1 font-semibold group-hover:text-purple-400 transition-colors">Project</p>
            <div className="flex items-center justify-between text-white font-medium">
              <span className="truncate">{selectedProject.name}</span>
              <ChevronDown className="w-4 h-4 text-slate-500 flex-shrink-0" />
            </div>
          </div>
        </div>
      )}

      {/* Navigation */}
      <nav className="flex-1 px-2 space-y-1 overflow-y-auto">
        {menuItems.map((item) => {
          const isActive =
            pathname === item.href ||
            (item.href !== "/clients" && pathname.startsWith(item.href))

          return (
            <Link
              key={item.label}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-4 py-3 transition-colors group",
                isActive
                  ? "bg-purple-500/10 text-purple-300 border-l-2 border-purple-500 font-medium shadow-[0_0_20px_-5px_rgba(168,85,247,0.3)]"
                  : "text-slate-400 hover:text-white hover:bg-white/5"
              )}
            >
              <item.icon className={cn(
                "w-5 h-5",
                isActive ? "" : "group-hover:text-purple-400 transition-colors"
              )} />
              <span>{item.label}</span>
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-white/5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-purple-600 to-blue-600 flex items-center justify-center text-xs text-white font-bold ring-2 ring-white/10">
              {getUserInitials()}
            </div>
            <div className="text-sm">
              <p className="text-white font-medium truncate max-w-[120px]">{getUserName()}</p>
            </div>
          </div>
          <button
            onClick={toggleDarkMode}
            className="p-2 hover:bg-white/5 rounded-full text-slate-400 hover:text-white transition-colors"
            aria-label="Toggle dark mode"
          >
            {mounted ? (
              darkMode ? (
                <Sun className="w-4 h-4" />
              ) : (
                <Moon className="w-4 h-4" />
              )
            ) : (
              <div className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
