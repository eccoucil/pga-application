-- Add assessment_id to questionnaire_sessions to link generated questions
-- to the specific assessment that provided context for generation.
-- Nullable because existing rows predate this column and the conversational
-- flow may not always have an assessment context.

ALTER TABLE questionnaire_sessions
  ADD COLUMN assessment_id UUID REFERENCES assessments(id) ON DELETE SET NULL;

CREATE INDEX idx_questionnaire_sessions_assessment
  ON questionnaire_sessions(assessment_id);
