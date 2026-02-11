-- Migration 009: Migrate Existing Data to Multi-Tenant Schema
-- This migration populates the client_members table and audit columns for existing data
-- Run this migration AFTER 008_multi_tenant_client_members.sql

-- ============================================================================
-- PART 1: Create owner memberships for existing clients
-- ============================================================================

-- Insert owner membership for each existing client's user_id
-- Uses ON CONFLICT to safely handle any clients already processed
INSERT INTO client_members (client_id, user_id, role, accepted_at, invited_by, created_at)
SELECT
    c.id AS client_id,
    c.user_id AS user_id,
    'owner' AS role,
    COALESCE(c.created_at, NOW()) AS accepted_at,
    c.user_id AS invited_by,
    COALESCE(c.created_at, NOW()) AS created_at
FROM clients c
WHERE NOT EXISTS (
    SELECT 1 FROM client_members cm
    WHERE cm.client_id = c.id
    AND cm.user_id = c.user_id
);

-- Log the migration
DO $$
DECLARE
    v_migrated_count INT;
BEGIN
    SELECT COUNT(*) INTO v_migrated_count
    FROM client_members
    WHERE role = 'owner';

    RAISE NOTICE 'Created % owner memberships for existing clients', v_migrated_count;
END $$;

-- ============================================================================
-- PART 2: Populate audit columns on existing tables
-- ============================================================================

-- Update clients: set created_by from user_id
UPDATE clients
SET
    created_by = user_id,
    updated_by = user_id
WHERE created_by IS NULL;

-- Update projects: set created_by from user_id
UPDATE projects
SET
    created_by = user_id,
    updated_by = user_id
WHERE created_by IS NULL;

-- Update project_documents: set created_by from user_id
UPDATE project_documents
SET
    created_by = user_id,
    updated_by = user_id
WHERE created_by IS NULL;

-- Update framework_questions: set created_by from user_id
UPDATE framework_questions
SET
    created_by = user_id,
    updated_by = user_id
WHERE created_by IS NULL;

-- Update gap_analysis_findings: set created_by from user_id
UPDATE gap_analysis_findings
SET created_by = user_id
WHERE created_by IS NULL;

-- Update question_responses if it exists
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'question_responses') THEN
        EXECUTE 'UPDATE question_responses SET created_by = user_id WHERE created_by IS NULL';
    END IF;
END $$;

-- ============================================================================
-- PART 3: Verify migration
-- ============================================================================

DO $$
DECLARE
    v_clients_without_owners INT;
    v_clients_total INT;
    v_orphan_projects INT;
BEGIN
    -- Check for clients without owner membership
    SELECT COUNT(*) INTO v_clients_without_owners
    FROM clients c
    WHERE NOT EXISTS (
        SELECT 1 FROM client_members cm
        WHERE cm.client_id = c.id
        AND cm.role = 'owner'
    );

    -- Get total clients
    SELECT COUNT(*) INTO v_clients_total FROM clients;

    -- Check for projects where user is not a client member
    SELECT COUNT(*) INTO v_orphan_projects
    FROM projects p
    WHERE NOT EXISTS (
        SELECT 1 FROM client_members cm
        WHERE cm.client_id = p.client_id
        AND cm.user_id = p.user_id
    );

    IF v_clients_without_owners > 0 THEN
        RAISE WARNING 'Found % clients without owner membership!', v_clients_without_owners;
    ELSE
        RAISE NOTICE 'All % clients have owner memberships', v_clients_total;
    END IF;

    IF v_orphan_projects > 0 THEN
        RAISE WARNING 'Found % projects where creator is not a client member!', v_orphan_projects;
    ELSE
        RAISE NOTICE 'All project creators are client members';
    END IF;
END $$;

-- ============================================================================
-- PART 4: Add helpful views for querying client memberships
-- ============================================================================

-- View: Get client with user's role
CREATE OR REPLACE VIEW client_with_role AS
SELECT
    c.*,
    cm.role AS my_role,
    cm.accepted_at AS membership_accepted_at
FROM clients c
JOIN client_members cm ON cm.client_id = c.id AND cm.user_id = auth.uid();

COMMENT ON VIEW client_with_role IS 'Clients the current user is a member of, with their role';

-- View: Get team members for display
CREATE OR REPLACE VIEW client_team_members AS
SELECT
    cm.id AS membership_id,
    cm.client_id,
    cm.user_id,
    cm.role,
    cm.invited_by,
    cm.invited_at,
    cm.accepted_at,
    p.email,
    p.full_name,
    p.organization
FROM client_members cm
LEFT JOIN profiles p ON p.id = cm.user_id
WHERE is_client_member(cm.client_id);  -- Only show for clients user belongs to

COMMENT ON VIEW client_team_members IS 'Team members of clients the current user belongs to, with profile info';
