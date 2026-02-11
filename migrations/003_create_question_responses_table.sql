-- Migration: Create question_responses table for storing user answers to compliance questions
-- Run this migration in your Supabase SQL Editor

-- Create question_responses table
CREATE TABLE IF NOT EXISTS question_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    framework_question_id UUID NOT NULL REFERENCES framework_questions(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    question_number INTEGER NOT NULL CHECK (question_number BETWEEN 1 AND 5),

    -- Response data
    response_text TEXT,
    compliance_status TEXT CHECK (compliance_status IN ('compliant', 'partial', 'non_compliant', 'not_applicable', 'pending')),
    evidence_provided TEXT,
    evidence_files JSONB,  -- Array of file references [{filename, storage_path, uploaded_at}]

    -- Audit trail
    responded_by UUID REFERENCES auth.users(id),
    responded_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Ensure one response per question per framework_question
    UNIQUE(framework_question_id, question_number)
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_responses_project ON question_responses(project_id);
CREATE INDEX IF NOT EXISTS idx_responses_framework_question ON question_responses(framework_question_id);
CREATE INDEX IF NOT EXISTS idx_responses_status ON question_responses(compliance_status);
CREATE INDEX IF NOT EXISTS idx_responses_user ON question_responses(user_id);

-- Enable Row Level Security
ALTER TABLE question_responses ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Users can only see responses for their projects
CREATE POLICY "Users can view own question responses" ON question_responses
    FOR SELECT USING (auth.uid() = user_id);

-- RLS Policy: Users can insert responses for their projects
CREATE POLICY "Users can insert own question responses" ON question_responses
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- RLS Policy: Users can update their own responses
CREATE POLICY "Users can update own question responses" ON question_responses
    FOR UPDATE USING (auth.uid() = user_id);

-- RLS Policy: Users can delete their own responses
CREATE POLICY "Users can delete own question responses" ON question_responses
    FOR DELETE USING (auth.uid() = user_id);

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_question_responses_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for auto-updating updated_at
DROP TRIGGER IF EXISTS trigger_question_responses_updated_at ON question_responses;
CREATE TRIGGER trigger_question_responses_updated_at
    BEFORE UPDATE ON question_responses
    FOR EACH ROW
    EXECUTE FUNCTION update_question_responses_updated_at();

-- Add comments to document the table
COMMENT ON TABLE question_responses IS 'Stores user responses to AI-generated compliance assessment questions';
COMMENT ON COLUMN question_responses.framework_question_id IS 'References the framework_questions record containing the question';
COMMENT ON COLUMN question_responses.question_number IS 'Which of the 5 questions this response is for (1-5)';
COMMENT ON COLUMN question_responses.compliance_status IS 'Current compliance status: compliant, partial, non_compliant, not_applicable, pending';
COMMENT ON COLUMN question_responses.evidence_files IS 'JSONB array of file references: [{filename, storage_path, uploaded_at}]';
COMMENT ON COLUMN question_responses.responded_by IS 'User who last updated this response';
COMMENT ON COLUMN question_responses.responded_at IS 'Timestamp of last response update';
