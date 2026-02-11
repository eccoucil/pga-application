"use client"

import { useState, useEffect } from "react"
import { DashboardLayout } from "@/components/layout/DashboardLayout"
import { ClientTable } from "@/components/clients/ClientTable"
import { CreateClientDialog } from "@/components/clients/CreateClientDialog"
import { EditClientDialog } from "@/components/clients/EditClientDialog"
import { Button } from "@/components/ui/button"
import { useToast } from "@/hooks/use-toast"
import { useAuth } from "@/contexts/AuthContext"
import { getClients, addClient, updateClient, deleteClient } from "@/lib/supabase"
import type { Client, CreateClientData, UpdateClientData } from "@/types/client"
import { Plus, Loader2 } from "lucide-react"

export default function OrganizationsPage() {
  const { user } = useAuth()
  const { toast } = useToast()
  const [clients, setClients] = useState<Client[]>([])
  const [loading, setLoading] = useState(true)
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [selectedClient, setSelectedClient] = useState<Client | null>(null)

  const fetchClients = async () => {
    if (!user?.id) return

    setLoading(true)
    try {
      const { data, error } = await getClients(user.id)
      if (error) {
        toast({
          title: "Error",
          description: error.message,
          variant: "destructive",
        })
      } else {
        setClients(data)
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to fetch clients",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchClients()
  }, [user?.id])

  const handleCreate = async (data: CreateClientData) => {
    if (!user?.id) return

    try {
      const { data: newClient, error } = await addClient(user.id, data)
      if (error) {
        toast({
          title: "Error",
          description: error.message,
          variant: "destructive",
        })
      } else if (newClient) {
        toast({
          title: "Success",
          description: "Client created successfully",
        })
        setCreateDialogOpen(false)
        fetchClients()
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to create client",
        variant: "destructive",
      })
    }
  }

  const handleEdit = (client: Client) => {
    setSelectedClient(client)
    setEditDialogOpen(true)
  }

  const handleUpdate = async (clientId: string, data: UpdateClientData) => {
    try {
      const { data: updatedClient, error } = await updateClient(clientId, data)
      if (error) {
        toast({
          title: "Error",
          description: error.message,
          variant: "destructive",
        })
      } else if (updatedClient) {
        toast({
          title: "Success",
          description: "Client updated successfully",
        })
        setEditDialogOpen(false)
        setSelectedClient(null)
        fetchClients()
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to update client",
        variant: "destructive",
      })
    }
  }

  const handleDelete = async (client: Client) => {
    if (!confirm(`Are you sure you want to delete ${client.name}?`)) {
      return
    }

    try {
      const { error } = await deleteClient(client.id)
      if (error) {
        toast({
          title: "Error",
          description: error.message,
          variant: "destructive",
        })
      } else {
        toast({
          title: "Success",
          description: "Client deleted successfully",
        })
        fetchClients()
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to delete client",
        variant: "destructive",
      })
    }
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-2xl font-bold text-white mb-1">
              Organizations
            </h1>
            <p className="text-slate-400">
              Manage your client organizations and their information
            </p>
          </div>
          <button
            onClick={() => setCreateDialogOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white rounded-lg font-medium transition-all shadow-lg shadow-purple-500/20"
          >
            <Plus className="w-5 h-5" />
            <span>Add Organization</span>
          </button>
        </div>

        {/* Table */}
        {loading ? (
          <div className="flex justify-center items-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
          </div>
        ) : (
          <ClientTable
            clients={clients}
            onView={handleEdit}
            onEdit={handleEdit}
            onDelete={handleDelete}
          />
        )}

        {/* Dialogs */}
        <CreateClientDialog
          open={createDialogOpen}
          onOpenChange={setCreateDialogOpen}
          onSubmit={handleCreate}
        />
        <EditClientDialog
          client={selectedClient}
          open={editDialogOpen}
          onOpenChange={setEditDialogOpen}
          onSubmit={handleUpdate}
        />
      </div>
    </DashboardLayout>
  )
}
