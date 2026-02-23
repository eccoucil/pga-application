"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import {
  Loader2,
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
  ChevronDown,
  ChevronUp,
  ArrowRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { AssessmentResponse } from "@/types/assessment";

const ContextNodesGraph = dynamic(
  () =>
    import("@/components/knowledge-graph/ContextNodesGraph").then(
      (mod) => mod.ContextNodesGraph,
    ),
  {
    ssr: false,
    loading: () => (
      <div className="h-[500px] flex items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
      </div>
    ),
  },
);

interface FindingsContentProps {
  data: AssessmentResponse;
  onProceedToQuestionnaire?: () => void;
}

function getDocumentStatusIcon(status: string) {
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
}

function getDocumentStatusColor(status: string) {
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
}

export function FindingsContent({ data, onProceedToQuestionnaire }: FindingsContentProps) {
  const [graphExpanded, setGraphExpanded] = useState(false);

  return (
    <>
      {/* Summary Card */}
      <div className="bg-[#0f1016]/60 backdrop-blur-md border border-white/10 rounded-2xl p-6 mb-6">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-purple-500/10 rounded-lg">
            <CheckCircle2 className="h-6 w-6 text-purple-400" />
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-white mb-2">
              {data.summary.headline}
            </h3>
            <p className="text-sm text-slate-400 mb-4">
              Processed in{" "}
              {(data.summary.processing_time_ms / 1000).toFixed(2)} seconds
            </p>
            <div className="flex flex-wrap gap-2">
              {data.summary.highlights.map((highlight, index) => (
                <span
                  key={index}
                  className="px-3 py-1 bg-purple-500/10 text-purple-300 text-xs rounded-full border border-purple-500/20"
                >
                  {highlight}
                </span>
              ))}
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
              {data.organization_context.organization_name}
            </p>
          </div>
          <div>
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">
              Industry
            </p>
            <p className="text-white">
              {data.organization_context.industry_type}
            </p>
            {data.organization_context.industry_sector && (
              <p className="text-xs text-slate-500 mt-1">
                Sector: {data.organization_context.industry_sector}
              </p>
            )}
          </div>
          <div>
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">
              Department
            </p>
            <p className="text-white">
              {data.organization_context.department}
            </p>
          </div>
          {data.organization_context.web_domain && (
            <div>
              <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">
                Web Domain
              </p>
              <div className="flex items-center gap-2">
                <Globe className="h-4 w-4 text-slate-400" />
                <p className="text-white">
                  {data.organization_context.web_domain}
                </p>
              </div>
            </div>
          )}
          <div className="md:col-span-2">
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">
              Scope Statement
            </p>
            <p className="text-slate-300 text-sm">
              {data.organization_context.scope_statement_preview}
            </p>
          </div>
        </div>
      </div>

      {/* Knowledge Graph (collapsible) */}
      {data.knowledge_graph && data.knowledge_graph.nodes.length > 0 && (
        <div className="bg-[#0f1016]/60 backdrop-blur-md border border-white/10 rounded-2xl mb-6 overflow-hidden">
          <button
            onClick={() => setGraphExpanded((prev) => !prev)}
            className="w-full flex items-center justify-between p-6 hover:bg-white/5 transition-colors"
          >
            <div className="flex items-center gap-3">
              <Network className="w-5 h-5 text-purple-400" />
              <h3 className="text-lg font-semibold text-white">
                Knowledge Graph
              </h3>
              <span className="px-2 py-0.5 bg-purple-500/10 text-purple-300 text-xs rounded-full border border-purple-500/20">
                {data.knowledge_graph.nodes.length} nodes
              </span>
            </div>
            {graphExpanded ? (
              <ChevronUp className="w-5 h-5 text-slate-400" />
            ) : (
              <ChevronDown className="w-5 h-5 text-slate-400" />
            )}
          </button>
          {graphExpanded && (
            <div className="h-[500px] border-t border-white/10">
              <ContextNodesGraph knowledgeGraph={data.knowledge_graph} />
            </div>
          )}
        </div>
      )}

      {/* Documents Section */}
      <div className="bg-[#0f1016]/60 backdrop-blur-md border border-white/10 rounded-2xl p-6 mb-6">
        <div className="flex items-center gap-3 mb-4">
          <FileText className="w-5 h-5 text-purple-400" />
          <h3 className="text-lg font-semibold text-white">
            Documents ({data.documents_received})
          </h3>
        </div>
        <div className="space-y-3">
          {data.documents.map((doc) => (
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
      {data.web_crawl && (
        <div className="bg-[#0f1016]/60 backdrop-blur-md border border-white/10 rounded-2xl p-6 mb-6">
          <div className="flex items-center gap-3 mb-4">
            <Network className="w-5 h-5 text-purple-400" />
            <h3 className="text-lg font-semibold text-white">
              Web Crawl Results
            </h3>
          </div>

          {/* Error banner -- only when crawl failed */}
          {!data.web_crawl.success && data.web_crawl.errors.length > 0 && (
            <div className="mb-4 p-4 bg-red-500/10 rounded-lg border border-red-500/20">
              <p className="text-xs font-medium text-red-400 uppercase tracking-wider mb-2">
                Crawl Errors
              </p>
              <ul className="space-y-1">
                {data.web_crawl.errors.map((error, index) => (
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

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 bg-black/40 rounded-lg border border-white/10">
              <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">
                Pages Crawled
              </p>
              <p className="text-2xl font-bold text-white">
                {data.web_crawl.pages_crawled}
              </p>
            </div>
            <div className="p-4 bg-black/40 rounded-lg border border-white/10">
              <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">
                Digital Assets
              </p>
              <p className="text-2xl font-bold text-white">
                {data.web_crawl.digital_assets_found}
              </p>
            </div>
            <div className="p-4 bg-black/40 rounded-lg border border-white/10">
              <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">
                Confidence Score
              </p>
              <p className="text-2xl font-bold text-white">
                {(data.web_crawl.confidence_score * 100).toFixed(0)}%
              </p>
            </div>
          </div>

          {/* Business Context Extraction */}
          {data.web_crawl.business_context && (
            <div className="mt-6 p-4 bg-black/40 rounded-lg border border-white/10">
              <div className="flex items-center gap-2 mb-4">
                <Briefcase className="h-4 w-4 text-purple-400" />
                <p className="text-sm font-semibold text-white">
                  Business Context
                </p>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {data.web_crawl.business_context.company_name != null && (
                  <div>
                    <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">
                      Company Name
                    </p>
                    <p className="text-white text-sm">
                      {String(data.web_crawl.business_context.company_name)}
                    </p>
                  </div>
                )}
                {data.web_crawl.business_context.industry != null && (
                  <div>
                    <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">
                      Industry
                    </p>
                    <p className="text-white text-sm">
                      {String(data.web_crawl.business_context.industry)}
                    </p>
                  </div>
                )}
                {data.web_crawl.business_context.description != null && (
                  <div className="md:col-span-2">
                    <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">
                      Description
                    </p>
                    <p className="text-slate-300 text-sm">
                      {String(data.web_crawl.business_context.description)}
                    </p>
                  </div>
                )}
                {data.web_crawl.business_context.mission_statement != null && (
                  <div className="md:col-span-2">
                    <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">
                      Mission Statement
                    </p>
                    <p className="text-slate-300 text-sm">
                      {String(
                        data.web_crawl.business_context.mission_statement,
                      )}
                    </p>
                  </div>
                )}
                {data.web_crawl.business_context.target_audience != null && (
                  <div className="md:col-span-2">
                    <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">
                      Target Audience
                    </p>
                    <p className="text-slate-300 text-sm">
                      {String(data.web_crawl.business_context.target_audience)}
                    </p>
                  </div>
                )}
                {Array.isArray(
                  data.web_crawl.business_context.key_services,
                ) &&
                  (
                    data.web_crawl.business_context.key_services as unknown[]
                  ).length > 0 && (
                    <div className="md:col-span-2">
                      <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">
                        Key Services
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {(
                          data.web_crawl.business_context
                            .key_services as unknown[]
                        ).map((service, index) => (
                          <span
                            key={index}
                            className="px-2.5 py-1 bg-purple-500/10 text-purple-300 text-xs rounded-full border border-purple-500/20"
                          >
                            {String(service)}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
              </div>
            </div>
          )}

          {/* Digital Assets Extraction */}
          {data.web_crawl.digital_assets &&
            data.web_crawl.digital_assets.length > 0 && (
              <div className="mt-6 p-4 bg-black/40 rounded-lg border border-white/10">
                <div className="flex items-center gap-2 mb-4">
                  <Database className="h-4 w-4 text-purple-400" />
                  <p className="text-sm font-semibold text-white">
                    Digital Assets ({data.web_crawl.digital_assets.length})
                  </p>
                </div>
                <div className="space-y-3">
                  {data.web_crawl.digital_assets.map((asset, index) => (
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
                        {asset.url != null && /^https?:\/\//i.test(String(asset.url)) ? (
                          <a
                            href={String(asset.url)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm text-purple-400 hover:text-purple-300 underline underline-offset-2 truncate max-w-md"
                          >
                            {String(asset.url)}
                          </a>
                        ) : asset.url != null ? (
                          <span className="text-sm text-slate-400 truncate max-w-md">
                            {String(asset.url)}
                          </span>
                        ) : null}
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
          {data.web_crawl.organization_info && (
            <div className="mt-6 p-4 bg-black/40 rounded-lg border border-white/10">
              <div className="flex items-center gap-2 mb-4">
                <Building2 className="h-4 w-4 text-purple-400" />
                <p className="text-sm font-semibold text-white">
                  Organization Info
                </p>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {data.web_crawl.organization_info.headquarters != null && (
                  <div>
                    <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">
                      Headquarters
                    </p>
                    <p className="text-white text-sm">
                      {String(
                        data.web_crawl.organization_info.headquarters,
                      )}
                    </p>
                  </div>
                )}
                {data.web_crawl.organization_info.contact_email != null && (
                  <div>
                    <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">
                      Contact Email
                    </p>
                    <p className="text-white text-sm">
                      {String(
                        data.web_crawl.organization_info.contact_email,
                      )}
                    </p>
                  </div>
                )}
                {Array.isArray(
                  data.web_crawl.organization_info.certifications,
                ) &&
                  (
                    data.web_crawl.organization_info
                      .certifications as unknown[]
                  ).length > 0 && (
                    <div className="md:col-span-2">
                      <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">
                        Certifications
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {(
                          data.web_crawl.organization_info
                            .certifications as unknown[]
                        ).map((cert, index) => (
                          <span
                            key={index}
                            className="px-2.5 py-1 bg-emerald-500/10 text-emerald-300 text-xs rounded-full border border-emerald-500/20"
                          >
                            {String(cert)}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                {Array.isArray(
                  data.web_crawl.organization_info.partnerships,
                ) &&
                  (
                    data.web_crawl.organization_info
                      .partnerships as unknown[]
                  ).length > 0 && (
                    <div className="md:col-span-2">
                      <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">
                        Partnerships
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {(
                          data.web_crawl.organization_info
                            .partnerships as unknown[]
                        ).map((partner, index) => (
                          <span
                            key={index}
                            className="px-2.5 py-1 bg-blue-500/10 text-blue-300 text-xs rounded-full border border-blue-500/20"
                          >
                            {String(partner)}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
              </div>
            </div>
          )}
        </div>
      )}

      {onProceedToQuestionnaire && (
        <div className="flex justify-end pt-6">
          <button
            type="button"
            onClick={onProceedToQuestionnaire}
            className="flex items-center gap-2 px-6 py-2.5 text-sm font-medium bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white rounded-lg shadow-lg shadow-purple-900/20 transition-all"
          >
            Proceed to Questionnaire
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </>
  );
}
