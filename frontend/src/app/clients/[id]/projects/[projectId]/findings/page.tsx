"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { useClient } from "@/contexts/ClientContext";
import { useProject } from "@/contexts/ProjectContext";
import { useAuth } from "@/contexts/AuthContext";
import { getClient, getProject, supabase } from "@/lib/supabase";
import {
  AssessmentStepper,
  type AssessmentStep,
} from "@/components/ui/assessment-stepper";
import type { AssessmentResponse } from "@/types/assessment";
import {
  Loader2,
  ArrowLeft,
  ArrowRight,
  FileText,
  CheckCircle2,
  Clock,
  AlertCircle,
  Globe,
  Building2,
  Briefcase,
  CheckCircle,
  XCircle,
  Info,
  Database,
  Network,
} from "lucide-react";
import { cn } from "@/lib/utils";

export default function FindingsPage() {
  const params = useParams();
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const { selectedClient, setSelectedClient } = useClient();
  const { selectedProject, setSelectedProject } = useProject();
  const clientId = params.id as string;
  const projectId = params.projectId as string;
  const [loading, setLoading] = useState(true);
  const [assessmentData, setAssessmentData] =
    useState<AssessmentResponse | null>(null);
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

          // Fetch findings from API (real assessment response for this project)
          if (typeof window !== "undefined" && clientId && projectId) {
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
              if (res.ok) {
                const data: AssessmentResponse = await res.json();
                setAssessmentData(data);
              } else {
                // No assessment context (404) — load sample data
                const sampleRes = await fetch(
                  `${window.location.origin}/data/sample-assessment-response.json`,
                  { headers: { "Content-Type": "application/json" } },
                );
                if (sampleRes.ok) {
                  const sample: AssessmentResponse = await sampleRes.json();
                  setAssessmentData(sample);
                }
              }
            } catch {
              // Fallback: load sample only
              try {
                const sampleRes = await fetch(
                  `${window.location.origin}/data/sample-assessment-response.json`,
                  { headers: { "Content-Type": "application/json" } },
                );
                if (sampleRes.ok) {
                  const sample: AssessmentResponse = await sampleRes.json();
                  setAssessmentData(sample);
                }
              } catch {
                // Continue without data
              }
            }
          }
        } catch (error) {
          console.error("Error loading assessment data:", error);
        } finally {
          setLoading(false);
        }
      }
    };

    fetchData();
  }, [
    clientId,
    projectId,
    selectedClient,
    selectedProject,
    authLoading,
    user,
    setSelectedClient,
    setSelectedProject,
    router,
  ]);

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

  const steps: AssessmentStep[] = [
    { number: 1, title: "Scope", status: "completed" },
    { number: 2, title: "Findings", status: "current" },
    { number: 3, title: "Questionnaire", status: "upcoming" },
  ];

  const getDocumentStatusIcon = (status: string) => {
    switch (status) {
      case "processed":
        return <CheckCircle className="h-5 w-5 text-emerald-400" />;
      case "processing":
        return <Loader2 className="h-5 w-5 text-blue-400 animate-spin" />;
      case "pending":
        return <Clock className="h-5 w-5 text-amber-400" />;
      case "failed":
        return <XCircle className="h-5 w-5 text-red-400" />;
      default:
        return <Info className="h-5 w-5 text-slate-400" />;
    }
  };

  const getDocumentStatusColor = (status: string) => {
    switch (status) {
      case "processed":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
      case "processing":
        return "bg-blue-500/10 text-blue-400 border-blue-500/20";
      case "pending":
        return "bg-amber-500/10 text-amber-400 border-amber-500/20";
      case "failed":
        return "bg-red-500/10 text-red-400 border-red-500/20";
      default:
        return "bg-slate-500/10 text-slate-400 border-slate-500/20";
    }
  };

  return (
    <DashboardLayout>
      <div className="max-w-6xl mx-auto pb-10">
        {/* Back Button */}
        <button
          onClick={() =>
            router.push(`/clients/${clientId}/projects/${projectId}/assessment`)
          }
          className="mb-6 flex items-center gap-2 px-4 py-2.5 bg-[#0f1016]/80 backdrop-blur-md border border-white/10 rounded-lg text-slate-300 hover:text-white hover:bg-white/10 transition-all shadow-lg hover:shadow-xl hover:border-purple-500/30 group w-fit"
          title="Back to Assessment"
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
                  <p className="text-slate-400 text-sm ml-8">
                    {selectedProject.description}
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Divider */}
        <div className="h-px bg-gradient-to-r from-transparent via-white/10 to-transparent mb-8"></div>

        {/* Stepper */}
        <AssessmentStepper steps={steps} />

        {/* Assessment Summary Card */}
        {assessmentData && (
          <>
            {/* Summary Card */}
            <div className="bg-[#0f1016]/60 backdrop-blur-md border border-white/10 rounded-2xl p-6 mb-6">
              <div className="flex items-start gap-4">
                <div className="p-3 bg-purple-500/10 rounded-lg">
                  <CheckCircle2 className="h-6 w-6 text-purple-400" />
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-white mb-2">
                    {assessmentData.summary.headline}
                  </h3>
                  <p className="text-sm text-slate-400 mb-4">
                    Processed in{" "}
                    {(assessmentData.summary.processing_time_ms / 1000).toFixed(
                      2,
                    )}{" "}
                    seconds
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {assessmentData.summary.highlights.map(
                      (highlight, index) => (
                        <span
                          key={index}
                          className="px-3 py-1 bg-purple-500/10 text-purple-300 text-xs rounded-full border border-purple-500/20"
                        >
                          {highlight}
                        </span>
                      ),
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Organization Context */}
            <div className="bg-[#0f1016]/60 backdrop-blur-md border border-white/10 rounded-2xl p-6 mb-6">
              <div className="flex items-center gap-3 mb-4">
                <Building2 className="w-5 h-5 text-purple-400" />
                <h3 className="text-lg font-semibold text-white">
                  Organization Context
                </h3>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">
                    Organization
                  </p>
                  <p className="text-white">
                    {assessmentData.organization_context.organization_name}
                  </p>
                  {assessmentData.organization_context.organization_id && (
                    <p className="text-xs text-slate-500 mt-1">
                      ID: {assessmentData.organization_context.organization_id}
                    </p>
                  )}
                </div>
                <div>
                  <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">
                    Industry
                  </p>
                  <p className="text-white">
                    {assessmentData.organization_context.industry_type}
                  </p>
                  {assessmentData.organization_context.industry_sector && (
                    <p className="text-xs text-slate-500 mt-1">
                      Sector:{" "}
                      {assessmentData.organization_context.industry_sector}
                    </p>
                  )}
                </div>
                <div>
                  <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">
                    Department
                  </p>
                  <p className="text-white">
                    {assessmentData.organization_context.department}
                  </p>
                </div>
                {assessmentData.organization_context.web_domain && (
                  <div>
                    <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">
                      Web Domain
                    </p>
                    <div className="flex items-center gap-2">
                      <Globe className="h-4 w-4 text-slate-400" />
                      <p className="text-white">
                        {assessmentData.organization_context.web_domain}
                      </p>
                    </div>
                  </div>
                )}
                <div className="md:col-span-2">
                  <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">
                    Scope Statement
                  </p>
                  <p className="text-slate-300 text-sm">
                    {
                      assessmentData.organization_context
                        .scope_statement_preview
                    }
                  </p>
                </div>
                {assessmentData.organization_context.context_nodes_created &&
                  assessmentData.organization_context.context_nodes_created
                    .length > 0 && (
                    <div className="md:col-span-2">
                      <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">
                        Nodes Created Summary
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {assessmentData.organization_context.context_nodes_created.map(
                          (node, index) => (
                            <span
                              key={index}
                              className="px-2 py-1 bg-emerald-500/10 text-emerald-300 text-xs rounded-full border border-emerald-500/20"
                            >
                              {node}
                            </span>
                          ),
                        )}
                      </div>
                    </div>
                  )}
              </div>
            </div>

            {/* Documents Section */}
            <div className="bg-[#0f1016]/60 backdrop-blur-md border border-white/10 rounded-2xl p-6 mb-6">
              <div className="flex items-center gap-3 mb-4">
                <FileText className="w-5 h-5 text-purple-400" />
                <h3 className="text-lg font-semibold text-white">
                  Documents ({assessmentData.documents_received})
                </h3>
              </div>
              <div className="space-y-3">
                {assessmentData.documents.map((doc) => (
                  <div
                    key={doc.document_id}
                    className={cn(
                      "p-4 rounded-lg border flex items-start justify-between",
                      getDocumentStatusColor(doc.status),
                    )}
                  >
                    <div className="flex items-start gap-3 flex-1">
                      {getDocumentStatusIcon(doc.status)}
                      <div className="flex-1">
                        <p className="text-sm font-medium text-white mb-1">
                          {doc.filename}
                        </p>
                        <div className="flex items-center gap-4 text-xs text-slate-400">
                          <span>Status: {doc.status}</span>
                          {doc.extracted_text_length > 0 && (
                            <span>
                              {doc.extracted_text_length.toLocaleString()} chars
                              extracted
                            </span>
                          )}
                          {doc.findings_count > 0 && (
                            <span>{doc.findings_count} finding(s)</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Web Crawl Section */}
            {assessmentData.web_crawl && (
              <div className="bg-[#0f1016]/60 backdrop-blur-md border border-white/10 rounded-2xl p-6 mb-6">
                <div className="flex items-center gap-3 mb-4">
                  <Network className="w-5 h-5 text-purple-400" />
                  <h3 className="text-lg font-semibold text-white">
                    Web Crawl Results
                  </h3>
                  {assessmentData.web_crawl.from_cache && (
                    <span className="px-2 py-1 bg-amber-500/10 text-amber-300 text-xs rounded border border-amber-500/20">
                      From Cache
                    </span>
                  )}
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-4 bg-black/40 rounded-lg border border-white/10">
                    <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">
                      Pages Crawled
                    </p>
                    <p className="text-2xl font-bold text-white">
                      {assessmentData.web_crawl.pages_crawled}
                    </p>
                  </div>
                  <div className="p-4 bg-black/40 rounded-lg border border-white/10">
                    <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">
                      Digital Assets
                    </p>
                    <p className="text-2xl font-bold text-white">
                      {assessmentData.web_crawl.digital_assets_found}
                    </p>
                  </div>
                  <div className="p-4 bg-black/40 rounded-lg border border-white/10">
                    <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">
                      Confidence Score
                    </p>
                    <p className="text-2xl font-bold text-white">
                      {(
                        assessmentData.web_crawl.confidence_score * 100
                      ).toFixed(0)}
                      %
                    </p>
                  </div>
                  <div className="p-4 bg-black/40 rounded-lg border border-white/10">
                    <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">
                      Status
                    </p>
                    <div className="flex items-center gap-2">
                      {assessmentData.web_crawl.success ? (
                        <CheckCircle className="h-5 w-5 text-emerald-400" />
                      ) : (
                        <XCircle className="h-5 w-5 text-red-400" />
                      )}
                      <p className="text-white font-medium">
                        {assessmentData.web_crawl.success
                          ? "Success"
                          : "Failed"}
                      </p>
                    </div>
                  </div>
                  {assessmentData.web_crawl.business_context_extracted && (
                    <div className="p-4 bg-emerald-500/10 rounded-lg border border-emerald-500/20">
                      <div className="flex items-center gap-2 mb-1">
                        <CheckCircle className="h-4 w-4 text-emerald-400" />
                        <p className="text-sm font-medium text-emerald-300">
                          Business Context Extracted
                        </p>
                      </div>
                    </div>
                  )}
                  {assessmentData.web_crawl.organization_info_extracted && (
                    <div className="p-4 bg-emerald-500/10 rounded-lg border border-emerald-500/20">
                      <div className="flex items-center gap-2 mb-1">
                        <CheckCircle className="h-4 w-4 text-emerald-400" />
                        <p className="text-sm font-medium text-emerald-300">
                          Organization Info Extracted
                        </p>
                      </div>
                    </div>
                  )}
                  {assessmentData.web_crawl.errors.length > 0 && (
                    <div className="md:col-span-2 p-4 bg-red-500/10 rounded-lg border border-red-500/20">
                      <p className="text-xs font-medium text-red-400 uppercase tracking-wider mb-2">
                        Errors
                      </p>
                      <ul className="space-y-1">
                        {assessmentData.web_crawl.errors.map((error, index) => (
                          <li
                            key={index}
                            className="text-sm text-red-300 flex items-start gap-2"
                          >
                            <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                            <span>{error}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>

                {/* Business Context Extraction */}
                {assessmentData.web_crawl.business_context && (
                  <div className="mt-6 p-4 bg-black/40 rounded-lg border border-white/10">
                    <div className="flex items-center gap-2 mb-4">
                      <Briefcase className="h-4 w-4 text-purple-400" />
                      <p className="text-sm font-semibold text-white">
                        Business Context
                      </p>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {assessmentData.web_crawl.business_context.company_name != null && (
                        <div>
                          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">
                            Company Name
                          </p>
                          <p className="text-white text-sm">
                            {String(assessmentData.web_crawl.business_context.company_name)}
                          </p>
                        </div>
                      )}
                      {assessmentData.web_crawl.business_context.industry != null && (
                        <div>
                          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">
                            Industry
                          </p>
                          <p className="text-white text-sm">
                            {String(assessmentData.web_crawl.business_context.industry)}
                          </p>
                        </div>
                      )}
                      {assessmentData.web_crawl.business_context.description != null && (
                        <div className="md:col-span-2">
                          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">
                            Description
                          </p>
                          <p className="text-slate-300 text-sm">
                            {String(assessmentData.web_crawl.business_context.description)}
                          </p>
                        </div>
                      )}
                      {assessmentData.web_crawl.business_context.mission_statement != null && (
                        <div className="md:col-span-2">
                          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">
                            Mission Statement
                          </p>
                          <p className="text-slate-300 text-sm">
                            {String(assessmentData.web_crawl.business_context.mission_statement)}
                          </p>
                        </div>
                      )}
                      {assessmentData.web_crawl.business_context.target_audience != null && (
                        <div className="md:col-span-2">
                          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">
                            Target Audience
                          </p>
                          <p className="text-slate-300 text-sm">
                            {String(assessmentData.web_crawl.business_context.target_audience)}
                          </p>
                        </div>
                      )}
                      {Array.isArray(assessmentData.web_crawl.business_context.key_services) &&
                        (assessmentData.web_crawl.business_context.key_services as unknown[]).length > 0 && (
                        <div className="md:col-span-2">
                          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">
                            Key Services
                          </p>
                          <div className="flex flex-wrap gap-2">
                            {(assessmentData.web_crawl.business_context.key_services as unknown[]).map(
                              (service, index) => (
                                <span
                                  key={index}
                                  className="px-2.5 py-1 bg-purple-500/10 text-purple-300 text-xs rounded-full border border-purple-500/20"
                                >
                                  {String(service)}
                                </span>
                              ),
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Digital Assets Extraction */}
                {assessmentData.web_crawl.digital_assets &&
                  assessmentData.web_crawl.digital_assets.length > 0 && (
                  <div className="mt-6 p-4 bg-black/40 rounded-lg border border-white/10">
                    <div className="flex items-center gap-2 mb-4">
                      <Database className="h-4 w-4 text-purple-400" />
                      <p className="text-sm font-semibold text-white">
                        Digital Assets ({assessmentData.web_crawl.digital_assets.length})
                      </p>
                    </div>
                    <div className="space-y-3">
                      {assessmentData.web_crawl.digital_assets.map((asset, index) => (
                        <div
                          key={index}
                          className="p-3 bg-black/30 rounded-lg border border-white/5 flex flex-col gap-2"
                        >
                          <div className="flex items-center gap-2 flex-wrap">
                            {asset.asset_type != null && (
                              <span className="px-2 py-0.5 bg-slate-500/20 text-slate-300 text-xs rounded border border-slate-500/20 uppercase tracking-wider font-medium">
                                {String(asset.asset_type)}
                              </span>
                            )}
                            {asset.url != null && (
                              <a
                                href={String(asset.url)}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-sm text-purple-400 hover:text-purple-300 underline underline-offset-2 truncate max-w-md"
                              >
                                {String(asset.url)}
                              </a>
                            )}
                            {asset.name != null && asset.url == null && (
                              <span className="text-sm text-white">
                                {String(asset.name)}
                              </span>
                            )}
                          </div>
                          {asset.description != null && (
                            <p className="text-xs text-slate-400">
                              {String(asset.description)}
                            </p>
                          )}
                          {asset.purpose != null && (
                            <p className="text-xs text-slate-500">
                              Purpose: {String(asset.purpose)}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Organization Info Extraction */}
                {assessmentData.web_crawl.organization_info && (
                  <div className="mt-6 p-4 bg-black/40 rounded-lg border border-white/10">
                    <div className="flex items-center gap-2 mb-4">
                      <Building2 className="h-4 w-4 text-purple-400" />
                      <p className="text-sm font-semibold text-white">
                        Organization Info
                      </p>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {assessmentData.web_crawl.organization_info.headquarters != null && (
                        <div>
                          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">
                            Headquarters
                          </p>
                          <p className="text-white text-sm">
                            {String(assessmentData.web_crawl.organization_info.headquarters)}
                          </p>
                        </div>
                      )}
                      {assessmentData.web_crawl.organization_info.contact_email != null && (
                        <div>
                          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">
                            Contact Email
                          </p>
                          <p className="text-white text-sm">
                            {String(assessmentData.web_crawl.organization_info.contact_email)}
                          </p>
                        </div>
                      )}
                      {Array.isArray(assessmentData.web_crawl.organization_info.certifications) &&
                        (assessmentData.web_crawl.organization_info.certifications as unknown[]).length > 0 && (
                        <div className="md:col-span-2">
                          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">
                            Certifications
                          </p>
                          <div className="flex flex-wrap gap-2">
                            {(assessmentData.web_crawl.organization_info.certifications as unknown[]).map(
                              (cert, index) => (
                                <span
                                  key={index}
                                  className="px-2.5 py-1 bg-emerald-500/10 text-emerald-300 text-xs rounded-full border border-emerald-500/20"
                                >
                                  {String(cert)}
                                </span>
                              ),
                            )}
                          </div>
                        </div>
                      )}
                      {Array.isArray(assessmentData.web_crawl.organization_info.partnerships) &&
                        (assessmentData.web_crawl.organization_info.partnerships as unknown[]).length > 0 && (
                        <div className="md:col-span-2">
                          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">
                            Partnerships
                          </p>
                          <div className="flex flex-wrap gap-2">
                            {(assessmentData.web_crawl.organization_info.partnerships as unknown[]).map(
                              (partner, index) => (
                                <span
                                  key={index}
                                  className="px-2.5 py-1 bg-blue-500/10 text-blue-300 text-xs rounded-full border border-blue-500/20"
                                >
                                  {String(partner)}
                                </span>
                              ),
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Proceed to Questionnaire */}
            <div className="flex justify-end mt-6">
              <button
                onClick={() =>
                  router.push(
                    `/clients/${clientId}/projects/${projectId}/questionnaires`,
                  )
                }
                className="px-6 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white rounded-lg shadow-lg shadow-purple-900/20 transition-all font-medium flex items-center gap-2"
              >
                Proceed to Questionnaire
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </>
        )}

        {!assessmentData && !loading && (
          <div className="bg-[#0f1016]/60 backdrop-blur-md border border-white/10 rounded-2xl p-12 text-center">
            <AlertCircle className="h-12 w-12 text-slate-400 mx-auto mb-4" />
            <p className="text-slate-400">No assessment data available</p>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
