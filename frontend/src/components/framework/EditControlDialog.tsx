"use client"

import { useState, useEffect } from "react"
import { Loader2, Plus, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog"
import { supabase } from "@/lib/supabase"
import { useToast } from "@/hooks/use-toast"
import {
  FrameworkControl,
  ISORequirement,
  BNMRequirement,
  isISORequirement,
  isBNMRequirement,
} from "@/types/framework"

interface EditControlDialogProps {
  control: FrameworkControl | null
  framework: string
  open: boolean
  onOpenChange: (open: boolean) => void
  onSave: () => void
}

export function EditControlDialog({
  control,
  framework,
  open,
  onOpenChange,
  onSave,
}: EditControlDialogProps) {
  const { toast } = useToast()
  const [saving, setSaving] = useState(false)

  // ISO fields
  const [isoTitle, setIsoTitle] = useState("")
  const [isoDescription, setIsoDescription] = useState("")
  const [keyActivities, setKeyActivities] = useState<string[]>([])

  // BNM fields
  const [requirementText, setRequirementText] = useState("")
  const [subRequirements, setSubRequirements] = useState<{ key: string; text: string }[]>([])

  // Reset form when control changes
  useEffect(() => {
    if (control) {
      if (isISORequirement(control)) {
        setIsoTitle(control.title)
        setIsoDescription(control.description || "")
        setKeyActivities(control.key_activities || [])
      } else if (isBNMRequirement(control)) {
        setRequirementText(control.requirement_text)
        setSubRequirements(control.sub_requirements || [])
      }
    }
  }, [control])

  const handleSave = async () => {
    if (!control) return

    setSaving(true)

    try {
      let error: Error | null = null

      if (isISORequirement(control)) {
        const { error: updateError } = await supabase
          .from("iso_requirements")
          .update({
            title: isoTitle,
            description: isoDescription || null,
            key_activities: keyActivities.length > 0 ? keyActivities : null,
          })
          .eq("id", control.id)

        if (updateError) error = new Error(updateError.message)
      } else if (isBNMRequirement(control)) {
        const { error: updateError } = await supabase
          .from("bnm_rmit_requirements")
          .update({
            requirement_text: requirementText,
            sub_requirements: subRequirements.length > 0 ? subRequirements : null,
          })
          .eq("id", control.id)

        if (updateError) error = new Error(updateError.message)
      }

      if (error) {
        toast({
          title: "Update failed",
          description: error.message,
          variant: "destructive",
        })
      } else {
        toast({
          title: "Control updated",
          description: "The control has been updated successfully.",
        })
        onSave()
        onOpenChange(false)
      }
    } finally {
      setSaving(false)
    }
  }

  // Key Activities handlers (ISO)
  const addKeyActivity = () => {
    setKeyActivities([...keyActivities, ""])
  }

  const updateKeyActivity = (index: number, value: string) => {
    const updated = [...keyActivities]
    updated[index] = value
    setKeyActivities(updated)
  }

  const removeKeyActivity = (index: number) => {
    setKeyActivities(keyActivities.filter((_, i) => i !== index))
  }

  // Sub-requirements handlers (BNM)
  const addSubRequirement = () => {
    setSubRequirements([...subRequirements, { key: "", text: "" }])
  }

  const updateSubRequirement = (index: number, field: "key" | "text", value: string) => {
    const updated = [...subRequirements]
    updated[index][field] = value
    setSubRequirements(updated)
  }

  const removeSubRequirement = (index: number) => {
    setSubRequirements(subRequirements.filter((_, i) => i !== index))
  }

  if (!control) return null

  const identifier = isISORequirement(control) ? control.identifier : control.reference_id

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            Edit Control
            <span className="text-sm font-mono text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
              {identifier}
            </span>
          </DialogTitle>
          <DialogDescription>
            Update the control details for {framework}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* ISO 27001:2022 Fields */}
          {isISORequirement(control) && (
            <>
              <div className="space-y-2">
                <Label htmlFor="title" className="text-white">
                  Title
                </Label>
                <Input
                  id="title"
                  value={isoTitle}
                  onChange={(e) => setIsoTitle(e.target.value)}
                  className="bg-slate-950 border-slate-700 text-white"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="description" className="text-white">
                  Description
                </Label>
                <textarea
                  id="description"
                  value={isoDescription}
                  onChange={(e) => setIsoDescription(e.target.value)}
                  rows={4}
                  className="flex w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white ring-offset-slate-950 placeholder:text-slate-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                />
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label className="text-white">Key Activities</Label>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={addKeyActivity}
                    className="text-cyan-400 hover:text-cyan-300 hover:bg-slate-800"
                  >
                    <Plus className="h-4 w-4 mr-1" />
                    Add Activity
                  </Button>
                </div>
                <div className="space-y-2">
                  {keyActivities.map((activity, index) => (
                    <div key={index} className="flex gap-2">
                      <Input
                        value={activity}
                        onChange={(e) => updateKeyActivity(index, e.target.value)}
                        placeholder={`Activity ${index + 1}`}
                        className="bg-slate-950 border-slate-700 text-white"
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => removeKeyActivity(index)}
                        className="text-slate-400 hover:text-red-400 hover:bg-slate-800 flex-shrink-0"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                  {keyActivities.length === 0 && (
                    <p className="text-slate-500 text-sm">No key activities defined</p>
                  )}
                </div>
              </div>
            </>
          )}

          {/* BNM RMIT Fields */}
          {isBNMRequirement(control) && (
            <>
              <div className="space-y-2">
                <Label htmlFor="requirement_text" className="text-white">
                  Requirement Text
                </Label>
                <textarea
                  id="requirement_text"
                  value={requirementText}
                  onChange={(e) => setRequirementText(e.target.value)}
                  rows={4}
                  className="flex w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white ring-offset-slate-950 placeholder:text-slate-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                />
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label className="text-white">Sub-Requirements</Label>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={addSubRequirement}
                    className="text-cyan-400 hover:text-cyan-300 hover:bg-slate-800"
                  >
                    <Plus className="h-4 w-4 mr-1" />
                    Add Sub-Requirement
                  </Button>
                </div>
                <div className="space-y-3">
                  {subRequirements.map((sub, index) => (
                    <div key={index} className="flex gap-2">
                      <Input
                        value={sub.key}
                        onChange={(e) => updateSubRequirement(index, "key", e.target.value)}
                        placeholder="Key (e.g., a, b, i)"
                        className="bg-slate-950 border-slate-700 text-white w-24 flex-shrink-0"
                      />
                      <Input
                        value={sub.text}
                        onChange={(e) => updateSubRequirement(index, "text", e.target.value)}
                        placeholder="Requirement text"
                        className="bg-slate-950 border-slate-700 text-white"
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => removeSubRequirement(index)}
                        className="text-slate-400 hover:text-red-400 hover:bg-slate-800 flex-shrink-0"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                  {subRequirements.length === 0 && (
                    <p className="text-slate-500 text-sm">No sub-requirements defined</p>
                  )}
                </div>
              </div>
            </>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="ghost"
            onClick={() => onOpenChange(false)}
            disabled={saving}
            className="text-slate-400 hover:text-white hover:bg-slate-800"
          >
            Cancel
          </Button>
          <Button variant="cyber" onClick={handleSave} disabled={saving}>
            {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            Save Changes
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
