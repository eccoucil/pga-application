"use client"

import { createContext, useContext, useState, useEffect, ReactNode } from "react"
import { usePathname } from "next/navigation"
import type { Client } from "@/types/client"

interface ClientContextType {
  selectedClient: Client | null
  setSelectedClient: (client: Client | null) => void
  clearSelectedClient: () => void
}

const ClientContext = createContext<ClientContextType | undefined>(undefined)

export function ClientProvider({ children }: { children: ReactNode }) {
  const [selectedClient, setSelectedClient] = useState<Client | null>(null)
  const pathname = usePathname()

  // Clear selected client when navigating away from client-specific pages
  useEffect(() => {
    // If we're not on a client-specific page, clear the selection
    if (!pathname.startsWith("/clients/") || pathname === "/clients") {
      // Don't clear immediately on /clients page - user might be browsing
      if (!pathname.startsWith("/clients")) {
        setSelectedClient(null)
      }
    }
  }, [pathname])

  const clearSelectedClient = () => {
    setSelectedClient(null)
  }

  return (
    <ClientContext.Provider
      value={{
        selectedClient,
        setSelectedClient,
        clearSelectedClient,
      }}
    >
      {children}
    </ClientContext.Provider>
  )
}

export function useClient() {
  const context = useContext(ClientContext)
  if (context === undefined) {
    throw new Error("useClient must be used within a ClientProvider")
  }
  return context
}
