"use client";

import { useEffect, useState, useRef, FormEvent, ChangeEvent } from "react";
import { useParams, useRouter } from "next/navigation";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { useClient } from "@/contexts/ClientContext";
import { useProject } from "@/contexts/ProjectContext";
import { useAuth } from "@/contexts/AuthContext";
import { getClient, getProject, supabase } from "@/lib/supabase";
import { useToast } from "@/hooks/use-toast";
import {
  AssessmentStepper,
  type AssessmentStep,
} from "@/components/ui/assessment-stepper";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import type { AssessmentResponse } from "@/types/assessment";
import {
  Loader2,
  ArrowLeft,
  Upload,
  X,
  FileText,
  AlertCircle,
  Plus,
  Check,
  ChevronDown,
  Info,
  Calendar,
  Briefcase,
  FileCheck,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface FormData {
  organizationName: string;
  natureOfBusiness: string;
  industryType: string;
  webDomain: string;
  department: string;
  scopeStatementISMS: string;
  documents: File[];
}

interface FormErrors {
  organizationName?: string;
  natureOfBusiness?: string;
  industryType?: string;
  webDomain?: string;
  department?: string;
  scopeStatementISMS?: string;
  documents?: string;
}

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

const STORAGE_KEY_PREFIX = "assessment-form-";

/** Serializable form fields only (no File[]) */
type StoredFormData = Pick<
  FormData,
  | "organizationName"
  | "natureOfBusiness"
  | "industryType"
  | "webDomain"
  | "department"
  | "scopeStatementISMS"
>;

function getStoredForm(projectId: string): StoredFormData | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(`${STORAGE_KEY_PREFIX}${projectId}`);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as StoredFormData;
    if (typeof parsed !== "object" || parsed === null) return null;
    return {
      organizationName:
        typeof parsed.organizationName === "string"
          ? parsed.organizationName
          : "",
      natureOfBusiness:
        typeof parsed.natureOfBusiness === "string"
          ? parsed.natureOfBusiness
          : "",
      industryType:
        typeof parsed.industryType === "string" ? parsed.industryType : "",
      webDomain: typeof parsed.webDomain === "string" ? parsed.webDomain : "",
      department:
        typeof parsed.department === "string" ? parsed.department : "",
      scopeStatementISMS:
        typeof parsed.scopeStatementISMS === "string"
          ? parsed.scopeStatementISMS
          : "",
    };
  } catch {
    return null;
  }
}

function setStoredForm(projectId: string, data: StoredFormData): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.setItem(
      `${STORAGE_KEY_PREFIX}${projectId}`,
      JSON.stringify(data),
    );
  } catch {
    // ignore quota or other storage errors
  }
}


