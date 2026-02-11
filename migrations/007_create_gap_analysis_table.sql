-- Migration: Create gap_analysis_findings table for storing gap analysis results
-- Run this migration in your Supabase SQL Editor

-- Create gap_analysis_findings table
CREATE TABLE IF NOT EXISTS gap_analysis_findings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

  -- Control identification
  framework TEXT NOT NULL,
  control_id TEXT NOT NULL,
  control_title TEXT NOT NULL,

  -- Compliance assessment
  compliance_level TEXT NOT NULL
    CHECK (compliance_level IN ('compliant', 'partially_compliant', 'non_compliant', 'not_assessed')),
  evidence_strength TEXT NOT NULL
    CHECK (evidence_strength IN ('strong', 'moderate', 'weak', 'none')),
  confidence_score FLOAT NOT NULL
    CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),

  -- Evidence grounding (anti-hallucination)
  grounding_quotes JSONB DEFAULT '[]',

  -- Analysis
  analysis_summary TEXT,
  gaps_identified JSONB DEFAULT '[]',
  recommendations JSONB DEFAULT '[]',

  -- Timestamps
  assessed_at TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_gap_findings_project_id ON gap_analysis_findings(project_id);
CREATE INDEX IF NOT EXISTS idx_gap_findings_client_id ON gap_analysis_findings(client_id);
CREATE INDEX IF NOT EXISTS idx_gap_findings_user_id ON gap_analysis_findings(user_id);
CREATE INDEX IF NOT EXISTS idx_gap_findings_framework ON gap_analysis_findings(framework);
CREATE INDEX IF NOT EXISTS idx_gap_findings_control_id ON gap_analysis_findings(control_id);
CREATE INDEX IF NOT EXISTS idx_gap_findings_compliance_level ON gap_analysis_findings(compliance_level);

-- Composite index for common queries (project + framework)
CREATE INDEX IF NOT EXISTS idx_gap_findings_project_framework
  ON gap_analysis_findings(project_id, framework);

-- Composite index for filtering by compliance level within project
CREATE INDEX IF NOT EXISTS idx_gap_findings_project_compliance
  ON gap_analysis_findings(project_id, compliance_level);

-- Enable Row Level Security
ALTER TABLE gap_analysis_findings ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Users can only see their own findings
CREATE POLICY "Users can view own gap findings" ON gap_analysis_findings
  FOR SELECT USING (auth.uid() = user_id);

-- RLS Policy: Users can insert their own findings
CREATE POLICY "Users can insert own gap findings" ON gap_analysis_findings
  FOR INSERT WITH CHECK (auth.uid() = user_id);

-- RLS Policy: Users can update their own findings
CREATE POLICY "Users can update own gap findings" ON gap_analysis_findings
  FOR UPDATE USING (auth.uid() = user_id);

-- RLS Policy: Users can delete their own findings
CREATE POLICY "Users can delete own gap findings" ON gap_analysis_findings
  FOR DELETE USING (auth.uid() = user_id);

-- Add comments to document columns
COMMENT ON TABLE gap_analysis_findings IS 'Stores gap analysis findings for compliance assessment';
COMMENT ON COLUMN gap_analysis_findings.framework IS 'Framework name: ISO 27001:2022 or BNM RMIT';
COMMENT ON COLUMN gap_analysis_findings.control_id IS 'Control identifier (e.g., A.5.1, 10.1)';
COMMENT ON COLUMN gap_analysis_findings.control_title IS 'Title of the control requirement';
COMMENT ON COLUMN gap_analysis_findings.compliance_level IS 'Assessment result: compliant, partially_compliant, non_compliant, not_assessed';
COMMENT ON COLUMN gap_analysis_findings.evidence_strength IS 'Strength of documentary evidence: strong, moderate, weak, none';
COMMENT ON COLUMN gap_analysis_findings.confidence_score IS 'Model confidence in assessment (0.0-1.0)';
COMMENT ON COLUMN gap_analysis_findings.grounding_quotes IS 'Array of direct quotes from documents supporting the assessment';
COMMENT ON COLUMN gap_analysis_findings.analysis_summary IS 'Summary of compliance status analysis';
COMMENT ON COLUMN gap_analysis_findings.gaps_identified IS 'Array of specific gaps found for this control';
COMMENT ON COLUMN gap_analysis_findings.recommendations IS 'Array of remediation recommendations';
COMMENT ON COLUMN gap_analysis_findings.assessed_at IS 'When the assessment was performed';

-- Create a unique constraint to prevent duplicate findings for same control
CREATE UNIQUE INDEX IF NOT EXISTS idx_gap_findings_unique_control
  ON gap_analysis_findings(project_id, framework, control_id);
