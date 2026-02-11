"use client"

import { Sidebar } from "./Sidebar"
import { Footer } from "./Footer"

interface DashboardLayoutProps {
  children: React.ReactNode
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-[#050505] to-[#1e1b4b] text-slate-300 font-sans selection:bg-purple-500/30">
      {/* Background Pattern */}
      <div className="fixed inset-0 bg-[linear-gradient(to_right,#0f172a_1px,transparent_1px),linear-gradient(to_bottom,#0f172a_1px,transparent_1px)] bg-[size:4rem_4rem] opacity-20 pointer-events-none" />

      {/* Animated Glow Effects */}
      <div className="fixed top-0 left-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-[100px] pointer-events-none" />
      <div className="fixed bottom-0 right-1/4 w-96 h-96 bg-indigo-500/10 rounded-full blur-[100px] pointer-events-none" />

      <div className="relative flex min-h-screen">
        {/* Sidebar - Fixed on the left */}
        <aside className="fixed inset-y-0 left-0 z-50">
          <Sidebar />
        </aside>

        {/* Main Content Area - Offset by sidebar width */}
        <div className="flex-1 flex flex-col min-w-0 ml-64 min-h-screen">
          {/* Main content area - scrollable with padding */}
          <main className="flex-1 overflow-y-auto">
            <div className="p-8 max-w-7xl mx-auto pb-0">
              {children}
            </div>
          </main>

          {/* Footer - Sticky at bottom of viewport */}
          <div className="mt-auto">
            <Footer />
          </div>
        </div>
      </div>
    </div>
  )
}
