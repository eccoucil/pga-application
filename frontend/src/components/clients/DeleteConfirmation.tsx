"use client"

import { X } from "lucide-react"
import type { Client } from "@/types/client"

interface DeleteConfirmationProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void
  client: Client | null
}

export function DeleteConfirmation({
  isOpen,
  onClose,
  onConfirm,
  client,
}: DeleteConfirmationProps) {
  if (!isOpen || !client) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="relative bg-[#0f1016]/90 border border-white/10 rounded-2xl w-full max-w-md shadow-2xl p-6 backdrop-blur-xl">
        {/* Glow effect */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-1/2 h-1 bg-red-500 shadow-[0_0_20px_rgba(239,68,68,0.5)]"></div>

        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-white">Delete Client</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>
        
        <p className="text-slate-400 text-sm mb-6 leading-relaxed">
          Are you sure you want to delete <span className="text-white font-medium">{client.name}</span>? This action cannot be undone and will remove all associated data.
        </p>
        
        <div className="flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-slate-400 hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-2 text-sm font-medium bg-red-500/10 hover:bg-red-500/20 text-red-500 border border-red-500/20 rounded-lg transition-colors"
          >
            Delete Client
          </button>
        </div>
      </div>
    </div>
  )
}
