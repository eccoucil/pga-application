"use client"

import { useState } from "react"
import { format } from "date-fns"
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
import { Checkbox } from "@/components/ui/checkbox"
import { DatePicker } from "@/components/ui/date-picker"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Loader2 } from "lucide-react"
import type { CreateProjectData, ProjectStatus } from "@/types/project"
import { FRAMEWORK_OPTIONS } from "@/types/project"

interface CreateProjectDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (data: CreateProjectData) => Promise<void>
}

export function CreateProjectDialog({
  open,
  onOpenChange,
  onSubmit,
}: CreateProjectDialogProps) {
  const [loading, setLoading] = useState(false)
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    status: "planning" as ProjectStatus,
  })
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [selectedFrameworks, setSelectedFrameworks] = useState<string[]>([])
  const [otherChecked, setOtherChecked] = useState(false)
  const [customFramework, setCustomFramework] = useState("")

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.name.trim()) return

    setLoading(true)
    try {
      // Build the framework array
      const frameworks = [...selectedFrameworks]
      if (otherChecked && customFramework.trim()) {
        frameworks.push(customFramework.trim())
      }

      const submitData: CreateProjectData = {
        name: formData.name,
        description: formData.description || undefined,
        status: formData.status,
        framework: frameworks.length > 0 ? frameworks : undefined,
        start_date: startDate ? format(startDate, "yyyy-MM-dd") : undefined,
        end_date: endDate ? format(endDate, "yyyy-MM-dd") : undefined,
      }
      await onSubmit(submitData)
      // Reset form on success
      setFormData({
        name: "",
        description: "",
        status: "planning",
      })
      setStartDate(undefined)
      setEndDate(undefined)
      setSelectedFrameworks([])
      setOtherChecked(false)
      setCustomFramework("")
      onOpenChange(false)
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (field: "name" | "description" | "status", value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
  }

  const handleFrameworkToggle = (framework: string, checked: boolean) => {
    setSelectedFrameworks((prev) =>
      checked
        ? [...prev, framework]
        : prev.filter((f) => f !== framework)
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Create New Project</DialogTitle>
            <DialogDescription>
              Add a new compliance assessment project for this client.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            {/* Project Name - Required */}
            <div className="grid gap-2">
              <Label htmlFor="name" className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                Project Name <span className="text-red-400">*</span>
              </Label>
              <Input
                id="name"
                placeholder="e.g., BNM RMIT 2024 Assessment"
                value={formData.name}
                onChange={(e) => handleChange("name", e.target.value)}
                className="bg-black/40 border border-white/10 text-white placeholder:text-slate-600 focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/50"
                required
              />
            </div>

            {/* Description */}
            <div className="grid gap-2">
              <Label htmlFor="description" className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                Description
              </Label>
              <textarea
                id="description"
                placeholder="Brief description of the project scope"
                value={formData.description}
                onChange={(e) => handleChange("description", e.target.value)}
                className="flex min-h-[80px] w-full rounded-lg border border-white/10 bg-black/40 px-3 py-2.5 text-sm text-white placeholder:text-slate-600 focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/50 disabled:cursor-not-allowed disabled:opacity-50 resize-none"
              />
            </div>

            {/* Framework - Multi-select checkboxes */}
            <div className="grid gap-3">
              <Label className="text-xs font-medium text-slate-400 uppercase tracking-wider">Compliance Framework(s)</Label>
              <div className="space-y-3">
                {FRAMEWORK_OPTIONS.map((option) => (
                  <div key={option.value} className="flex items-center gap-3">
                    <Checkbox
                      id={`framework-${option.value}`}
                      checked={selectedFrameworks.includes(option.value)}
                      onCheckedChange={(checked) =>
                        handleFrameworkToggle(option.value, checked === true)
                      }
                    />
                    <Label
                      htmlFor={`framework-${option.value}`}
                      className="text-sm text-slate-300 cursor-pointer font-normal"
                    >
                      {option.label}
                    </Label>
                  </div>
                ))}
                {/* Other option with text input */}
                <div className="flex items-start gap-3">
                  <Checkbox
                    id="framework-other"
                    checked={otherChecked}
                    onCheckedChange={(checked) => {
                      setOtherChecked(checked === true)
                      if (!checked) setCustomFramework("")
                    }}
                    className="mt-0.5"
                  />
                  <div className="flex-1 space-y-2">
                    <Label
                      htmlFor="framework-other"
                      className="text-sm text-slate-300 cursor-pointer font-normal"
                    >
                      Other
                    </Label>
                    {otherChecked && (
                      <Input
                        id="customFramework"
                        placeholder="Enter framework name"
                        value={customFramework}
                        onChange={(e) => setCustomFramework(e.target.value)}
                        className="bg-black/40 border border-white/10 text-white placeholder:text-slate-600 focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/50"
                      />
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Date Fields */}
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="start_date" className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                  Start Date
                </Label>
                <DatePicker
                  id="start_date"
                  date={startDate}
                  onDateChange={setStartDate}
                  placeholder="Select start date"
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="end_date" className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                  End Date
                </Label>
                <DatePicker
                  id="end_date"
                  date={endDate}
                  onDateChange={setEndDate}
                  placeholder="Select end date"
                />
              </div>
            </div>

            {/* Status */}
            <div className="grid gap-2">
              <Label htmlFor="status" className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                Status
              </Label>
              <Select
                value={formData.status}
                onValueChange={(value) => handleChange("status", value as ProjectStatus)}
              >
                <SelectTrigger className="bg-black/40 border border-white/10 text-white focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/50">
                  <SelectValue placeholder="Select status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="planning">Planning</SelectItem>
                  <SelectItem value="in-progress">In Progress</SelectItem>
                  <SelectItem value="completed">Completed</SelectItem>
                  <SelectItem value="on-hold">On Hold</SelectItem>
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
                  Creating...
                </>
              ) : (
                "Create Project"
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
