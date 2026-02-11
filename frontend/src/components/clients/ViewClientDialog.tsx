"use client"

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Building2, User, Mail, Phone, MapPin, Briefcase, Calendar } from "lucide-react"
import type { Client } from "@/types/client"

interface ViewClientDialogProps {
  client: Client | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onEdit: () => void
}

export function ViewClientDialog({
  client,
  open,
  onOpenChange,
  onEdit,
}: ViewClientDialogProps) {
  if (!client) return null

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-white">
            <Building2 className="h-5 w-5 text-purple-400" />
            {client.name}
          </DialogTitle>
          <DialogDescription className="text-slate-400">Client organization details</DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Status Badge */}
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Status</span>
            <span
              className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border backdrop-blur-sm shadow-sm ${
                client.status === "active"
                  ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20 shadow-emerald-900/20"
                  : "bg-rose-500/10 text-rose-400 border-rose-500/20 shadow-rose-900/20"
              }`}
            >
              <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${
                client.status === "active" ? "bg-emerald-400" : "bg-rose-400"
              }`}></span>
              {client.status === "active" ? "Active" : "Inactive"}
            </span>
          </div>

          {/* Contact Person */}
          <div className="flex items-start gap-3 p-3 rounded-lg bg-black/40 border border-white/10">
            <User className="h-5 w-5 text-slate-400 mt-0.5" />
            <div>
              <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">Contact Person</p>
              <p className="text-sm text-white">
                {client.company || <span className="text-slate-500">Not specified</span>}
              </p>
            </div>
          </div>

          {/* Contact Email */}
          <div className="flex items-start gap-3 p-3 rounded-lg bg-black/40 border border-white/10">
            <Mail className="h-5 w-5 text-slate-400 mt-0.5" />
            <div>
              <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">Contact Email</p>
              <p className="text-sm text-white">
                {client.email ? (
                  <a href={`mailto:${client.email}`} className="text-purple-400 hover:text-purple-300 hover:underline transition-colors">
                    {client.email}
                  </a>
                ) : (
                  <span className="text-slate-500">Not specified</span>
                )}
              </p>
            </div>
          </div>

          {/* Contact Phone */}
          <div className="flex items-start gap-3 p-3 rounded-lg bg-black/40 border border-white/10">
            <Phone className="h-5 w-5 text-slate-400 mt-0.5" />
            <div>
              <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">Contact Phone</p>
              <p className="text-sm text-white">
                {client.phone ? (
                  <a href={`tel:${client.phone}`} className="text-purple-400 hover:text-purple-300 hover:underline transition-colors">
                    {client.phone}
                  </a>
                ) : (
                  <span className="text-slate-500">Not specified</span>
                )}
              </p>
            </div>
          </div>

          {/* Address */}
          <div className="flex items-start gap-3 p-3 rounded-lg bg-black/40 border border-white/10">
            <MapPin className="h-5 w-5 text-slate-400 mt-0.5" />
            <div>
              <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">Address</p>
              <p className="text-sm text-white whitespace-pre-wrap">
                {client.address || <span className="text-slate-500">Not specified</span>}
              </p>
            </div>
          </div>

          {/* Industry */}
          <div className="flex items-start gap-3 p-3 rounded-lg bg-black/40 border border-white/10">
            <Briefcase className="h-5 w-5 text-slate-400 mt-0.5" />
            <div>
              <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">Industry</p>
              <p className="text-sm text-white">
                {client.industry || <span className="text-slate-500">Not specified</span>}
              </p>
            </div>
          </div>

          {/* Dates */}
          <div className="flex items-start gap-3 p-3 rounded-lg bg-black/40 border border-white/10">
            <Calendar className="h-5 w-5 text-slate-400 mt-0.5" />
            <div className="flex-1">
              <div className="flex justify-between items-center">
                <div>
                  <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">Created</p>
                  <p className="text-sm text-white">{formatDate(client.created_at)}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">Last Updated</p>
                  <p className="text-sm text-white">{formatDate(client.updated_at)}</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-3 pt-6 border-t border-white/5 mt-2">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            className="px-4 py-2 text-sm font-medium text-slate-400 hover:text-white border-0 bg-transparent"
          >
            Close
          </Button>
          <Button 
            onClick={onEdit}
            className="px-6 py-2 text-sm font-medium bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white rounded-lg shadow-lg shadow-purple-900/20"
          >
            Edit Client
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
