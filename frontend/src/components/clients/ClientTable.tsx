"use client"

import { Edit2, Trash2, Mail, Phone, Eye, Search, Filter, ChevronDown } from "lucide-react"
import type { Client } from "@/types/client"
import { useState, useEffect, useRef } from "react"

interface ClientTableProps {
  clients: Client[]
  onView: (client: Client) => void
  onEdit: (client: Client) => void
  onDelete: (client: Client) => void
  searchTerm?: string
  onSearchChange?: (value: string) => void
  statusFilter?: "all" | "active" | "inactive"
  onStatusFilterChange?: (status: "all" | "active" | "inactive") => void
}

export function ClientTable({ 
  clients, 
  onView, 
  onEdit, 
  onDelete,
  searchTerm: externalSearchTerm = "",
  onSearchChange,
  statusFilter = "all",
  onStatusFilterChange,
}: ClientTableProps) {
  const [internalSearchTerm, setInternalSearchTerm] = useState("")
  const [isFilterOpen, setIsFilterOpen] = useState(false)
  const filterRef = useRef<HTMLDivElement>(null)
  
  const searchTerm = externalSearchTerm || internalSearchTerm
  const handleSearchChange = onSearchChange || ((value: string) => setInternalSearchTerm(value))

  // Close filter dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (filterRef.current && !filterRef.current.contains(event.target as Node)) {
        setIsFilterOpen(false)
      }
    }

    if (isFilterOpen) {
      document.addEventListener("mousedown", handleClickOutside)
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside)
    }
  }, [isFilterOpen])

  const formatDate = (date: string) => {
    return new Date(date).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    })
  }

  const filteredClients = clients.filter((client) => {
    if (searchTerm) {
      const search = searchTerm.toLowerCase()
      const matchesSearch =
        client.name.toLowerCase().includes(search) ||
        client.company?.toLowerCase().includes(search) ||
        client.email?.toLowerCase().includes(search) ||
        client.industry?.toLowerCase().includes(search)
      if (!matchesSearch) return false
    }

    if (statusFilter !== "all" && client.status !== statusFilter) {
      return false
    }

    return true
  })

  const getStatusLabel = () => {
    if (statusFilter === "all") return "All Status"
    return statusFilter.charAt(0).toUpperCase() + statusFilter.slice(1)
  }

  return (
    <div className="bg-[#0f1016]/60 backdrop-blur-md border border-white/10 rounded-2xl overflow-hidden shadow-xl">
      {/* Toolbar */}
      <div className="p-5 border-b border-white/5 flex gap-4">
        <div className="flex-1 relative group">
          <div className="absolute -inset-0.5 bg-gradient-to-r from-purple-600 to-blue-600 rounded-lg blur opacity-0 group-focus-within:opacity-20 transition duration-1000 group-hover:duration-200"></div>
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 group-focus-within:text-purple-400 transition-colors" />
          <input
            type="text"
            placeholder="Search by company, email, or industry..."
            value={searchTerm}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="relative w-full bg-black/40 border border-white/10 rounded-lg pl-10 pr-4 py-2.5 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/50 transition-all"
          />
        </div>
        {onStatusFilterChange && (
          <div className="relative" ref={filterRef}>
            <button
              onClick={() => setIsFilterOpen(!isFilterOpen)}
              className="flex items-center gap-2 px-4 py-2.5 bg-black/40 border border-white/10 rounded-lg text-sm text-slate-300 hover:text-white hover:border-purple-500/30 hover:bg-purple-500/10 transition-all"
            >
              <span>{getStatusLabel()}</span>
              <ChevronDown className={`w-4 h-4 transition-transform ${isFilterOpen ? "rotate-180" : ""}`} />
            </button>
            {isFilterOpen && (
              <div className="absolute right-0 mt-2 w-40 bg-[#0f1016] border border-white/10 rounded-lg shadow-xl z-10 overflow-hidden">
                <button
                  onClick={() => {
                    onStatusFilterChange("all")
                    setIsFilterOpen(false)
                  }}
                  className={`w-full text-left px-4 py-2 text-sm transition-colors ${
                    statusFilter === "all"
                      ? "bg-purple-500/10 text-purple-300"
                      : "text-slate-300 hover:bg-white/5 hover:text-white"
                  }`}
                >
                  All Status
                </button>
                <button
                  onClick={() => {
                    onStatusFilterChange("active")
                    setIsFilterOpen(false)
                  }}
                  className={`w-full text-left px-4 py-2 text-sm transition-colors ${
                    statusFilter === "active"
                      ? "bg-purple-500/10 text-purple-300"
                      : "text-slate-300 hover:bg-white/5 hover:text-white"
                  }`}
                >
                  Active
                </button>
                <button
                  onClick={() => {
                    onStatusFilterChange("inactive")
                    setIsFilterOpen(false)
                  }}
                  className={`w-full text-left px-4 py-2 text-sm transition-colors ${
                    statusFilter === "inactive"
                      ? "bg-purple-500/10 text-purple-300"
                      : "text-slate-300 hover:bg-white/5 hover:text-white"
                  }`}
                >
                  Inactive
                </button>
              </div>
            )}
          </div>
        )}
        <button className="flex items-center gap-2 px-4 py-2.5 bg-black/40 border border-white/10 rounded-lg text-sm text-slate-300 hover:text-white hover:border-purple-500/30 hover:bg-purple-500/10 transition-all">
          <Filter className="w-4 h-4" />
          <span>Filters</span>
        </button>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-white/5 bg-white/[0.02]">
              <th className="px-6 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">Company</th>
              <th className="px-6 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">Contact Info</th>
              <th className="px-6 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">Industry</th>
              <th className="px-6 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">Status</th>
              <th className="px-6 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">Last Updated</th>
              <th className="px-6 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {filteredClients.map((client) => (
              <tr key={client.id} className="group hover:bg-white/[0.02] transition-colors">
                {/* Company */}
                <td className="px-6 py-4">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-indigo-600 text-white flex items-center justify-center font-bold text-lg shadow-lg shadow-purple-900/20">
                      {client.name.charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <div className="font-medium text-white group-hover:text-purple-300 transition-colors">{client.name}</div>
                      {client.address && (
                        <div className="text-xs text-slate-500 mt-0.5">{client.address}</div>
                      )}
                    </div>
                  </div>
                </td>

                {/* Contact Info */}
                <td className="px-6 py-4">
                  <div className="space-y-1">
                    {client.company && (
                      <div className="text-sm font-medium text-white">{client.company}</div>
                    )}
                    {client.email && (
                      <div className="flex items-center gap-2 text-xs text-slate-400 group-hover:text-slate-300 transition-colors">
                        <Mail className="w-3 h-3" />
                        {client.email}
                      </div>
                    )}
                    {client.phone && (
                      <div className="flex items-center gap-2 text-xs text-slate-400 group-hover:text-slate-300 transition-colors">
                        <Phone className="w-3 h-3" />
                        {client.phone}
                      </div>
                    )}
                  </div>
                </td>

                {/* Industry */}
                <td className="px-6 py-4">
                  {client.industry ? (
                    <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-slate-800/50 text-slate-300 border border-white/10 backdrop-blur-sm">
                      {client.industry}
                    </span>
                  ) : (
                    <span className="text-sm text-slate-500">—</span>
                  )}
                </td>

                {/* Status */}
                <td className="px-6 py-4">
                  <span
                    className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border backdrop-blur-sm shadow-sm ${
                      client.status === "active"
                        ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20 shadow-emerald-900/20"
                        : "bg-rose-500/10 text-rose-400 border-rose-500/20 shadow-rose-900/20"
                    }`}
                  >
                    <span
                      className={`w-1.5 h-1.5 rounded-full mr-1.5 ${
                        client.status === "active" ? "bg-emerald-400" : "bg-rose-400"
                      }`}
                    ></span>
                    {client.status.charAt(0).toUpperCase() + client.status.slice(1)}
                  </span>
                </td>

                {/* Last Updated */}
                <td className="px-6 py-4">
                  <span className="text-sm text-slate-400">{formatDate(client.updated_at)}</span>
                </td>

                {/* Actions */}
                <td className="px-6 py-4 text-right">
                  <div className="flex items-center justify-end gap-1 opacity-60 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={() => onView(client)}
                      className="p-2 text-purple-400 hover:bg-purple-500/20 rounded-lg transition-colors"
                      title="View Projects"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => onEdit(client)}
                      className="p-2 text-blue-400 hover:bg-blue-500/20 rounded-lg transition-colors"
                      title="Edit"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => onDelete(client)}
                      className="p-2 text-rose-400 hover:bg-rose-500/20 rounded-lg transition-colors"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {filteredClients.length === 0 && (
        <div className="text-center py-12">
          <p className="text-slate-400 text-lg">No clients found</p>
          <p className="text-slate-500 text-sm mt-2">Add your first client to get started</p>
        </div>
      )}
    </div>
  )
}
