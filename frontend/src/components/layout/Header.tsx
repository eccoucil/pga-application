"use client"

import { Moon, Sun, Menu } from "lucide-react"
import { useTheme } from "@/contexts/ThemeContext"
import { useAuth } from "@/contexts/AuthContext"

interface HeaderProps {
  onMenuClick: () => void
}

export function Header({ onMenuClick }: HeaderProps) {
  const { darkMode, toggleDarkMode, mounted } = useTheme()
  const { user } = useAuth()

  // Get user initials for avatar
  const getInitials = () => {
    if (!user?.email) return "U"
    return user.email.charAt(0).toUpperCase()
  }

  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 dark:border-slate-800/50 bg-white/80 dark:bg-slate-950/80 backdrop-blur-xl">
      <div className="px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {/* Mobile menu button */}
            <button
              className="lg:hidden p-2 text-slate-400 hover:text-cyan-500 dark:hover:text-cyan-400 hover:bg-slate-100 dark:hover:bg-slate-800/50 rounded-lg transition-colors"
              onClick={onMenuClick}
            >
              <Menu className="size-5" />
            </button>
          </div>

          <div className="flex items-center gap-4">
            {/* Theme toggle */}
            <button
              onClick={toggleDarkMode}
              className="p-2 rounded-lg text-slate-400 hover:text-cyan-500 dark:hover:text-cyan-400 hover:bg-slate-100 dark:hover:bg-slate-800/50 transition-all duration-300"
              aria-label="Toggle dark mode"
            >
              {mounted ? (
                darkMode ? (
                  <Sun className="size-5" />
                ) : (
                  <Moon className="size-5" />
                )
              ) : (
                <div className="size-5" />
              )}
            </button>

            {/* User avatar */}
            <div className="h-10 w-10 rounded-full bg-gradient-to-br from-cyan-400 to-blue-500 flex items-center justify-center font-semibold text-white shadow-lg shadow-cyan-500/25">
              {getInitials()}
            </div>
          </div>
        </div>
      </div>
    </header>
  )
}
