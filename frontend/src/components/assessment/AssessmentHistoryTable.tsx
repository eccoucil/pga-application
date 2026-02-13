"use client";

import type { AssessmentRecord } from "@/types/assessment";
import {
  Plus,
  Eye,
  Clock,
  CheckCircle,
  AlertCircle,
  XCircle,
} from "lucide-react";

interface AssessmentHistoryTableProps {
  assessments: AssessmentRecord[];
  onSelect: (id: string) => void;
  onNew: () => void;
  onViewFindings?: (id: string) => void;
}

const statusConfig: Record<
  AssessmentRecord["status"],
  { label: string; classes: string; icon: React.ElementType }
> = {
  completed: {
    label: "Completed",
    classes:
      "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
    icon: CheckCircle,
  },
  processing: {
    label: "Processing",
    classes: "bg-amber-500/10 text-amber-400 border border-amber-500/20",
    icon: Clock,
  },
  received: {
    label: "Received",
    classes: "bg-blue-500/10 text-blue-400 border border-blue-500/20",
    icon: Clock,
  },
  failed: {
    label: "Failed",
    classes: "bg-red-500/10 text-red-400 border border-red-500/20",
    icon: XCircle,
  },
  partial: {
    label: "Partial",
    classes: "bg-orange-500/10 text-orange-400 border border-orange-500/20",
    icon: AlertCircle,
  },
};

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function AssessmentHistoryTable({
  assessments,
  onSelect,
  onNew,
  onViewFindings,
}: AssessmentHistoryTableProps) {
  return (
    <div className="bg-[#0f1016]/60 backdrop-blur-md border border-white/10 rounded-2xl overflow-hidden shadow-2xl">
      {/* Header */}
      <div className="flex items-center justify-between p-6 border-b border-white/5">
        <div>
          <h2 className="text-xl font-bold text-white">Assessment History</h2>
          <p className="text-sm text-slate-400 mt-1">
            {assessments.length} assessment{assessments.length !== 1 ? "s" : ""}{" "}
            submitted
          </p>
        </div>
        <button
          onClick={onNew}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white rounded-lg shadow-lg shadow-purple-900/20 transition-all"
        >
          <Plus className="w-4 h-4" />
          New Assessment
        </button>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-white/5">
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                Version
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                Organization
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                Industry
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                Department
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                Documents
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                Date
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-slate-400 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {assessments.map((assessment) => {
              const status = statusConfig[assessment.status] ?? statusConfig.received;
              const StatusIcon = status.icon;

              return (
                <tr
                  key={assessment.id}
                  className="hover:bg-white/5 transition-colors cursor-pointer"
                  onClick={() => onSelect(assessment.id)}
                >
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm font-medium text-purple-300">
                      v{assessment.version}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm text-white">
                      {assessment.organization_name}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm text-slate-300">
                      {assessment.industry_type}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm text-slate-300">
                      {assessment.department}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${status.classes}`}
                    >
                      <StatusIcon className="w-3 h-3" />
                      {status.label}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm text-slate-300">
                      {assessment.documents_count}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm text-slate-400">
                      {formatDate(assessment.created_at)}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelect(assessment.id);
                        }}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-purple-300 bg-purple-500/10 border border-purple-500/20 rounded-lg hover:bg-purple-500/20 hover:text-purple-200 transition-all"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        View
                      </button>
                      {onViewFindings &&
                        (assessment.status === "received" ||
                          assessment.status === "completed") && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              onViewFindings(assessment.id);
                            }}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-emerald-300 bg-emerald-500/10 border border-emerald-500/20 rounded-lg hover:bg-emerald-500/20 hover:text-emerald-200 transition-all"
                          >
                            <CheckCircle className="w-3.5 h-3.5" />
                            Findings
                          </button>
                        )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Empty state */}
      {assessments.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="w-12 h-12 rounded-full bg-purple-500/10 flex items-center justify-center text-purple-400 mb-4">
            <Clock className="w-6 h-6" />
          </div>
          <h3 className="text-sm font-medium text-white mb-1">
            No assessments yet
          </h3>
          <p className="text-xs text-slate-500 mb-6">
            Submit your first assessment to get started
          </p>
          <button
            onClick={onNew}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white rounded-lg shadow-lg shadow-purple-900/20 transition-all"
          >
            <Plus className="w-4 h-4" />
            New Assessment
          </button>
        </div>
      )}
    </div>
  );
}
