"use client"

import { type LucideIcon, CheckCircle2, Lock } from "lucide-react"
import { cn } from "@/lib/utils"

export interface Step {
  id: string
  label: string
  description?: string
  icon: LucideIcon
}

export type StepStatus = "completed" | "active" | "locked"

interface StepperProps {
  steps: Step[]
  stepStatuses: StepStatus[]
  onStepClick?: (step: Step, index: number) => void
  className?: string
}

export function Stepper({ steps, stepStatuses, onStepClick, className }: StepperProps) {
  return (
    <div className={cn("w-full", className)}>
      {/* Desktop horizontal layout */}
      <div className="hidden sm:flex items-center justify-center">
        {steps.map((step, index) => {
          const status = stepStatuses[index] || "locked"
          const Icon = step.icon
          const isLast = index === steps.length - 1
          const isClickable = status !== "locked"

          return (
            <div key={step.id} className="flex items-center">
              {/* Step */}
              <button
                onClick={() => isClickable && onStepClick?.(step, index)}
                disabled={!isClickable}
                className={cn(
                  "flex flex-col items-center gap-2 px-4 py-2 rounded-lg transition-all duration-200",
                  isClickable && "hover:bg-slate-800/50 cursor-pointer",
                  !isClickable && "cursor-not-allowed opacity-60"
                )}
              >
                {/* Step circle */}
                <div
                  className={cn(
                    "relative w-14 h-14 rounded-full flex items-center justify-center transition-all duration-300",
                    status === "completed" && "bg-green-500/20 border-2 border-green-500/50",
                    status === "active" && "bg-cyan-500/20 border-2 border-cyan-500/50 shadow-[0_0_15px_rgba(6,182,212,0.3)]",
                    status === "locked" && "bg-slate-700/50 border-2 border-slate-600/50"
                  )}
                >
                  {status === "completed" ? (
                    <CheckCircle2 className="h-7 w-7 text-green-400" />
                  ) : status === "locked" ? (
                    <div className="relative">
                      <Icon className="h-6 w-6 text-slate-500" />
                      <Lock className="absolute -bottom-1 -right-1 h-4 w-4 text-slate-400 bg-slate-700 rounded-full p-0.5" />
                    </div>
                  ) : (
                    <Icon className="h-6 w-6 text-cyan-400" />
                  )}
                </div>

                {/* Step label */}
                <div className="text-center">
                  <span
                    className={cn(
                      "text-sm font-medium block",
                      status === "completed" && "text-green-400",
                      status === "active" && "text-cyan-400",
                      status === "locked" && "text-slate-500"
                    )}
                  >
                    {step.label}
                  </span>
                  {step.description && (
                    <span
                      className={cn(
                        "text-xs block mt-0.5",
                        status === "completed" && "text-green-400/70",
                        status === "active" && "text-cyan-400/70",
                        status === "locked" && "text-slate-600"
                      )}
                    >
                      {step.description}
                    </span>
                  )}
                </div>
              </button>

              {/* Connector line */}
              {!isLast && (
                <div
                  className={cn(
                    "w-16 h-0.5 mx-2 transition-all duration-300",
                    stepStatuses[index] === "completed"
                      ? "bg-gradient-to-r from-green-500 to-green-500/50"
                      : "bg-slate-700"
                  )}
                />
              )}
            </div>
          )
        })}
      </div>

      {/* Mobile vertical layout */}
      <div className="sm:hidden space-y-3">
        {steps.map((step, index) => {
          const status = stepStatuses[index] || "locked"
          const Icon = step.icon
          const isClickable = status !== "locked"

          return (
            <button
              key={step.id}
              onClick={() => isClickable && onStepClick?.(step, index)}
              disabled={!isClickable}
              className={cn(
                "w-full flex items-center gap-4 p-4 rounded-lg transition-all duration-200",
                status === "completed" && "bg-green-500/10 border border-green-500/30",
                status === "active" && "bg-cyan-500/10 border border-cyan-500/30",
                status === "locked" && "bg-slate-800/50 border border-slate-700/50",
                isClickable && "hover:bg-slate-800/70 cursor-pointer",
                !isClickable && "cursor-not-allowed"
              )}
            >
              {/* Step circle */}
              <div
                className={cn(
                  "flex-shrink-0 w-12 h-12 rounded-full flex items-center justify-center",
                  status === "completed" && "bg-green-500/20",
                  status === "active" && "bg-cyan-500/20",
                  status === "locked" && "bg-slate-700/50"
                )}
              >
                {status === "completed" ? (
                  <CheckCircle2 className="h-6 w-6 text-green-400" />
                ) : status === "locked" ? (
                  <div className="relative">
                    <Icon className="h-5 w-5 text-slate-500" />
                    <Lock className="absolute -bottom-0.5 -right-0.5 h-3 w-3 text-slate-400" />
                  </div>
                ) : (
                  <Icon className="h-5 w-5 text-cyan-400" />
                )}
              </div>

              {/* Step content */}
              <div className="flex-1 text-left">
                <span
                  className={cn(
                    "text-sm font-medium block",
                    status === "completed" && "text-green-400",
                    status === "active" && "text-cyan-400",
                    status === "locked" && "text-slate-500"
                  )}
                >
                  Step {index + 1}: {step.label}
                </span>
                {step.description && (
                  <span
                    className={cn(
                      "text-xs block mt-0.5",
                      status === "completed" && "text-green-400/70",
                      status === "active" && "text-cyan-400/70",
                      status === "locked" && "text-slate-600"
                    )}
                  >
                    {step.description}
                  </span>
                )}
              </div>

              {/* Status indicator */}
              <div className="flex-shrink-0">
                {status === "completed" && (
                  <span className="text-xs text-green-400 bg-green-500/20 px-2 py-1 rounded">
                    Complete
                  </span>
                )}
                {status === "active" && (
                  <span className="text-xs text-cyan-400 bg-cyan-500/20 px-2 py-1 rounded">
                    Start
                  </span>
                )}
                {status === "locked" && (
                  <span className="text-xs text-slate-500 bg-slate-700/50 px-2 py-1 rounded">
                    Locked
                  </span>
                )}
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
