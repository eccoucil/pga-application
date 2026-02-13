import { cn } from "@/lib/utils";
import type { AgentState } from "@/hooks/use-questionnaire-agent";

interface QuestionnaireProgressProps {
  answeredCount: number;
  isComplete: boolean;
  state: AgentState;
  estimatedTotal?: number;
}

export function QuestionnaireProgress({
  answeredCount,
  isComplete,
  state,
  estimatedTotal = 4,
}: QuestionnaireProgressProps) {
  const total = Math.max(estimatedTotal, answeredCount + (isComplete ? 0 : 1));

  return (
    <div className="flex items-center gap-3">
      <div className="flex items-center gap-1.5">
        {Array.from({ length: total }).map((_, i) => (
          <div
            key={i}
            className={cn(
              "w-2 h-2 rounded-full transition-colors",
              i < answeredCount
                ? "bg-emerald-500"
                : i === answeredCount && !isComplete
                  ? "bg-purple-500"
                  : "bg-white/20",
            )}
          />
        ))}
      </div>
      <span className="text-xs text-slate-400">
        {isComplete ? (
          <span className="text-emerald-400">Complete</span>
        ) : state === "starting" ? (
          "Starting..."
        ) : (
          `Question ${answeredCount + 1} of ~${total}`
        )}
      </span>
    </div>
  );
}
