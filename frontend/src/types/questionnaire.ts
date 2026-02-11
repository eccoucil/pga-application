export type QuestionScope = 'framework_overview' | 'section_deep_dive'
export type QuestionStyle = 'control_specific' | 'practice_based' | 'evidence_focused' | 'maturity_assessment'
export type QuestionType = 'policy' | 'implementation' | 'evidence'

export interface GeneratedQuestion {
  question_number: number
  question_text: string
  question_type: QuestionType
  expected_evidence: string
}

export interface FrameworkQuestion {
  id: string
  project_id: string
  framework: string
  control_id: string | null
  control_title: string | null
  section_id: string | null
  section_title: string | null
  question_scope: QuestionScope | null
  question_style: QuestionStyle | null
  questions: GeneratedQuestion[]
  referenced_controls: string[]
  grounding_source: string | null
  generated_at: string
}

export interface SectionGroup {
  section_id: string
  section_title: string
  framework: string
  question_scope: QuestionScope | null
  questions: FrameworkQuestion[]
}

export interface ControlItem {
  control_id: string
  control_title: string
  framework: string
  question_scope: QuestionScope | null
  frameworkQuestion: FrameworkQuestion
}

export interface SectionWithControls {
  section_id: string
  section_title: string
  framework: string
  controls: ControlItem[]
}
