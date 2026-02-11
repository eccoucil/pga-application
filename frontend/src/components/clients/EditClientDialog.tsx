"use client"

import { useState, useEffect } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Loader2 } from "lucide-react"
import type { Client, UpdateClientData } from "@/types/client"

interface EditClientDialogProps {
  client: Client | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (clientId: string, data: UpdateClientData) => Promise<void>
}

export function EditClientDialog({
  client,
  open,
  onOpenChange,
  onSubmit,
}: EditClientDialogProps) {
  const [loading, setLoading] = useState(false)
  const [formData, setFormData] = useState<UpdateClientData>({
    name: "",
    company: "",
    email: "",
    phone: "",
    address: "",
    industry: "",
    status: "active",
  })

  // Populate form when client changes
  useEffect(() => {
    if (client) {
      setFormData({
        name: client.name,
        company: client.company || "",
        email: client.email || "",
        phone: client.phone || "",
        address: client.address || "",
        industry: client.industry || "",
        status: client.status,
      })
    }
  }, [client])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!client || !formData.name?.trim()) return

    setLoading(true)
    try {
      await onSubmit(client.id, formData)
      onOpenChange(false)
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (field: keyof UpdateClientData, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
  }

  if (!client) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Edit Client</DialogTitle>
            <DialogDescription>
              Update the client organization details.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            {/* Company Name - Required */}
            <div className="grid gap-2">
              <Label htmlFor="edit-name" className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                Company Name <span className="text-red-400">*</span>
              </Label>
              <Input
                id="edit-name"
                placeholder="Enter company name"
                value={formData.name || ""}
                onChange={(e) => handleChange("name", e.target.value)}
                className="bg-black/40 border border-white/10 text-white placeholder:text-slate-600 focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/50"
                required
              />
            </div>

            {/* Contact Person */}
            <div className="grid gap-2">
              <Label htmlFor="edit-company" className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                Contact Person
              </Label>
              <Input
                id="edit-company"
                placeholder="Primary contact name"
                value={formData.company || ""}
                onChange={(e) => handleChange("company", e.target.value)}
                className="bg-black/40 border border-white/10 text-white placeholder:text-slate-600 focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/50"
              />
            </div>

            {/* Contact Email */}
            <div className="grid gap-2">
              <Label htmlFor="edit-email" className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                Contact Email
              </Label>
              <Input
                id="edit-email"
                type="email"
                placeholder="contact@company.com"
                value={formData.email || ""}
                onChange={(e) => handleChange("email", e.target.value)}
                className="bg-black/40 border border-white/10 text-white placeholder:text-slate-600 focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/50"
              />
            </div>

            {/* Contact Phone */}
            <div className="grid gap-2">
              <Label htmlFor="edit-phone" className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                Contact Phone
              </Label>
              <Input
                id="edit-phone"
                placeholder="+1 (555) 000-0000"
                value={formData.phone || ""}
                onChange={(e) => handleChange("phone", e.target.value)}
                className="bg-black/40 border border-white/10 text-white placeholder:text-slate-600 focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/50"
              />
            </div>

            {/* Address */}
            <div className="grid gap-2">
              <Label htmlFor="edit-address" className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                Address
              </Label>
              <textarea
                id="edit-address"
                placeholder="Enter address"
                value={formData.address || ""}
                onChange={(e) => handleChange("address", e.target.value)}
                className="flex min-h-[80px] w-full rounded-lg border border-white/10 bg-black/40 px-3 py-2.5 text-sm text-white placeholder:text-slate-600 focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/50 disabled:cursor-not-allowed disabled:opacity-50 resize-none"
              />
            </div>

            {/* Industry */}
            <div className="grid gap-2">
              <Label htmlFor="edit-industry" className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                Industry
              </Label>
              <Input
                id="edit-industry"
                placeholder="e.g., Financial Services, Technology"
                value={formData.industry || ""}
                onChange={(e) => handleChange("industry", e.target.value)}
                className="bg-black/40 border border-white/10 text-white placeholder:text-slate-600 focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/50"
              />
            </div>

            {/* Status */}
            <div className="grid gap-2">
              <Label htmlFor="edit-status" className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                Status
              </Label>
              <Select
                value={formData.status}
                onValueChange={(value) => handleChange("status", value)}
              >
                <SelectTrigger className="bg-black/40 border border-white/10 text-white focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/50">
                  <SelectValue placeholder="Select status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="inactive">Inactive</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <DialogFooter className="flex justify-end gap-3 pt-6 border-t border-white/5 mt-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              className="px-4 py-2 text-sm font-medium text-slate-400 hover:text-white border-0 bg-transparent"
              disabled={loading}
            >
              Cancel
            </Button>
            <Button 
              type="submit" 
              className="px-6 py-2 text-sm font-medium bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white rounded-lg shadow-lg shadow-purple-900/20"
              disabled={loading}
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                "Save Changes"
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
