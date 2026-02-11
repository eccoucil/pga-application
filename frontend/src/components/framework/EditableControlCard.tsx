"use client"

import { useState } from "react"
import { Pencil, Check, X } from "lucide-react"
import { Button } from "@/components/ui/button"

interface EditableControlCardProps {
  controlId: string
  title: string
  description: string
  categoryLabel?: string
  onSave: (id: string, title: string, description: string) => Promise<void>
}

export function EditableControlCard({
  controlId,
  title,
  description,
  categoryLabel,
  onSave,
}: EditableControlCardProps) {
  const [editing, setEditing] = useState(false)
  const [editTitle, setEditTitle] = useState(title)
  const [editDescription, setEditDescription] = useState(description)
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    setSaving(true)
    try {
      await onSave(controlId, editTitle, editDescription)
      setEditing(false)
    } catch (err) {
      console.error("Save failed:", err)
    } finally {
      setSaving(false)
    }
  }

  const handleCancel = () => {
    setEditTitle(title)
    setEditDescription(description)
    setEditing(false)
  }

  return (
    <div className="bg-slate-800/50 rounded-lg border border-slate-700 p-4 hover:border-slate-600 transition-colors">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          {/* Identifier Badge & Title */}
          <div className="flex items-start gap-3 mb-2">
            <span className="inline-flex items-center px-2.5 py-1 rounded text-xs font-mono font-medium bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 whitespace-nowrap">
              {controlId}
            </span>
            {editing ? (
              <input
                type="text"
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                className="flex-1 bg-slate-700 text-white rounded px-2 py-1 text-sm border border-slate-600 focus:border-cyan-500 focus:outline-none"
              />
            ) : (
              <h3 className="text-white font-medium leading-tight">{title}</h3>
            )}
          </div>

          {/* Description */}
          {editing ? (
            <textarea
              value={editDescription}
              onChange={(e) => setEditDescription(e.target.value)}
              rows={3}
              className="w-full bg-slate-700 text-slate-300 rounded px-2 py-1 text-sm border border-slate-600 focus:border-cyan-500 focus:outline-none resize-y mb-2"
            />
          ) : (
            description && (
              <p className="text-slate-400 text-sm mb-2">{description}</p>
            )
          )}

          {/* Category Info */}
          {categoryLabel && (
            <p className="text-slate-500 text-xs">{categoryLabel}</p>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-1 flex-shrink-0">
          {editing ? (
            <>
              <Button
                variant="ghost"
                size="icon"
                onClick={handleSave}
                disabled={saving}
                className="text-green-400 hover:text-green-300 hover:bg-slate-700"
              >
                <Check className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={handleCancel}
                disabled={saving}
                className="text-slate-400 hover:text-red-400 hover:bg-slate-700"
              >
                <X className="h-4 w-4" />
              </Button>
            </>
          ) : (
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setEditing(true)}
              className="text-slate-400 hover:text-cyan-400 hover:bg-slate-700"
            >
              <Pencil className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
