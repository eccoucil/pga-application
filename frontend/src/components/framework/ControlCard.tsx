"use client"

import { Pencil } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  FrameworkControl,
  isISORequirement,
  isBNMRequirement,
} from "@/types/framework"

interface ControlCardProps {
  control: FrameworkControl
  onEdit: (control: FrameworkControl) => void
}

export function ControlCard({ control, onEdit }: ControlCardProps) {
  // Get display values based on framework type
  const getIdentifier = () => {
    if (isISORequirement(control)) return control.identifier
    if (isBNMRequirement(control)) return control.reference_id
    return ""
  }

  const getTitle = () => {
    if (isISORequirement(control)) return control.title
    if (isBNMRequirement(control)) return control.subsection_title || control.section_title
    return ""
  }

  const getDescription = () => {
    if (isISORequirement(control)) return control.description
    if (isBNMRequirement(control)) return control.requirement_text
    return ""
  }

  const getCategoryInfo = () => {
    if (isISORequirement(control)) {
      return control.category
        ? `${control.category_code || ""} ${control.category}`.trim()
        : control.clause_type === "management"
        ? "Management Clause"
        : "Domain Control"
    }
    if (isBNMRequirement(control)) {
      return `Section ${control.section_number}: ${control.section_title}`
    }
    return ""
  }

  const identifier = getIdentifier()
  const title = getTitle()
  const description = getDescription()
  const categoryInfo = getCategoryInfo()

  return (
    <div className="bg-slate-800/50 rounded-lg border border-slate-700 p-4 hover:border-slate-600 transition-colors">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          {/* Identifier Badge & Title */}
          <div className="flex items-start gap-3 mb-2">
            <span className="inline-flex items-center px-2.5 py-1 rounded text-xs font-mono font-medium bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 whitespace-nowrap">
              {identifier}
            </span>
            <h3 className="text-white font-medium leading-tight">{title}</h3>
          </div>

          {/* Description */}
          {description && (
            <p className="text-slate-400 text-sm line-clamp-2 mb-2">
              {description}
            </p>
          )}

          {/* Category/Section Info */}
          <p className="text-slate-500 text-xs">{categoryInfo}</p>
        </div>

        {/* Edit Button */}
        <Button
          variant="ghost"
          size="icon"
          onClick={() => onEdit(control)}
          className="text-slate-400 hover:text-cyan-400 hover:bg-slate-700 flex-shrink-0"
        >
          <Pencil className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}
