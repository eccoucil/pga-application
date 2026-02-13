"use client";

import { useEffect, useState, useRef, type FormEvent } from "react";
import { useParams, useRouter, useSearchParams, usePathname } from "next/navigation";
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
import type {
  AssessmentResponse,
  AssessmentRecord,
  AssessmentDetail,
} from "@/types/assessment";
import { AssessmentHistoryTable } from "@/components/assessment/AssessmentHistoryTable";
import { AssessmentFormCard } from "@/components/assessment/AssessmentFormCard";
import { FindingsContent } from "@/components/assessment/FindingsContent";
import { QuestionnaireContent } from "@/components/assessment/QuestionnaireContent";
import {
  Loader2,
  ArrowLeft,
  Calendar,
  Briefcase,
  FileCheck,
} from "lucide-react";

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

type ViewMode = "loading" | "table" | "view" | "edit" | "new";

export default function AssessmentPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const { user, loading: authLoading } = useAuth();
  const { selectedClient, setSelectedClient } = useClient();
  const { selectedProject, setSelectedProject } = useProject();
  const { toast } = useToast();
  const clientId = params.id as string;
  const projectId = params.projectId as string;
  const [loading, setLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showLoadingModal, setShowLoadingModal] = useState(false);

  // View mode state machine
  const [viewMode, setViewMode] = useState<ViewMode>("loading");
  const [assessments, setAssessments] = useState<AssessmentRecord[]>([]);
  const [selectedAssessmentId, setSelectedAssessmentId] = useState<
    string | null
  >(null);
  const [activeStep, setActiveStep] = useState<1 | 2 | 3>(1);
  const [findingsData, setFindingsData] = useState<AssessmentResponse | null>(
    null,
  );

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
  const [steps, setSteps] = useState<AssessmentStep[]>([
    { number: 1, title: "Scope", status: "current" },
    { number: 2, title: "Findings", status: "upcoming" },
    { number: 3, title: "Questionnaire", status: "upcoming" },
  ]);

  // ---------- URL sync ----------

  const urlAssessmentId = searchParams.get("assessment");
  const urlStep = searchParams.get("step");

  function updateUrl(assessmentId: string | null, step: number | null) {
    const params = new URLSearchParams();
    if (assessmentId) params.set("assessment", assessmentId);
    if (step) params.set("step", String(step));
    const query = params.toString();
    router.replace(`${pathname}${query ? `?${query}` : ""}`, { scroll: false });
  }

  // ---------- Data fetching ----------

  /** Try to hydrate form fields from the /findings endpoint (legacy Neo4j data). */
  const hydrateFromFindings = async (session: { access_token: string } | null) => {
    try {
      const apiUrl =
        process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
      const res = await fetch(
        `${apiUrl}/assessment/findings?client_id=${encodeURIComponent(clientId)}&project_id=${encodeURIComponent(projectId)}`,
        {
          headers: {
            ...(session?.access_token
              ? { Authorization: `Bearer ${session.access_token}` }
              : {}),
          },
        },
      );
      if (!res.ok) return;
      const data: AssessmentResponse = await res.json();
      const ctx = data.organization_context;
      const validIndustry = industryTypes.includes(ctx.industry_type)
        ? ctx.industry_type
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

  const fetchAssessments = async (): Promise<AssessmentRecord[]> => {
    try {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const apiUrl =
        process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
      const res = await fetch(
        `${apiUrl}/assessment/list?project_id=${encodeURIComponent(projectId)}&client_id=${encodeURIComponent(clientId)}`,
        {
          headers: {
            ...(session?.access_token
              ? { Authorization: `Bearer ${session.access_token}` }
              : {}),
          },
        },
      );
      if (!res.ok) {
        // List endpoint failed — try hydrating from findings (legacy data)
        const { data: { session: s } } = await supabase.auth.getSession();
        await hydrateFromFindings(s);
        setViewMode("new");
        return [];
      }
      const data = await res.json();
      const list: AssessmentRecord[] = data.assessments || [];
      setAssessments(list);
      if (list.length > 0) {
        setViewMode("table");
      } else {
        // No rows in assessments table — try hydrating from findings (legacy Neo4j data)
        await hydrateFromFindings(session);
        setViewMode("new");
      }
      return list;
    } catch {
      setViewMode("new");
      return [];
    }
  };

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

  // Fetch assessment list once loading finishes, then restore from URL params
  useEffect(() => {
    if (loading || authLoading || !user || !projectId || !clientId) return;
    const init = async () => {
      const list = await fetchAssessments();
      // Restore navigation state from URL if an assessment ID is present
      if (urlAssessmentId && list.some((a) => a.id === urlAssessmentId)) {
        const rawStep = Number(urlStep);
        const step: 1 | 2 | 3 = rawStep === 2 ? 2 : rawStep === 3 ? 3 : 1;
        await handleSelectAssessment(urlAssessmentId, step);
      }
    };
    init();
  }, [loading, authLoading, user, projectId, clientId]);

  // Persist serializable form fields to sessionStorage (debounced)
  useEffect(() => {
    if (!projectId || viewMode === "loading" || viewMode === "table") return;
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
    viewMode,
    formData.organizationName,
    formData.natureOfBusiness,
    formData.industryType,
    formData.webDomain,
    formData.department,
    formData.scopeStatementISMS,
  ]);

  // Update stepper based on view mode, active step, and findings data
  useEffect(() => {
    if (viewMode === "view") {
      if (activeStep === 3 && findingsData) {
        setSteps([
          { number: 1, title: "Scope", status: "completed" },
          { number: 2, title: "Findings", status: "completed" },
          { number: 3, title: "Questionnaire", status: "current" },
        ]);
      } else if (activeStep === 2 && findingsData) {
        setSteps([
          { number: 1, title: "Scope", status: "completed" },
          { number: 2, title: "Findings", status: "current" },
          { number: 3, title: "Questionnaire", status: "upcoming" },
        ]);
      } else {
        setSteps([
          { number: 1, title: "Scope", status: "current" },
          {
            number: 2,
            title: "Findings",
            status: findingsData ? "completed" : "upcoming",
          },
          { number: 3, title: "Questionnaire", status: "upcoming" },
        ]);
      }
    } else {
      setSteps([
        { number: 1, title: "Scope", status: "current" },
        { number: 2, title: "Findings", status: "upcoming" },
        { number: 3, title: "Questionnaire", status: "upcoming" },
      ]);
    }
  }, [viewMode, activeStep, findingsData]);

  // ---------- Handlers ----------

  const handleSelectAssessment = async (
    id: string,
    targetStep: 1 | 2 | 3 = 1,
  ) => {
    try {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const apiUrl =
        process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
      const res = await fetch(`${apiUrl}/assessment/detail/${id}`, {
        headers: {
          ...(session?.access_token
            ? { Authorization: `Bearer ${session.access_token}` }
            : {}),
        },
      });
      if (!res.ok) throw new Error("Failed to fetch assessment");
      const detail: AssessmentDetail = await res.json();
      setSelectedAssessmentId(id);
      setFormData({
        organizationName: detail.organization_name,
        natureOfBusiness: detail.nature_of_business,
        industryType: detail.industry_type,
        webDomain: detail.web_domain || "",
        department: detail.department,
        scopeStatementISMS: detail.scope_statement_isms,
        documents: [],
      });
      setErrors({});
      setViewMode("view");

      // Parse response_snapshot if available
      let hasFindings = false;
      if (detail.response_snapshot) {
        setFindingsData(
          detail.response_snapshot as unknown as AssessmentResponse,
        );
        hasFindings = true;
      } else {
        // Fallback: fetch from /assessment/findings endpoint
        try {
          const findingsRes = await fetch(
            `${apiUrl}/assessment/findings?client_id=${encodeURIComponent(clientId)}&project_id=${encodeURIComponent(projectId)}`,
            {
              headers: {
                ...(session?.access_token
                  ? { Authorization: `Bearer ${session.access_token}` }
                  : {}),
              },
            },
          );
          if (findingsRes.ok) {
            const findingsJson: AssessmentResponse =
              await findingsRes.json();
            setFindingsData(findingsJson);
            hasFindings = true;
          } else {
            setFindingsData(null);
          }
        } catch {
          setFindingsData(null);
        }
      }

      // Fall back to step 1 if requesting findings/questionnaire but no data
      const resolvedStep = (targetStep > 1 && !hasFindings) ? 1 : targetStep;
      setActiveStep(resolvedStep);
      updateUrl(id, resolvedStep);
    } catch {
      toast({
        title: "Error",
        description: "Failed to load assessment details.",
        variant: "destructive",
      });
    }
  };

  const handleNewAssessment = async () => {
    // Auto-fill from latest assessment if one exists
    if (assessments.length > 0) {
      try {
        const {
          data: { session },
        } = await supabase.auth.getSession();
        const apiUrl =
          process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
        const res = await fetch(
          `${apiUrl}/assessment/detail/${assessments[0].id}`,
          {
            headers: {
              ...(session?.access_token
                ? { Authorization: `Bearer ${session.access_token}` }
                : {}),
            },
          },
        );
        if (res.ok) {
          const detail: AssessmentDetail = await res.json();
          setFormData({
            organizationName: detail.organization_name,
            natureOfBusiness: detail.nature_of_business,
            industryType: detail.industry_type,
            webDomain: detail.web_domain || "",
            department: detail.department,
            scopeStatementISMS: detail.scope_statement_isms,
            documents: [],
          });
          setErrors({});
          setSelectedAssessmentId(null);
          setViewMode("new");
          updateUrl(null, null);
          return;
        }
      } catch {
        /* fall through */
      }
    }
    // Fall back to client name
    setFormData({
      organizationName: selectedClient?.name || "",
      natureOfBusiness: "",
      industryType: "",
      webDomain: "",
      department: "",
      scopeStatementISMS: "",
      documents: [],
    });
    setErrors({});
    setSelectedAssessmentId(null);
    setViewMode("new");
    updateUrl(null, null);
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

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
          errorData.detail ||
            `Failed to submit assessment: ${response.status}`,
        );
      }

      await response.json();

      setShowLoadingModal(false);

      toast({
        title: "Success",
        description: "Assessment form submitted successfully.",
      });

      // Refetch list and go to table view
      await fetchAssessments();
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

  // ---------- Early returns ----------

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

  // ---------- Helpers ----------

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

  // ---------- Render ----------

  return (
    <DashboardLayout>
      <div
        className={`${
          viewMode === "view" && (activeStep === 2 || activeStep === 3)
            ? "max-w-6xl"
            : "max-w-4xl"
        } mx-auto pb-10 transition-all duration-300`}
      >
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
                        {selectedProject.framework.map(
                          (fw: string, idx: number) => (
                            <span
                              key={idx}
                              className="px-2 py-1 bg-purple-500/10 text-purple-300 text-xs rounded border border-purple-500/20"
                            >
                              {fw}
                            </span>
                          ),
                        )}
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

        {/* View mode: loading */}
        {viewMode === "loading" && (
          <div className="flex justify-center items-center min-h-[200px]">
            <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
          </div>
        )}

        {/* View mode: table */}
        {viewMode === "table" && (
          <AssessmentHistoryTable
            assessments={assessments}
            onSelect={handleSelectAssessment}
            onNew={handleNewAssessment}
            onViewFindings={(id) => handleSelectAssessment(id, 2)}
          />
        )}

        {/* View mode: view / edit / new */}
        {(viewMode === "view" ||
          viewMode === "edit" ||
          viewMode === "new") && (
          <>
            {/* Stepper */}
            <AssessmentStepper
              steps={steps}
              onStepClick={(stepNumber) => {
                if (viewMode === "view") {
                  if (stepNumber === 1) {
                    setActiveStep(1);
                    updateUrl(selectedAssessmentId, 1);
                  }
                  if (stepNumber === 2 && findingsData) {
                    setActiveStep(2);
                    updateUrl(selectedAssessmentId, 2);
                  }
                  if (stepNumber === 3 && findingsData) {
                    setActiveStep(3);
                    updateUrl(selectedAssessmentId, 3);
                  }
                }
              }}
            />

            {/* Step 1: Scope Form (shown when activeStep === 1 or when editing/new) */}
            {(viewMode !== "view" || activeStep === 1) && (
              <AssessmentFormCard
                formData={formData}
                formErrors={errors}
                readOnly={viewMode === "view"}
                onFieldChange={(name, value) => {
                  setFormData((prev) => ({ ...prev, [name]: value }));
                  if (errors[name as keyof typeof errors]) {
                    setErrors((prev) => ({ ...prev, [name]: undefined }));
                  }
                }}
                onDocumentsChange={(files) => {
                  setFormData((prev) => ({
                    ...prev,
                    documents: [...prev.documents, ...files],
                  }));
                }}
                onRemoveDocument={(index) => {
                  setFormData((prev) => ({
                    ...prev,
                    documents: prev.documents.filter((_, i) => i !== index),
                  }));
                }}
                onSubmit={handleSubmit}
                onCancel={() => {
                  if (assessments.length > 0) {
                    setSelectedAssessmentId(null);
                    setViewMode("table");
                    updateUrl(null, null);
                  } else {
                    router.push(`/clients/${clientId}/projects`);
                  }
                }}
                onEdit={() => setViewMode("edit")}
                isSubmitting={isSubmitting}
                onProceedToFindings={
                  findingsData ? () => { setActiveStep(2); updateUrl(selectedAssessmentId, 2); } : undefined
                }
              />
            )}

            {/* Step 2: Findings (shown when activeStep === 2 in view mode) */}
            {viewMode === "view" && activeStep === 2 && findingsData && (
              <FindingsContent
                data={findingsData}
                onProceedToQuestionnaire={() => { setActiveStep(3); updateUrl(selectedAssessmentId, 3); }}
              />
            )}

            {/* Step 3: Questionnaire (shown when activeStep === 3 in view mode) */}
            {viewMode === "view" && activeStep === 3 && findingsData && (
              <QuestionnaireContent projectId={projectId} frameworks={selectedProject?.framework ?? []} assessmentId={selectedAssessmentId ?? undefined} />
            )}
          </>
        )}
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
