-- Migration 012: Create assessments table for persistent assessment records
-- Depends on: 008_multi_tenant_client_members.sql (is_client_member, can_write_client)

CREATE TABLE IF NOT EXISTS assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id),
    version INT NOT NULL DEFAULT 1,

    -- Step 1 form fields (denormalized for fast table queries)
    organization_name TEXT NOT NULL,
    nature_of_business TEXT NOT NULL,
    industry_type TEXT NOT NULL,
    department TEXT NOT NULL,
    scope_statement_isms TEXT NOT NULL,
    web_domain TEXT,

    -- Processing state
    status TEXT NOT NULL DEFAULT 'received'
        CHECK (status IN ('received','processing','completed','failed','partial')),
    documents_count INT NOT NULL DEFAULT 0,

    -- Snapshot of orchestrator response (frozen at submission time)
    response_snapshot JSONB,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Auto-increment version per project
CREATE OR REPLACE FUNCTION set_assessment_version()
RETURNS TRIGGER AS $$
BEGIN
    NEW.version := COALESCE(
        (SELECT MAX(version) FROM assessments WHERE project_id = NEW.project_id), 0
    ) + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_assessment_version
    BEFORE INSERT ON assessments
    FOR EACH ROW EXECUTE FUNCTION set_assessment_version();

-- Indexes
CREATE INDEX idx_assessments_project ON assessments(project_id, created_at DESC);
CREATE INDEX idx_assessments_client ON assessments(client_id);
CREATE INDEX idx_assessments_user ON assessments(user_id);

-- RLS (reuse existing helper functions from migration 008)
ALTER TABLE assessments ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Members can view assessments"
    ON assessments FOR SELECT
    USING (is_client_member(client_id));

CREATE POLICY "Writers can create assessments"
    ON assessments FOR INSERT
    WITH CHECK (can_write_client(client_id));

CREATE POLICY "Writers can update assessments"
    ON assessments FOR UPDATE
    USING (can_write_client(client_id));
