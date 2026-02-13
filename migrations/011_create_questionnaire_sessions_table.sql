-- Create questionnaire_sessions table for storing
-- conversational question generation sessions and results.

CREATE TABLE IF NOT EXISTS questionnaire_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id),
    client_id UUID NOT NULL REFERENCES clients(id),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'generating', 'completed', 'failed')),
    agent_criteria JSONB DEFAULT '{}'::jsonb,
    generated_questions JSONB DEFAULT '[]'::jsonb,
    conversation_history JSONB DEFAULT '[]'::jsonb,
    model_used TEXT NOT NULL DEFAULT 'claude-opus-4-6',
    total_controls INTEGER DEFAULT 0,
    total_questions INTEGER DEFAULT 0,
    generation_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ,
    created_by UUID REFERENCES auth.users(id)
);

CREATE INDEX idx_questionnaire_sessions_project ON questionnaire_sessions(project_id);
CREATE INDEX idx_questionnaire_sessions_status ON questionnaire_sessions(status);

-- RLS: users can only see sessions they created or that belong to their projects
ALTER TABLE questionnaire_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own sessions"
    ON questionnaire_sessions FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own sessions"
    ON questionnaire_sessions FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Service role has full access"
    ON questionnaire_sessions FOR ALL
    USING (auth.role() = 'service_role');
