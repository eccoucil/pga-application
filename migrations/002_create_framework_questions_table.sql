-- Migration: Create framework_questions table for storing AI-generated compliance questions
-- Run this migration in your Supabase SQL Editor

-- Create framework_questions table
CREATE TABLE IF NOT EXISTS framework_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    framework TEXT NOT NULL,
    control_id TEXT NOT NULL,
    control_title TEXT NOT NULL,
    control_description TEXT,
    questions JSONB NOT NULL,  -- Array of 5 questions with metadata
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_framework_questions_project ON framework_questions(project_id);
CREATE INDEX IF NOT EXISTS idx_framework_questions_client ON framework_questions(client_id);
CREATE INDEX IF NOT EXISTS idx_framework_questions_user ON framework_questions(user_id);
CREATE INDEX IF NOT EXISTS idx_framework_questions_framework ON framework_questions(framework);
CREATE INDEX IF NOT EXISTS idx_framework_questions_control ON framework_questions(control_id);

-- Enable Row Level Security
ALTER TABLE framework_questions ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Users can only see their own generated questions
CREATE POLICY "Users can view own framework questions" ON framework_questions
    FOR SELECT USING (auth.uid() = user_id);

-- RLS Policy: Users can insert their own framework questions
CREATE POLICY "Users can insert own framework questions" ON framework_questions
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- RLS Policy: Users can update their own framework questions
CREATE POLICY "Users can update own framework questions" ON framework_questions
    FOR UPDATE USING (auth.uid() = user_id);

-- RLS Policy: Users can delete their own framework questions
CREATE POLICY "Users can delete own framework questions" ON framework_questions
    FOR DELETE USING (auth.uid() = user_id);

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_framework_questions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for auto-updating updated_at
DROP TRIGGER IF EXISTS trigger_framework_questions_updated_at ON framework_questions;
CREATE TRIGGER trigger_framework_questions_updated_at
    BEFORE UPDATE ON framework_questions
    FOR EACH ROW
    EXECUTE FUNCTION update_framework_questions_updated_at();

-- Add comment to document the table
COMMENT ON TABLE framework_questions IS 'Stores AI-generated compliance assessment questions for each framework control';
COMMENT ON COLUMN framework_questions.questions IS 'JSONB array of question objects: [{question_number, question_text, question_type, expected_evidence}]';
