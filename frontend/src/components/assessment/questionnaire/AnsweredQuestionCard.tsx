import { CheckCircle2 } from "lucide-react";
import type { QAEntry } from "@/hooks/use-questionnaire-agent";

interface AnsweredQuestionCardProps {
  entry: QAEntry;
  index: number;
}

export function AnsweredQuestionCard({ entry, index }: AnsweredQuestionCardProps) {
  return (
    <div className="group flex items-start gap-3 px-4 py-3 bg-white/[0.03] rounded-xl border border-white/5 opacity-70 hover:opacity-100 transition-opacity">
      <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 flex-shrink-0" />
      <div className="min-w-0 flex-1">
        <p className="text-xs text-slate-500 truncate">
          Q{index + 1}: {entry.question}
        </p>
        <p className="text-sm text-white mt-0.5 truncate">
          {entry.answer}
        </p>
      </div>
    </div>
  );
}
