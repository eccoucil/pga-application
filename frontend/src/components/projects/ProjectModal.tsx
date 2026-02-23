"use client"

import { useState, useEffect, FormEvent, ChangeEvent } from "react"
import { X, AlertCircle, Calendar as CalendarIcon } from "lucide-react"
import { format, addDays } from "date-fns"
import type { Project, CreateProjectData, UpdateProjectData, FRAMEWORK_OPTIONS } from "@/types/project"
import { Calendar } from "@/components/ui/calendar"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { cn } from "@/lib/utils"

interface ProjectModalProps {
  isOpen: boolean
  onClose: () => void
  onSave: (data: CreateProjectData | UpdateProjectData) => void
  project?: Project | null
}

interface FormErrors {
  name?: string
  description?: string
  start_date?: string
  end_date?: string
}

const frameworkOptions = [
  { value: "BNM RMIT", label: "BNM RMIT" },
  { value: "ISO 27001:2022", label: "ISO 27001:2022" },
]

const statusOptions = [
  { value: "started", label: "Started" },
  { value: "on-going", label: "On-going" },
  { value: "completed", label: "Completed" },
]

export function ProjectModal({ isOpen, onClose, onSave, project }: ProjectModalProps) {
  const [formData, setFormData] = useState<CreateProjectData>({
    name: "",
    description: "",
    framework: [],
    start_date: "",
    end_date: "",
    status: "started",
  })

  const [errors, setErrors] = useState<FormErrors>({})
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [startDateOpen, setStartDateOpen] = useState(false)
  const [endDateOpen, setEndDateOpen] = useState(false)

  useEffect(() => {
    if (project) {
      setFormData({
        name: project.name || "",
        description: project.description || "",
        framework: project.framework || [],
        start_date: project.start_date || "",
        end_date: project.end_date || "",
        status: project.status || "planning",
      })
    } else {
      setFormData({
        name: "",
        description: "",
        framework: [],
        start_date: format(new Date(), "yyyy-MM-dd"),
        end_date: "",
        status: "started",
      })
    }
    setErrors({})
    setStartDateOpen(false)
    setEndDateOpen(false)
  }, [project, isOpen])

  const validateForm = (): boolean => {
    const newErrors: FormErrors = {}

    if (!formData.name?.trim()) {
      newErrors.name = "Project name is required"
    } else if (formData.name.trim().length < 3) {
      newErrors.name = "Project name must be at least 3 characters"
    }

    if (formData.start_date && formData.end_date) {
      if (new Date(formData.end_date) <= new Date(formData.start_date)) {
        newErrors.end_date = "End date must be after start date"
      }
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleInputChange = (
    e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
    if (errors[name as keyof FormErrors]) {
      setErrors((prev) => ({ ...prev, [name]: undefined }))
    }
  }

  const handleFrameworkChange = (framework: string) => {
    setFormData((prev) => {
      const currentFrameworks = prev.framework || []
      if (currentFrameworks.includes(framework)) {
        return { ...prev, framework: currentFrameworks.filter((f) => f !== framework) }
      } else {
        return { ...prev, framework: [...currentFrameworks, framework] }
      }
    })
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()

    if (!validateForm()) {
      return
    }

    setIsSubmitting(true)
    await new Promise((resolve) => setTimeout(resolve, 500))

    onSave(formData)
    setIsSubmitting(false)
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="relative bg-[#0f1016]/90 border border-white/10 rounded-2xl w-full max-w-2xl shadow-2xl backdrop-blur-xl overflow-hidden max-h-[90vh] overflow-y-auto">
        {/* Glow effect */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-1/2 h-1 bg-purple-500 shadow-[0_0_20px_rgba(168,85,247,0.5)]"></div>
        
        <div className="flex items-center justify-between p-6 border-b border-white/5">
          <h2 className="text-xl font-semibold text-white">
            {project ? "Edit Project" : "Add New Project"}
          </h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="space-y-2">
            <label
              htmlFor="name"
              className="text-xs font-medium text-slate-400 uppercase tracking-wider"
            >
              Project Name <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              id="name"
              name="name"
              value={formData.name}
              onChange={handleInputChange}
              className={`w-full bg-black/40 border ${
                errors.name ? "border-red-500/50" : "border-white/10"
              } rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/50 transition-all`}
              placeholder="Enter project name"
            />
            {errors.name && (
              <div className="flex items-center gap-2 text-red-400 text-xs">
                <AlertCircle className="w-3 h-3" />
                <span>{errors.name}</span>
              </div>
            )}
          </div>

          <div className="space-y-2">
            <label
              htmlFor="description"
              className="text-xs font-medium text-slate-400 uppercase tracking-wider"
            >
              Description
            </label>
            <textarea
              id="description"
              name="description"
              value={formData.description}
              onChange={handleInputChange}
              rows={3}
              className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/50 transition-all resize-none"
              placeholder="Enter project description"
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">
              Compliance Framework
            </label>
            <div className="flex flex-wrap gap-3">
              {frameworkOptions.map((option) => (
                <label
                  key={option.value}
                  className={`flex items-center px-4 py-2 rounded-lg border cursor-pointer transition-all duration-200 ${
                    formData.framework?.includes(option.value)
                      ? "border-purple-500/50 bg-purple-500/10 text-purple-300"
                      : "border-white/10 bg-black/40 text-slate-300 hover:border-purple-500/30"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={formData.framework?.includes(option.value) || false}
                    onChange={() => handleFrameworkChange(option.value)}
                    className="sr-only"
                  />
                  <span className="text-sm font-medium">{option.label}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label
                htmlFor="start_date"
                className="text-xs font-medium text-slate-400 uppercase tracking-wider"
              >
                Start Date
              </label>
              <Popover open={startDateOpen} onOpenChange={setStartDateOpen}>
                <PopoverTrigger asChild>
                  <button
                    type="button"
                    id="start_date"
                    className={cn(
                      "w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/50 transition-all flex items-center justify-start text-left",
                      !formData.start_date && "text-slate-500"
                    )}
                  >
                    <CalendarIcon className="mr-2 h-4 w-4 text-slate-500" />
                    {formData.start_date
                      ? format(new Date(formData.start_date), "PPP")
                      : "Select start date"}
                  </button>
                </PopoverTrigger>
                <PopoverContent className="z-[200] w-auto p-0 bg-[#0f1016] border border-white/10 shadow-xl" align="start">
                  <Calendar
                    mode="single"
                    selected={formData.start_date ? new Date(formData.start_date) : undefined}
                    onSelect={(date) => {
                      const newStartDate = date ? format(date, "yyyy-MM-dd") : ""
                      setFormData((prev) => {
                        const shouldClearEnd = prev.end_date && newStartDate && prev.end_date <= newStartDate
                        return {
                          ...prev,
                          start_date: newStartDate,
                          ...(shouldClearEnd ? { end_date: "" } : {}),
                        }
                      })
                      setStartDateOpen(false)
                    }}
                    disabled={{ before: new Date() }}
                    autoFocus
                  />
                </PopoverContent>
              </Popover>
            </div>

            <div className="space-y-2">
              <label
                htmlFor="end_date"
                className="text-xs font-medium text-slate-400 uppercase tracking-wider"
              >
                End Date
              </label>
              <Popover open={endDateOpen} onOpenChange={setEndDateOpen}>
                <PopoverTrigger asChild>
                  <button
                    type="button"
                    id="end_date"
                    className={cn(
                      "w-full bg-black/40 border rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:ring-1 transition-all flex items-center justify-start text-left",
                      errors.end_date
                        ? "border-red-500/50 focus:ring-red-500/50"
                        : "border-white/10 focus:border-purple-500/50 focus:ring-purple-500/50",
                      !formData.end_date && "text-slate-500"
                    )}
                  >
                    <CalendarIcon className="mr-2 h-4 w-4 text-slate-500" />
                    {formData.end_date
                      ? format(new Date(formData.end_date), "PPP")
                      : "Select end date"}
                  </button>
                </PopoverTrigger>
                <PopoverContent className="z-[200] w-auto p-0 bg-[#0f1016] border border-white/10 shadow-xl" align="start">
                  <Calendar
                    mode="single"
                    selected={formData.end_date ? new Date(formData.end_date) : undefined}
                    onSelect={(date) => {
                      setFormData((prev) => ({
                        ...prev,
                        end_date: date ? format(date, "yyyy-MM-dd") : "",
                      }))
                      setEndDateOpen(false)
                      if (errors.end_date) {
                        setErrors((prev) => ({ ...prev, end_date: undefined }))
                      }
                    }}
                    disabled={{
                      before: formData.start_date
                        ? addDays(new Date(formData.start_date), 1)
                        : new Date(),
                    }}
                    defaultMonth={formData.start_date ? new Date(formData.start_date) : undefined}
                    autoFocus
                  />
                </PopoverContent>
              </Popover>
              {errors.end_date && (
                <div className="flex items-center gap-2 text-red-400 text-xs">
                  <AlertCircle className="w-3 h-3" />
                  <span>{errors.end_date}</span>
                </div>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <label
              htmlFor="status"
              className="text-xs font-medium text-slate-400 uppercase tracking-wider"
            >
              Status
            </label>
            <select
              id="status"
              name="status"
              value={formData.status}
              onChange={handleInputChange}
              disabled={!project}
              className={`w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/50 transition-all ${!project ? "opacity-60 cursor-not-allowed" : ""}`}
            >
              {statusOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div className="flex justify-end gap-3 pt-6 border-t border-white/5 mt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-slate-400 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-6 py-2 text-sm font-medium bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white rounded-lg shadow-lg shadow-purple-900/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? (
                <span className="flex items-center gap-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  <span>Saving...</span>
                </span>
              ) : (
                <span>{project ? "Save Changes" : "Create Project"}</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
