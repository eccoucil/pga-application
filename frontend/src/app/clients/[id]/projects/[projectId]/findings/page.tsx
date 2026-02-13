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
import { FindingsContent } from "@/components/assessment/FindingsContent";
import type { AssessmentResponse } from "@/types/assessment";
import {
  Loader2,
  ArrowLeft,
  Briefcase,
  AlertCircle,
} from "lucide-react";

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
                // No assessment context (404) -- load sample data
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
  ];

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

        {/* Assessment Findings Content */}
        {assessmentData && <FindingsContent data={assessmentData} />}

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