export default function AssessmentPage() {
  const params = useParams();
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const { selectedClient, setSelectedClient } = useClient();
  const { selectedProject, setSelectedProject } = useProject();
  const { toast } = useToast();
  const clientId = params.id as string;
  const projectId = params.projectId as string;
  const [loading, setLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showLoadingModal, setShowLoadingModal] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const hasHydratedRef = useRef(false);

  const [formData, setFormData] = useState<FormData>({
    organizationName: "",
    natureOfBusiness: "",
    industryType: "",
    webDomain: "",
    department: "",
    scopeStatementISMS: "",
    documents: [],
  });

  const [errors, setErrors] = useState<FormErrors>({});
  const [departments, setDepartments] = useState<string[]>(defaultDepartments);
  const [showDepartmentDropdown, setShowDepartmentDropdown] = useState(false);
  const [newDepartment, setNewDepartment] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [steps, setSteps] = useState<AssessmentStep[]>([
    { number: 1, title: "Scope", status: "current" },
    { number: 2, title: "Questionnaire", status: "upcoming" },
  ]);

  // Fetch client and project data if not in context
  useEffect(() => {
    const fetchData = async () => {
      if (!authLoading && user) {
        setLoading(true);
        try {
          // Fetch client if not in context
          if (!selectedClient && clientId) {
            const { data: client, error: clientError } =
              await getClient(clientId);
            if (clientError || !client) {
              router.push("/clients");
              return;
            }
            setSelectedClient(client);
          }

          // Fetch project if not in context
          if (!selectedProject && projectId) {
            const { data: project, error: projectError } =
              await getProject(projectId);
            if (projectError || !project) {
              router.push(`/clients/${clientId}/projects`);
              return;
            }
            setSelectedProject(project);
          }
        } catch {
          router.push("/clients");
        } finally {
          setLoading(false);
        }
      }
    };

    fetchData();
  }, [clientId, projectId, selectedClient, selectedProject, authLoading, user]);

  // Hydrate form from sessionStorage (back from findings) or from API (existing assessment)
  useEffect(() => {
    if (
      typeof window === "undefined" ||
      !projectId ||
      !clientId ||
      loading ||
      authLoading ||
      !user
    )
      return;
    if (hasHydratedRef.current) return;
    hasHydratedRef.current = true;

    const stored = getStoredForm(projectId);
    const hasStored =
      stored &&
      (stored.organizationName?.trim() ||
        stored.natureOfBusiness?.trim() ||
        stored.industryType?.trim() ||
        stored.department?.trim() ||
        stored.scopeStatementISMS?.trim() ||
        stored.webDomain?.trim());

    if (hasStored && stored) {
      setFormData((prev) => ({
        ...prev,
        ...stored,
        documents: prev.documents,
      }));
      return;
    }

    const prefetchFromApi = async () => {
      try {
        const {
          data: { session },
        } = await supabase.auth.getSession();
        const apiUrl =
          process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
        const res = await fetch(
          `${apiUrl}/assessment/findings?client_id=${encodeURIComponent(clientId)}&project_id=${encodeURIComponent(projectId)}`,
          {
            method: "GET",
            headers: {
              "Content-Type": "application/json",
              ...(session?.access_token
                ? { Authorization: `Bearer ${session.access_token}` }
                : {}),
            },
          },
        );
        if (!res.ok) return;
        const data: AssessmentResponse = await res.json();
        const ctx = data.organization_context;
        const crawledIndustry = ctx.industry_type ?? "";
        const validIndustry = industryTypes.includes(crawledIndustry)
          ? crawledIndustry
          : "";
        setFormData((prev) => ({
          ...prev,
          organizationName: ctx.organization_name ?? "",
          natureOfBusiness: "",
          industryType: validIndustry,
          webDomain: ctx.web_domain ?? "",
          department: ctx.department ?? "",
          scopeStatementISMS: ctx.scope_statement_preview ?? "",
          documents: prev.documents,
        }));
      } catch {
        // leave form as-is
      }
    };

    prefetchFromApi();
  }, [projectId, clientId, loading, authLoading, user]);

  // Persist serializable form fields to sessionStorage (debounced)
  useEffect(() => {
    if (!projectId) return;
    const stored: StoredFormData = {
      organizationName: formData.organizationName,
      natureOfBusiness: formData.natureOfBusiness,
      industryType: formData.industryType,
      webDomain: formData.webDomain,
      department: formData.department,
      scopeStatementISMS: formData.scopeStatementISMS,
    };
    const hasAny =
      stored.organizationName?.trim() ||
      stored.natureOfBusiness?.trim() ||
      stored.industryType?.trim() ||
      stored.department?.trim() ||
      stored.scopeStatementISMS?.trim() ||
      stored.webDomain?.trim();
    if (!hasAny) return;

    const t = setTimeout(() => {
      setStoredForm(projectId, stored);
    }, 400);
    return () => clearTimeout(t);
  }, [
    projectId,
    formData.organizationName,
    formData.natureOfBusiness,
    formData.industryType,
    formData.webDomain,
    formData.department,
    formData.scopeStatementISMS,
  ]);

  const validateForm = (): boolean => {
    const newErrors: FormErrors = {};

    if (!formData.organizationName.trim()) {
      newErrors.organizationName = "Organization name is required";
    } else if (formData.organizationName.trim().length < 2) {
      newErrors.organizationName =
        "Organization name must be at least 2 characters";
    }

    if (!formData.natureOfBusiness.trim()) {
      newErrors.natureOfBusiness = "Nature of business is required";
    } else if (formData.natureOfBusiness.trim().length < 10) {
      newErrors.natureOfBusiness =
        "Please provide a more detailed description (at least 10 characters)";
    }

    if (!formData.industryType) {
      newErrors.industryType = "Please select an industry type";
    }

    // Web domain is optional, but validate format if provided
    if (formData.webDomain.trim()) {
      const domainRegex =
        /^([a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$/;
      if (!domainRegex.test(formData.webDomain.trim())) {
        newErrors.webDomain = "Please enter a valid domain (e.g., example.com)";
      }
    }

    if (!formData.department) {
      newErrors.department = "Please select or add a department";
    }

    if (!formData.scopeStatementISMS.trim()) {
      newErrors.scopeStatementISMS = "Scope Statement ISMS is required";
    } else if (formData.scopeStatementISMS.trim().length < 10) {
      newErrors.scopeStatementISMS =
        "Please provide a more detailed scope statement (at least 10 characters)";
    }

    // Documents are now optional - no validation needed

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleInputChange = (
    e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>,
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (errors[name as keyof FormErrors]) {
      setErrors((prev) => ({ ...prev, [name]: undefined }));
    }
  };

  const handleDepartmentSelect = (dept: string) => {
    setFormData((prev) => ({ ...prev, department: dept }));
    setShowDepartmentDropdown(false);
    if (errors.department) {
      setErrors((prev) => ({ ...prev, department: undefined }));
    }
  };

  const handleAddDepartment = () => {
    if (newDepartment.trim() && !departments.includes(newDepartment.trim())) {
      const trimmedDept = newDepartment.trim();
      setDepartments((prev) => [...prev, trimmedDept]);
      setFormData((prev) => ({ ...prev, department: trimmedDept }));
      setNewDepartment("");
      setShowDepartmentDropdown(false);
      if (errors.department) {
        setErrors((prev) => ({ ...prev, department: undefined }));
      }
    }
  };

  const validateFile = (file: File): boolean => {
    const extension = "." + file.name.split(".").pop()?.toLowerCase();
    return (
      allowedFileTypes.includes(file.type) ||
      allowedExtensions.includes(extension)
    );
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    addFiles(files);
  };

  const addFiles = (files: File[]) => {
    const validFiles = files.filter(validateFile);
    const invalidCount = files.length - validFiles.length;

    if (invalidCount > 0) {
      toast({
        title: "Invalid files",
        description: `${invalidCount} file(s) were not added. Only PDF, DOCX, TXT, XLSX, and CSV files are allowed.`,
        variant: "destructive",
      });
    }

    if (validFiles.length > 0) {
      setFormData((prev) => ({
        ...prev,
        documents: [...prev.documents, ...validFiles],
      }));
      if (errors.documents) {
        setErrors((prev) => ({ ...prev, documents: undefined }));
      }
    }
  };

  const handleRemoveFile = (index: number) => {
    setFormData((prev) => ({
      ...prev,
      documents: prev.documents.filter((_, i) => i !== index),
    }));
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

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    // Validation removed for stepper navigation
    // if (!validateForm()) {
    //   toast({
    //     title: "Validation Error",
    //     description: "Please fill in all required fields correctly.",
    //     variant: "destructive",
    //   })
    //   return
    // }

    setIsSubmitting(true);
    setShowLoadingModal(true);

    try {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session?.access_token) {
        throw new Error("Authentication required. Please log in again.");
      }

      const API_URL =
        process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
      const formDataToSubmit = new FormData();

      formDataToSubmit.append("client_id", clientId);
      formDataToSubmit.append("project_id", projectId);
      formDataToSubmit.append("organization_name", formData.organizationName);
      formDataToSubmit.append("nature_of_business", formData.natureOfBusiness);
      formDataToSubmit.append("industry_type", formData.industryType);
      formDataToSubmit.append("department", formData.department);
      formDataToSubmit.append(
        "scope_statement_isms",
        formData.scopeStatementISMS,
      );

      if (formData.webDomain.trim()) {
        formDataToSubmit.append("web_domain", formData.webDomain.trim());
      }

      // Add documents if any
      formData.documents.forEach((file) => {
        formDataToSubmit.append("documents", file);
      });

      const response = await fetch(`${API_URL}/assessment/submit`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
        body: formDataToSubmit,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.detail || `Failed to submit assessment: ${response.status}`,
        );
      }

      const result: AssessmentResponse = await response.json();

      setShowLoadingModal(false);

      toast({
        title: "Success",
        description: "Assessment form submitted successfully.",
      });
    } catch (error) {
      setShowLoadingModal(false);
      toast({
        title: "Error",
        description:
          error instanceof Error
            ? error.message
            : "Failed to submit assessment. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const getFileIcon = (fileName: string) => {
    return <FileText className="h-5 w-5 text-slate-400" />;
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  if (authLoading || loading) {
    return (
      <DashboardLayout>
        <div className="flex justify-center items-center min-h-[400px]">
          <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
        </div>
      </DashboardLayout>
    );
  }

  if (!user) {
    return null;
  }

  const formatDate = (dateString: string | null | undefined) => {
    if (!dateString) return "Not set";
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
      case "in-progress":
        return "bg-blue-500/10 text-blue-400 border-blue-500/20";
      case "on-hold":
        return "bg-amber-500/10 text-amber-400 border-amber-500/20";
      default:
        return "bg-slate-500/10 text-slate-400 border-slate-500/20";
    }
  };

  return (
    <DashboardLayout>
      <div className="max-w-4xl mx-auto pb-10">
        {/* Back Button - Top Left */}
        <button
          onClick={() => router.push(`/clients/${clientId}/projects`)}
          className="mb-6 flex items-center gap-2 px-4 py-2.5 bg-[#0f1016]/80 backdrop-blur-md border border-white/10 rounded-lg text-slate-300 hover:text-white hover:bg-white/10 transition-all shadow-lg hover:shadow-xl hover:border-purple-500/30 group w-fit"
          title="Back to Projects"
        >
          <ArrowLeft className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" />
          <span className="text-sm font-medium">Back</span>
        </button>

        {/* Project Details */}
        {selectedProject && (
          <div className="bg-[#0f1016]/60 backdrop-blur-md border border-white/10 rounded-2xl p-6 mb-6">
            <div className="flex items-start justify-between mb-4">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <Briefcase className="w-5 h-5 text-purple-400" />
                  <h2 className="text-xl font-semibold text-white">
                    {selectedProject.name}
                  </h2>
                </div>
                {selectedProject.description && (
                  <p className="text-slate-400 text-sm ml-8 mb-4">
                    {selectedProject.description}
                  </p>
                )}
              </div>
              <span
                className={`px-3 py-1 rounded-full text-xs font-medium border backdrop-blur-sm ${getStatusColor(
                  selectedProject.status,
                )}`}
              >
                {selectedProject.status
                  .replace("-", " ")
                  .replace(/\b\w/g, (l) => l.toUpperCase())}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 ml-8">
              {/* Frameworks */}
              {selectedProject.framework &&
                selectedProject.framework.length > 0 && (
                  <div className="flex items-start gap-3">
                    <FileCheck className="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">
                        Compliance Frameworks
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {selectedProject.framework.map((fw, idx) => (
                          <span
                            key={idx}
                            className="px-2 py-1 bg-purple-500/10 text-purple-300 text-xs rounded border border-purple-500/20"
                          >
                            {fw}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

              {/* Dates */}
              <div className="flex items-start gap-3">
                <Calendar className="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">
                    Timeline
                  </p>
                  <div className="space-y-1">
                    <p className="text-sm text-white">
                      <span className="text-slate-500">Start: </span>
                      {formatDate(selectedProject.start_date)}
                    </p>
                    <p className="text-sm text-white">
                      <span className="text-slate-500">End: </span>
                      {formatDate(selectedProject.end_date)}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Divider */}
        <div className="h-px bg-gradient-to-r from-transparent via-white/10 to-transparent mb-8"></div>

        {/* Stepper */}
        <AssessmentStepper steps={steps} />

        {/* Form Card */}
        <div className="bg-[#0f1016]/60 backdrop-blur-md border border-white/10 rounded-2xl overflow-hidden shadow-2xl relative group">
          <div className="absolute -inset-0.5 bg-gradient-to-br from-purple-600/20 to-indigo-600/20 rounded-2xl blur-xl opacity-0 group-hover:opacity-100 transition duration-500"></div>

          {/* Card Header */}
          <div className="relative p-6 text-white">
            <div className="relative">
              <h2 className="text-xl font-bold">
                Organization Assessment Form
              </h2>
              <p className="text-purple-100 text-sm mt-1 opacity-90">
                Please fill in all the required information for the compliance
                assessment
              </p>
            </div>
          </div>

          {/* Form Content */}
          <form onSubmit={handleSubmit} className="relative p-8 space-y-8">
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
                className={cn(
                  "w-full bg-black/40 border rounded-lg px-3 py-2.5 text-white text-sm placeholder:text-slate-600 focus:outline-none focus:ring-1 transition-all",
                  errors.organizationName
                    ? "border-red-500/50 focus:border-red-500/50 focus:ring-red-500/50"
                    : "border-white/10 focus:border-purple-500/50 focus:ring-purple-500/50",
                )}
                placeholder="Enter organization name"
              />
              {errors.organizationName && (
                <div className="flex items-center gap-2 text-red-400 text-xs">
                  <AlertCircle className="w-3 h-3" />
                  <span>{errors.organizationName}</span>
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
                rows={4}
                className={cn(
                  "w-full bg-black/40 border rounded-lg px-3 py-2.5 text-white text-sm placeholder:text-slate-600 focus:outline-none focus:ring-1 transition-all resize-none",
                  errors.natureOfBusiness
                    ? "border-red-500/50 focus:border-red-500/50 focus:ring-red-500/50"
                    : "border-white/10 focus:border-purple-500/50 focus:ring-purple-500/50",
                )}
                placeholder="Describe the nature of your business, products, services, and operations..."
              />
              {errors.natureOfBusiness && (
                <div className="flex items-center gap-2 text-red-400 text-xs">
                  <AlertCircle className="w-3 h-3" />
                  <span>{errors.natureOfBusiness}</span>
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
                  className={cn(
                    "w-full bg-black/40 border rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:ring-1 transition-all appearance-none cursor-pointer",
                    errors.industryType
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
              {errors.industryType && (
                <div className="flex items-center gap-2 text-red-400 text-xs">
                  <AlertCircle className="w-3 h-3" />
                  <span>{errors.industryType}</span>
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
                className={cn(
                  "w-full bg-black/40 border rounded-lg px-3 py-2.5 text-white text-sm placeholder:text-slate-600 focus:outline-none focus:ring-1 transition-all",
                  errors.webDomain
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
              {errors.webDomain && (
                <div className="flex items-center gap-2 text-red-400 text-xs">
                  <AlertCircle className="w-3 h-3" />
                  <span>{errors.webDomain}</span>
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
                  onClick={() =>
                    setShowDepartmentDropdown(!showDepartmentDropdown)
                  }
                  className={cn(
                    "w-full bg-black/40 border rounded-lg px-3 py-2.5 text-left flex items-center justify-between text-white text-sm focus:outline-none focus:ring-1 transition-all",
                    errors.department
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

                {showDepartmentDropdown && (
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
              {errors.department && (
                <div className="flex items-center gap-2 text-red-400 text-xs">
                  <AlertCircle className="w-3 h-3" />
                  <span>{errors.department}</span>
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
                rows={6}
                className={cn(
                  "w-full bg-black/40 border rounded-lg px-3 py-2.5 text-white text-sm placeholder:text-slate-600 focus:outline-none focus:ring-1 transition-all resize-none",
                  errors.scopeStatementISMS
                    ? "border-red-500/50 focus:border-red-500/50 focus:ring-red-500/50"
                    : "border-white/10 focus:border-purple-500/50 focus:ring-purple-500/50",
                )}
                placeholder="Enter the scope statement for your Information Security Management System (ISMS)..."
              />
              {errors.scopeStatementISMS && (
                <div className="flex items-center gap-2 text-red-400 text-xs">
                  <AlertCircle className="w-3 h-3" />
                  <span>{errors.scopeStatementISMS}</span>
                </div>
              )}
            </div>

            {/* File Upload */}
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
                    : errors.documents
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
                        {getFileIcon(file.name)}
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
                        onClick={() => handleRemoveFile(index)}
                        className="p-1 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {errors.documents && (
                <div className="flex items-center gap-2 text-red-400 text-xs">
                  <AlertCircle className="w-3 h-3" />
                  <span>{errors.documents}</span>
                </div>
              )}
            </div>

            {/* Footer Actions */}
            <div className="flex justify-end gap-3 pt-6 border-t border-white/5 mt-2">
              <button
                type="button"
                onClick={() => router.push(`/clients/${clientId}/projects`)}
                className="px-4 py-2 text-sm font-medium text-slate-400 hover:text-white transition-colors"
              >
                Cancel
              </button>
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
            </div>
          </form>
        </div>
      </div>

      {/* Loading Modal - centered in viewport via Dialog flex layout */}
      <Dialog open={showLoadingModal} onOpenChange={setShowLoadingModal}>
        <DialogContent hideCloseButton className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-center">
              Submitting Assessment
            </DialogTitle>
            <DialogDescription className="text-center">
              Please wait while we process your assessment...
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col items-center justify-center py-8">
            <Loader2 className="h-12 w-12 text-purple-400 animate-spin" />
          </div>
        </DialogContent>
      </Dialog>
    </DashboardLayout>
  );
}
