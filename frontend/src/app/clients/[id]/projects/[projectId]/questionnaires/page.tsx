"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { useClient } from "@/contexts/ClientContext";
import { useProject } from "@/contexts/ProjectContext";
import { useAuth } from "@/contexts/AuthContext";
import { getClient, getProject } from "@/lib/supabase";
import {
  AssessmentStepper,
  type AssessmentStep,
} from "@/components/ui/assessment-stepper";
import { QuestionnaireContent } from "@/components/project/QuestionnaireContent";
import { Loader2, ArrowLeft } from "lucide-react";

export default function QuestionnairesPage() {
  const params = useParams();
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const { selectedClient, setSelectedClient } = useClient();
  const { selectedProject, setSelectedProject } = useProject();
  const clientId = params.id as string;
  const projectId = params.projectId as string;
  const [loading, setLoading] = useState(true);

  // Fetch client and project data if not in context
  useEffect(() => {
    const fetchData = async () => {
      if (!authLoading && user) {
        setLoading(true);
        try {
          if (!selectedClient && clientId) {
            const { data: client, error: clientError } =
              await getClient(clientId);
            if (clientError || !client) {
              router.push("/clients");
              return;
            }
            setSelectedClient(client);
          }

          if (!selectedProject && projectId) {
            const { data: project, error: projectError } =
              await getProject(projectId);
            if (projectError || !project) {
              router.push(`/clients/${clientId}/projects`);
              return;
            }
            setSelectedProject(project);
          }
        } catch (error) {
          console.error("Error loading project data:", error);
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
    { number: 2, title: "Questionnaire", status: "current" },
  ];

  return (
    <DashboardLayout>
      <div className="max-w-6xl mx-auto pb-10">
        {/* Back Button */}
        <button
          onClick={() =>
            router.push(
              `/clients/${clientId}/projects/${projectId}/assessment`,
            )
          }
          className="mb-6 flex items-center gap-2 px-4 py-2.5 bg-[#0f1016]/80 backdrop-blur-md border border-white/10 rounded-lg text-slate-300 hover:text-white hover:bg-white/10 transition-all shadow-lg hover:shadow-xl hover:border-purple-500/30 group w-fit"
          title="Back to Assessment"
        >
          <ArrowLeft className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" />
          <span className="text-sm font-medium">Back to Assessment</span>
        </button>

        {/* Stepper */}
        <AssessmentStepper steps={steps} />

        {/* Title */}
        <h1 className="text-2xl font-bold text-white mb-6">
          Compliance Questionnaire
        </h1>

        {/* Content */}
        {selectedProject ? (
          <QuestionnaireContent
            clientId={clientId}
            projectId={projectId}
            project={selectedProject}
          />
        ) : (
          <div className="bg-[#0f1016]/60 backdrop-blur-md border border-white/10 rounded-2xl p-12 text-center">
            <Loader2 className="h-8 w-8 animate-spin text-gray-400 mx-auto mb-4" />
            <p className="text-slate-400">Loading project data...</p>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
