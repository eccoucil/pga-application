"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Plus, Search, Filter, Users, Loader2 } from "lucide-react"
import { ClientTable } from "@/components/clients/ClientTable"
import { ClientModal } from "@/components/clients/ClientModal"
import { DeleteConfirmation } from "@/components/clients/DeleteConfirmation"
import { Stats } from "@/components/ui/stats"
import type { Client, CreateClientData, UpdateClientData } from "@/types/client"
import { useAuth } from "@/contexts/AuthContext"
import { useClient } from "@/contexts/ClientContext"
import { useToast } from "@/hooks/use-toast"
import { getClients, addClient, updateClient, deleteClient } from "@/lib/supabase"

export function ClientManagement() {
  const router = useRouter()
  const { user } = useAuth()
  const { setSelectedClient: setContextClient } = useClient()
  const { toast } = useToast()
  const [clients, setClients] = useState<Client[]>([])
  const [filteredClients, setFilteredClients] = useState<Client[]>([])
  const [searchTerm, setSearchTerm] = useState("")
  const [statusFilter, setStatusFilter] = useState<"all" | "active" | "inactive">("all")
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false)
  const [selectedClient, setSelectedClient] = useState<Client | null>(null)
  const [clientToDelete, setClientToDelete] = useState<Client | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchClients = async () => {
    if (!user?.id) return

    setLoading(true)
    try {
      const { data, error } = await getClients(user.id, {
        search: searchTerm || undefined,
        status: statusFilter !== "all" ? statusFilter : undefined,
      })

      if (error) {
        toast({
          title: "Error",
          description: error.message,
          variant: "destructive",
        })
        setClients([])
        setFilteredClients([])
      } else {
        setClients(data)
        filterClientsLocally(data, searchTerm, statusFilter)
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to fetch clients",
        variant: "destructive",
      })
      setClients([])
      setFilteredClients([])
    } finally {
      setLoading(false)
    }
  }

  const filterClientsLocally = (
    clientList: Client[],
    search: string,
    status: "all" | "active" | "inactive"
  ) => {
    let filtered = clientList

    if (search) {
      filtered = filtered.filter(
        (client) =>
          client.name.toLowerCase().includes(search.toLowerCase()) ||
          client.email?.toLowerCase().includes(search.toLowerCase()) ||
          client.industry?.toLowerCase().includes(search.toLowerCase())
      )
    }

    if (status !== "all") {
      filtered = filtered.filter((client) => client.status === status)
    }

    setFilteredClients(filtered)
  }

  useEffect(() => {
    fetchClients()
  }, [user?.id])

  useEffect(() => {
    filterClientsLocally(clients, searchTerm, statusFilter)
  }, [searchTerm, statusFilter, clients])

  const handleSearch = (term: string) => {
    setSearchTerm(term)
  }

  const handleStatusFilter = (status: "all" | "active" | "inactive") => {
    setStatusFilter(status)
  }

  const handleViewClient = (client: Client) => {
    setContextClient(client)
    router.push(`/clients/${client.id}/projects`)
  }

  const handleAddClient = () => {
    setSelectedClient(null)
    setIsModalOpen(true)
  }

  const handleEditClient = (client: Client) => {
    setSelectedClient(client)
    setIsModalOpen(true)
  }

  const handleDeleteClient = (client: Client) => {
    setClientToDelete(client)
    setIsDeleteModalOpen(true)
  }

  const handleSaveClient = async (formData: CreateClientData | UpdateClientData) => {
    if (!user?.id) return

    try {
      if (selectedClient) {
        // Update existing client
        const { data: updatedClient, error } = await updateClient(selectedClient.id, formData)
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
          setIsModalOpen(false)
          setSelectedClient(null)
          fetchClients()
        }
      } else {
        // Create new client
        const { data: newClient, error } = await addClient(user.id, formData as CreateClientData)
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
          setIsModalOpen(false)
          fetchClients()
        }
      }
    } catch (error) {
      toast({
        title: "Error",
        description: selectedClient ? "Failed to update client" : "Failed to create client",
        variant: "destructive",
      })
    }
  }

  const confirmDelete = async () => {
    if (!clientToDelete) return

    try {
      const { error } = await deleteClient(clientToDelete.id)
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
        setIsDeleteModalOpen(false)
        setClientToDelete(null)
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

  const stats = {
    total: clients.length,
    active: clients.filter((c) => c.status === "active").length,
    inactive: clients.filter((c) => c.status === "inactive").length,
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white mb-1">
            Client Management
          </h1>
          <p className="text-slate-400">
            Manage your clients and their information
          </p>
        </div>
        <button
          onClick={handleAddClient}
          className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white rounded-lg font-medium transition-all shadow-lg shadow-purple-500/20"
        >
          <Plus className="w-5 h-5" />
          <span>Add Client</span>
        </button>
      </div>

      <Stats stats={stats} loading={loading} />

      {loading ? (
        <div className="flex justify-center items-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
        </div>
      ) : (
        <ClientTable
          clients={filteredClients}
          onView={handleViewClient}
          onEdit={handleEditClient}
          onDelete={handleDeleteClient}
          searchTerm={searchTerm}
          onSearchChange={handleSearch}
          statusFilter={statusFilter}
          onStatusFilterChange={handleStatusFilter}
        />
      )}

      <ClientModal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false)
          setSelectedClient(null)
        }}
        onSave={handleSaveClient}
        client={selectedClient}
      />

      <DeleteConfirmation
        isOpen={isDeleteModalOpen}
        onClose={() => {
          setIsDeleteModalOpen(false)
          setClientToDelete(null)
        }}
        onConfirm={confirmDelete}
        client={clientToDelete}
      />
    </div>
  )
}
