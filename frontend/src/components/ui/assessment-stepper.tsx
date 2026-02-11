"use client"

import { Check } from "lucide-react"

export interface AssessmentStep {
  number: number
  title: string
  status: "current" | "completed" | "upcoming"
}

interface AssessmentStepperProps {
  steps: AssessmentStep[]
  className?: string
}

export function AssessmentStepper({ steps, className = "" }: AssessmentStepperProps) {
  const currentStepIndex = steps.findIndex((step) => step.status === "current")
  const progressPercentage = currentStepIndex >= 0 ? ((currentStepIndex + 1) / steps.length) * 100 : 0

  return (
    <div className={`mb-10 relative ${className}`}>
      <div className="flex items-center justify-between relative z-10">
        {steps.map((step, index) => (
          <div key={step.number} className="flex flex-col items-center gap-3 flex-1">
            <div
              className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm border-2 transition-all duration-300 ${
                step.status === "current"
                  ? "bg-gradient-to-tr from-purple-600 to-indigo-600 border-purple-400 text-white shadow-[0_0_15px_rgba(168,85,247,0.5)] scale-110"
                  : step.status === "completed"
                  ? "bg-emerald-500 border-emerald-400 text-white"
                  : "bg-[#0f1016] border-white/10 text-slate-500"
              }`}
            >
              {step.status === "completed" ? <Check className="w-5 h-5" /> : step.number}
            </div>
            <span
              className={`text-xs font-medium uppercase tracking-wider ${
                step.status === "current" ? "text-white" : "text-slate-500"
              }`}
            >
              {step.title}
            </span>
          </div>
        ))}
      </div>

      {/* Progress Line */}
      <div className="absolute top-5 left-0 w-full h-0.5 bg-white/5 -z-0 rounded-full">
        <div
          className="absolute top-0 left-0 h-full bg-gradient-to-r from-purple-600 to-indigo-600 rounded-full transition-all duration-500"
          style={{ width: `${progressPercentage}%` }}
        ></div>
      </div>
    </div>
  )
}
