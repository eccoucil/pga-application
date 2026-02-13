"use client";

import { useRef, useState, type ChangeEvent } from "react";
import {
  Upload,
  X,
  FileText,
  AlertCircle,
  Plus,
  Check,
  ChevronDown,
  Info,
  Loader2,
  Pencil,
  ArrowRight,
} from "lucide-react";
import { cn } from "@/lib/utils";

const industryTypes = [
  "Banking & Financial Services",
  "Insurance",
  "Healthcare",
  "Technology",
  "Manufacturing",
  "Retail",
  "Government",
  "Other",
];

const defaultDepartments = [
  "Information Technology",
  "Human Resources",
  "Finance",
  "Operations",
  "Legal & Compliance",
  "Risk Management",
  "Internal Audit",
  "Security",
  "Customer Service",
  "Marketing",
  "Sales",
  "Research & Development",
];

const allowedFileTypes = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/msword",
  "text/plain",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "application/vnd.ms-excel",
  "text/csv",
];

const allowedExtensions = [
  ".pdf",
  ".docx",
  ".doc",
  ".txt",
  ".xlsx",
  ".xls",
  ".csv",
];

interface AssessmentFormCardProps {
  formData: {
    organizationName: string;
    natureOfBusiness: string;
    industryType: string;
    webDomain: string;
    department: string;
    scopeStatementISMS: string;
    documents: File[];
  };
  formErrors: {
    organizationName?: string;
    natureOfBusiness?: string;
    industryType?: string;
    webDomain?: string;
    department?: string;
    scopeStatementISMS?: string;
    documents?: string;
  };
  readOnly: boolean;
  onFieldChange: (name: string, value: string) => void;
  onDocumentsChange: (files: File[]) => void;
  onRemoveDocument: (index: number) => void;
  onSubmit: (e: React.FormEvent) => void;
  onCancel: () => void;
  onEdit?: () => void;
  isSubmitting: boolean;
  onProceedToFindings?: () => void;
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

function validateFile(file: File): boolean {
  const extension = "." + file.name.split(".").pop()?.toLowerCase();
  return (
    allowedFileTypes.includes(file.type) ||
    allowedExtensions.includes(extension)
  );
}

export function AssessmentFormCard({
  formData,
  formErrors,
  readOnly,
  onFieldChange,
  onDocumentsChange,
  onRemoveDocument,
  onSubmit,
  onCancel,
  onEdit,
  isSubmitting,
  onProceedToFindings,
}: AssessmentFormCardProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [departments, setDepartments] = useState<string[]>(defaultDepartments);
  const [showDepartmentDropdown, setShowDepartmentDropdown] = useState(false);
  const [newDepartment, setNewDepartment] = useState("");
  const [isDragging, setIsDragging] = useState(false);

  const handleInputChange = (
    e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>,
  ) => {
    onFieldChange(e.target.name, e.target.value);
  };

  const handleDepartmentSelect = (dept: string) => {
    onFieldChange("department", dept);
    setShowDepartmentDropdown(false);
  };

  const handleAddDepartment = () => {
    if (newDepartment.trim() && !departments.includes(newDepartment.trim())) {
      const trimmedDept = newDepartment.trim();
      setDepartments((prev) => [...prev, trimmedDept]);
      onFieldChange("department", trimmedDept);
      setNewDepartment("");
      setShowDepartmentDropdown(false);
    }
  };

  const addFiles = (files: File[]) => {
    const validFiles = files.filter(validateFile);
    if (validFiles.length > 0) {
      onDocumentsChange(validFiles);
    }
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    addFiles(files);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    addFiles(files);
  };

  return (
    <div className="bg-[#0f1016]/60 backdrop-blur-md border border-white/10 rounded-2xl overflow-hidden shadow-2xl relative group">
      <div className="absolute -inset-0.5 bg-gradient-to-br from-purple-600/20 to-indigo-600/20 rounded-2xl blur-xl opacity-0 group-hover:opacity-100 transition duration-500"></div>

      {/* Card Header */}
      <div className="relative p-6 text-white">
        <div className="relative flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold">
              Organization Assessment Form
            </h2>
            <p className="text-purple-100 text-sm mt-1 opacity-90">
              {readOnly
                ? "Review the assessment details below"
                : "Please fill in all the required information for the compliance assessment"}
            </p>
          </div>
          {readOnly && onEdit && (
            <button
              type="button"
              onClick={onEdit}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white rounded-lg shadow-lg shadow-purple-900/20 transition-all"
            >
              <Pencil className="w-4 h-4" />
              Edit
            </button>
          )}
        </div>
      </div>

      {/* Form Content */}
      <form onSubmit={onSubmit} className="relative p-8 space-y-8">
        {/* Organization Name */}
        <div className="space-y-2">
          <label
            htmlFor="organizationName"
            className="text-xs font-medium text-slate-400 uppercase tracking-wider"
          >
            Organization Name <span className="text-rose-500">*</span>
          </label>
          <input
            type="text"
            id="organizationName"
            name="organizationName"
            value={formData.organizationName}
            onChange={handleInputChange}
            disabled={readOnly}
            className={cn(
              "w-full bg-black/40 border rounded-lg px-3 py-2.5 text-white text-sm placeholder:text-slate-600 focus:outline-none focus:ring-1 transition-all",
              "disabled:opacity-60 disabled:cursor-not-allowed",
              formErrors.organizationName
                ? "border-red-500/50 focus:border-red-500/50 focus:ring-red-500/50"
                : "border-white/10 focus:border-purple-500/50 focus:ring-purple-500/50",
            )}
            placeholder="Enter organization name"
          />
          {formErrors.organizationName && (
            <div className="flex items-center gap-2 text-red-400 text-xs">
              <AlertCircle className="w-3 h-3" />
              <span>{formErrors.organizationName}</span>
            </div>
          )}
        </div>

        {/* Nature of Business */}
        <div className="space-y-2">
          <label
            htmlFor="natureOfBusiness"
            className="text-xs font-medium text-slate-400 uppercase tracking-wider"
          >
            Nature of Business <span className="text-rose-500">*</span>
          </label>
          <textarea
            id="natureOfBusiness"
            name="natureOfBusiness"
            value={formData.natureOfBusiness}
            onChange={handleInputChange}
            disabled={readOnly}
            rows={4}
            className={cn(
              "w-full bg-black/40 border rounded-lg px-3 py-2.5 text-white text-sm placeholder:text-slate-600 focus:outline-none focus:ring-1 transition-all resize-none",
              "disabled:opacity-60 disabled:cursor-not-allowed",
              formErrors.natureOfBusiness
                ? "border-red-500/50 focus:border-red-500/50 focus:ring-red-500/50"
                : "border-white/10 focus:border-purple-500/50 focus:ring-purple-500/50",
            )}
            placeholder="Describe the nature of your business, products, services, and operations..."
          />
          {formErrors.natureOfBusiness && (
            <div className="flex items-center gap-2 text-red-400 text-xs">
              <AlertCircle className="w-3 h-3" />
              <span>{formErrors.natureOfBusiness}</span>
            </div>
          )}
        </div>

        {/* Industry Type */}
        <div className="space-y-2">
          <label
            htmlFor="industryType"
            className="text-xs font-medium text-slate-400 uppercase tracking-wider"
          >
            Industry Type <span className="text-rose-500">*</span>
          </label>
          <div className="relative">
            <select
              id="industryType"
              name="industryType"
              value={formData.industryType}
              onChange={handleInputChange}
              disabled={readOnly}
              className={cn(
                "w-full bg-black/40 border rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:ring-1 transition-all appearance-none cursor-pointer",
                "disabled:opacity-60 disabled:cursor-not-allowed",
                formErrors.industryType
                  ? "border-red-500/50 focus:border-red-500/50 focus:ring-red-500/50"
                  : "border-white/10 focus:border-purple-500/50 focus:ring-purple-500/50",
              )}
            >
              <option value="" disabled>
                Select industry type
              </option>
              {industryTypes.map((industry) => (
                <option key={industry} value={industry}>
                  {industry}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
          </div>
          {formErrors.industryType && (
            <div className="flex items-center gap-2 text-red-400 text-xs">
              <AlertCircle className="w-3 h-3" />
              <span>{formErrors.industryType}</span>
            </div>
          )}
        </div>

        {/* Web Domain */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">
              Web Domain for Crawling
            </label>
            <span className="text-xs text-slate-500 bg-white/5 px-2 py-0.5 rounded border border-white/5">
              Optional
            </span>
          </div>
          <input
            type="text"
            id="webDomain"
            name="webDomain"
            value={formData.webDomain}
            onChange={handleInputChange}
            disabled={readOnly}
            className={cn(
              "w-full bg-black/40 border rounded-lg px-3 py-2.5 text-white text-sm placeholder:text-slate-600 focus:outline-none focus:ring-1 transition-all",
              "disabled:opacity-60 disabled:cursor-not-allowed",
              formErrors.webDomain
                ? "border-red-500/50 focus:border-red-500/50 focus:ring-red-500/50"
                : "border-white/10 focus:border-purple-500/50 focus:ring-purple-500/50",
            )}
            placeholder="example.com"
          />
          <p className="text-xs text-slate-500 flex items-center gap-1">
            <Info className="w-3 h-3" />
            Enter the domain to crawl for policy documents and compliance
            information
          </p>
          {formErrors.webDomain && (
            <div className="flex items-center gap-2 text-red-400 text-xs">
              <AlertCircle className="w-3 h-3" />
              <span>{formErrors.webDomain}</span>
            </div>
          )}
        </div>

        {/* Department - Creatable Dropdown */}
        <div className="space-y-2">
          <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">
            Department <span className="text-rose-500">*</span>
          </label>
          <div className="relative">
            <button
              type="button"
              onClick={() => {
                if (!readOnly) setShowDepartmentDropdown(!showDepartmentDropdown);
              }}
              disabled={readOnly}
              className={cn(
                "w-full bg-black/40 border rounded-lg px-3 py-2.5 text-left flex items-center justify-between text-white text-sm focus:outline-none focus:ring-1 transition-all",
                "disabled:opacity-60 disabled:cursor-not-allowed",
                formErrors.department
                  ? "border-red-500/50 focus:border-red-500/50 focus:ring-red-500/50"
                  : "border-white/10 focus:border-purple-500/50 focus:ring-purple-500/50",
                !formData.department && "text-slate-500",
              )}
            >
              <span>
                {formData.department || "Select or add department"}
              </span>
              <ChevronDown
                className={cn(
                  "w-4 h-4 text-slate-500 transition-transform",
                  showDepartmentDropdown && "rotate-180",
                )}
              />
            </button>

            {showDepartmentDropdown && !readOnly && (
              <div className="absolute z-[200] w-full mt-1 bg-[#0f1016] border border-white/10 rounded-lg shadow-xl max-h-60 overflow-y-auto">
                {/* Add new department input */}
                <div className="p-2 border-b border-white/10">
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      value={newDepartment}
                      onChange={(e) => setNewDepartment(e.target.value)}
                      placeholder="Add new department..."
                      className="flex-1 bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-slate-600 focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/50"
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          e.preventDefault();
                          handleAddDepartment();
                        }
                      }}
                    />
                    <button
                      type="button"
                      onClick={handleAddDepartment}
                      disabled={!newDepartment.trim()}
                      className="p-2 bg-purple-600 text-white rounded-lg hover:bg-purple-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      <Plus className="h-4 w-4" />
                    </button>
                  </div>
                </div>

                {/* Department options */}
                {departments.map((dept) => (
                  <button
                    key={dept}
                    type="button"
                    onClick={() => handleDepartmentSelect(dept)}
                    className={cn(
                      "w-full px-4 py-2 text-left text-sm hover:bg-white/5 flex items-center justify-between text-slate-300",
                      formData.department === dept &&
                        "bg-purple-500/10 text-purple-300",
                    )}
                  >
                    <span>{dept}</span>
                    {formData.department === dept && (
                      <Check className="h-4 w-4" />
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>
          {formErrors.department && (
            <div className="flex items-center gap-2 text-red-400 text-xs">
              <AlertCircle className="w-3 h-3" />
              <span>{formErrors.department}</span>
            </div>
          )}
        </div>

        {/* Scope Statement ISMS */}
        <div className="space-y-2">
          <label
            htmlFor="scopeStatementISMS"
            className="text-xs font-medium text-slate-400 uppercase tracking-wider"
          >
            Scope Statement ISMS <span className="text-rose-500">*</span>
          </label>
          <textarea
            id="scopeStatementISMS"
            name="scopeStatementISMS"
            value={formData.scopeStatementISMS}
            onChange={handleInputChange}
            disabled={readOnly}
            rows={6}
            className={cn(
              "w-full bg-black/40 border rounded-lg px-3 py-2.5 text-white text-sm placeholder:text-slate-600 focus:outline-none focus:ring-1 transition-all resize-none",
              "disabled:opacity-60 disabled:cursor-not-allowed",
              formErrors.scopeStatementISMS
                ? "border-red-500/50 focus:border-red-500/50 focus:ring-red-500/50"
                : "border-white/10 focus:border-purple-500/50 focus:ring-purple-500/50",
            )}
            placeholder="Enter the scope statement for your Information Security Management System (ISMS)..."
          />
          {formErrors.scopeStatementISMS && (
            <div className="flex items-center gap-2 text-red-400 text-xs">
              <AlertCircle className="w-3 h-3" />
              <span>{formErrors.scopeStatementISMS}</span>
            </div>
          )}
        </div>

        {/* File Upload - hidden in readOnly mode */}
        {!readOnly && (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                Upload Documents
              </label>
              <span className="text-xs text-slate-500 bg-white/5 px-2 py-0.5 rounded border border-white/5">
                Optional
              </span>
            </div>
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={cn(
                "border-2 border-dashed rounded-xl p-8 transition-all hover:border-purple-500/50 hover:bg-purple-500/5 cursor-pointer group/upload",
                isDragging
                  ? "border-purple-500/50 bg-purple-500/10"
                  : formErrors.documents
                    ? "border-red-500/50 bg-red-500/5"
                    : "border-white/10",
              )}
            >
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".pdf,.docx,.doc,.txt,.xlsx,.xls,.csv"
                onChange={handleFileChange}
                className="hidden"
              />
              <div className="flex flex-col items-center justify-center text-center">
                <div className="w-12 h-12 rounded-full bg-purple-500/10 flex items-center justify-center text-purple-400 mb-4 group-hover/upload:scale-110 transition-transform">
                  <Upload className="w-6 h-6" />
                </div>
                <h3 className="text-sm font-medium text-white mb-1">
                  Click to upload or drag and drop
                </h3>
                <p className="text-xs text-slate-500">
                  PDF, DOCX, TXT, XLSX, or CSV (max 10MB each)
                </p>
              </div>
            </div>

            {/* File list */}
            {formData.documents.length > 0 && (
              <div className="mt-4 space-y-2">
                {formData.documents.map((file, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-3 bg-black/40 border border-white/10 rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <FileText className="h-5 w-5 text-slate-400" />
                      <div>
                        <p className="text-sm font-medium text-white truncate max-w-xs">
                          {file.name}
                        </p>
                        <p className="text-xs text-slate-500">
                          {formatFileSize(file.size)}
                        </p>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => onRemoveDocument(index)}
                      className="p-1 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {formErrors.documents && (
              <div className="flex items-center gap-2 text-red-400 text-xs">
                <AlertCircle className="w-3 h-3" />
                <span>{formErrors.documents}</span>
              </div>
            )}
          </div>
        )}

        {/* Footer Actions */}
        <div className="flex justify-end gap-3 pt-6 border-t border-white/5 mt-2">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 text-sm font-medium text-slate-400 hover:text-white transition-colors"
          >
            {readOnly ? "Back" : "Cancel"}
          </button>
          {readOnly && onProceedToFindings && (
            <button
              type="button"
              onClick={onProceedToFindings}
              className="flex items-center gap-2 px-6 py-2 text-sm font-medium bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white rounded-lg shadow-lg shadow-purple-900/20 transition-all"
            >
              Proceed to Findings
              <ArrowRight className="w-4 h-4" />
            </button>
          )}
          {!readOnly && (
            <button
              type="submit"
              disabled={isSubmitting}
              className={cn(
                "px-6 py-2 text-sm font-medium bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white rounded-lg shadow-lg shadow-purple-900/20 transition-all",
                isSubmitting && "opacity-50 cursor-not-allowed",
              )}
            >
              {isSubmitting ? (
                <span className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Submitting...</span>
                </span>
              ) : (
                "Submit Assessment"
              )}
            </button>
          )}
        </div>
      </form>
    </div>
  );
}
