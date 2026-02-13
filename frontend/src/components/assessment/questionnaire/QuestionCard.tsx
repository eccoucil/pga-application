"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";
import type { AgentQuestion } from "@/types/questionnaire";

interface QuestionCardProps {
  question: AgentQuestion;
  questionNumber: number;
  onSubmit: (answer: string) => void;
  disabled?: boolean;
}

export function QuestionCard({
  question,
  questionNumber,
  onSubmit,
  disabled,
}: QuestionCardProps) {
  const [answer, setAnswer] = useState("");
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-focus input on mount
  useEffect(() => {
    // Small delay to ensure the card is rendered and scrolled into view
    const timer = setTimeout(() => inputRef.current?.focus(), 150);
    return () => clearTimeout(timer);
  }, []);

  const currentAnswer = selectedOption ?? answer;
  const canSubmit = currentAnswer.trim().length > 0 && !disabled;

  function handleSubmit() {
    if (!canSubmit) return;
    onSubmit(currentAnswer.trim());
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey && canSubmit) {
      e.preventDefault();
      handleSubmit();
    }
  }

  function handleOptionClick(option: string) {
    if (disabled) return;
    if (selectedOption === option) {
      setSelectedOption(null);
    } else {
      setSelectedOption(option);
      setAnswer("");
    }
  }

  return (
    <div className="bg-[#0f1016]/60 backdrop-blur-md border border-purple-500/20 rounded-2xl p-6 shadow-[0_0_25px_rgba(168,85,247,0.08)]">
      {/* Header with question number */}
      <div className="flex items-start gap-4 mb-4">
        <div className="w-8 h-8 rounded-full bg-purple-500/20 flex items-center justify-center flex-shrink-0">
          <span className="text-sm font-semibold text-purple-300">
            {questionNumber}
          </span>
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-white text-sm leading-relaxed font-medium">
            {question.question}
          </p>
          {question.context && (
            <div className="mt-3 pl-3 border-l-2 border-slate-700">
              <p className="text-xs text-slate-400 leading-relaxed">
                {question.context}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Option chips */}
      {question.options && question.options.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4 ml-12">
          {question.options.map((option) => (
            <button
              key={option}
              type="button"
              disabled={disabled}
              onClick={() => handleOptionClick(option)}
              className={cn(
                "px-3 py-1.5 rounded-lg text-sm border transition-all",
                selectedOption === option
                  ? "border-purple-500/50 bg-purple-500/15 text-purple-200 shadow-[0_0_10px_rgba(168,85,247,0.1)]"
                  : "border-white/10 bg-white/5 text-slate-300 hover:border-white/20 hover:bg-white/[0.07]",
                disabled && "opacity-50 cursor-not-allowed",
              )}
            >
              {option}
            </button>
          ))}
        </div>
      )}

      {/* Text input + submit */}
      <div className="flex items-center gap-2 ml-12">
        <input
          ref={inputRef}
          type="text"
          value={selectedOption ? "" : answer}
          onChange={(e) => {
            setAnswer(e.target.value);
            setSelectedOption(null);
          }}
          onKeyDown={handleKeyDown}
          placeholder={
            selectedOption
              ? "Option selected — press send or type to override"
              : "Type your answer..."
          }
          disabled={disabled}
          className={cn(
            "flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white placeholder:text-slate-500",
            "focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/25 transition-colors",
            disabled && "opacity-50 cursor-not-allowed",
          )}
        />
        <button
          type="button"
          onClick={handleSubmit}
          disabled={!canSubmit}
          className={cn(
            "p-2.5 rounded-xl transition-all flex-shrink-0",
            canSubmit
              ? "bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white shadow-lg shadow-purple-500/20"
              : "bg-white/5 text-slate-600 cursor-not-allowed",
          )}
        >
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
