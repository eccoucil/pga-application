/**
 * Questionnaire agent types matching the backend models in
 * backend/app/models/questionnaire.py
 */

/** Returned when the agent wants to ask the user something. */
export interface AgentQuestion {
  session_id: string;
  type: "question";
  question: string;
  context?: string | null;
  options?: string[] | null;
}

/** A single generated compliance question. */
export interface GeneratedQuestion {
  id: string;
  question: string;
  category: string;
  priority: string;
  expected_evidence?: string | null;
  guidance_notes?: string | null;
}

/** Questions generated for one framework control. */
export interface ControlQuestions {
  control_id: string;
  control_title: string;
  framework: string;
  questions: GeneratedQuestion[];
}

/** Returned when the agent finishes generating all questions. */
export interface QuestionnaireComplete {
  session_id: string;
  type: "complete";
  controls: ControlQuestions[];
  total_controls: number;
  total_questions: number;
  generation_time_ms: number;
  criteria_summary: string;
}

/** Discriminated union — narrows on `type` field. */
export type QuestionnaireResponse = AgentQuestion | QuestionnaireComplete;

/** Structured criteria for the wizard flow (batch generation). */
export interface GenerateWithCriteriaRequest {
  project_id: string;
  assessment_id?: string | null;
  maturity_level: "first_time_audit" | "recurring_assessment" | "mature_isms";
  question_depth: "high_level_overview" | "balanced" | "detailed_technical";
  priority_domains: string[];
  compliance_concerns?: string | null;
  controls_to_skip?: string | null;
}

/** Summary row from GET /questionnaire/sessions. */
export interface QuestionnaireSessionSummary {
  id: string;
  status: string;
  total_questions: number;
  total_controls: number;
  created_at: string;
  assessment_id: string | null;
}

/** Full session row from GET /questionnaire/sessions/:id. */
export interface QuestionnaireSessionDetail {
  id: string;
  project_id: string;
  client_id: string;
  status: string;
  assessment_id: string | null;
  generated_questions: ControlQuestions[];
  total_controls: number;
  total_questions: number;
  generation_time_ms: number;
  agent_criteria: { summary: string };
  created_at: string;
}
