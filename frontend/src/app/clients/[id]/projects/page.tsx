"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { DashboardLayout } from "@/components/layout/DashboardLayout"
import { ProjectManagement } from "@/components/projects/ProjectManagement"
import { useClient } from "@/contexts/ClientContext"
import { useAuth } from "@/contexts/AuthContext"
import { getClient } from "@/lib/supabase"
import { Loader2 } from "lucide-react"

export default function ProjectsPage() {
  const params = useParams()
  const router = useRouter()
  const { user, loading: authLoading } = useAuth()
  const { selectedClient, setSelectedClient } = useClient()
  const clientId = params.id as string
  const [clientLoading, setClientLoading] = useState(false)

  useEffect(() => {
    // If we have a clientId from URL but no selectedClient in context, fetch and set it
    const fetchClientFromId = async () => {
      if (!authLoading && user && clientId && !selectedClient) {
        setClientLoading(true)
        try {
          const { data: client, error } = await getClient(clientId)
          if (error || !client) {
            // Client not found, redirect to clients list
            router.push("/clients")
          } else {
            setSelectedClient(client)
          }
        } catch {
          router.push("/clients")
        } finally {
          setClientLoading(false)
        }
      }
    }

    fetchClientFromId()
  }, [clientId, selectedClient, authLoading, user, setSelectedClient, router])

  useEffect(() => {
    // If selected client doesn't match URL, update URL to match
    if (!authLoading && user && selectedClient && selectedClient.id !== clientId) {
      router.replace(`/clients/${selectedClient.id}/projects`)
    }
  }, [selectedClient, clientId, authLoading, user, router])

  // Show loading while auth or client is loading
  if (authLoading || clientLoading) {
    return (
      <DashboardLayout>
        <div className="flex justify-center items-center min-h-[400px]">
          <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
        </div>
      </DashboardLayout>
    )
  }

  // If no user, the layout will handle redirect to login
  if (!user) {
    return null
  }

  return (
    <DashboardLayout>
      <ProjectManagement />
    </DashboardLayout>
  )
}
