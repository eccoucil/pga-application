-- Migration: Update framework_questions table for framework-level question generation
-- This migration adds columns to support the new hybrid question generation approach
-- Run this migration in your Supabase SQL Editor

-- Add new columns for framework-level questions
ALTER TABLE framework_questions
ADD COLUMN IF NOT EXISTS question_scope TEXT,
ADD COLUMN IF NOT EXISTS question_style TEXT,
ADD COLUMN IF NOT EXISTS section_id TEXT,
ADD COLUMN IF NOT EXISTS section_title TEXT,
ADD COLUMN IF NOT EXISTS referenced_controls JSONB DEFAULT '[]',
ADD COLUMN IF NOT EXISTS assessment_criteria TEXT;

-- Make control_id nullable for framework-level (overview) questions
-- Overview questions don't map to a single control
ALTER TABLE framework_questions ALTER COLUMN control_id DROP NOT NULL;
ALTER TABLE framework_questions ALTER COLUMN control_title DROP NOT NULL;

-- Create index for efficient section-based queries
CREATE INDEX IF NOT EXISTS idx_framework_questions_section
ON framework_questions(framework, section_id);

-- Create index for scope-based queries (overview vs section deep-dive)
CREATE INDEX IF NOT EXISTS idx_framework_questions_scope
ON framework_questions(question_scope);

-- Add comments to document new columns
COMMENT ON COLUMN framework_questions.question_scope IS 'Scope: framework_overview or section_deep_dive';
COMMENT ON COLUMN framework_questions.question_style IS 'Style: control_specific, practice_based, evidence_focused, or maturity_assessment';
COMMENT ON COLUMN framework_questions.section_id IS 'Section identifier (e.g., overview, A.5, section_10)';
COMMENT ON COLUMN framework_questions.section_title IS 'Human-readable section title';
COMMENT ON COLUMN framework_questions.referenced_controls IS 'Array of control IDs referenced by this question';
COMMENT ON COLUMN framework_questions.assessment_criteria IS 'Criteria for evaluating the response quality';

-- Update table comment
COMMENT ON TABLE framework_questions IS 'Stores AI-generated compliance assessment questions. Supports both per-control (legacy) and framework-level (new) question formats.';
