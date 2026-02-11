-- Migration 008: Create Multi-Tenant Client Members Infrastructure
-- This migration adds team collaboration support where multiple users can share access to clients
-- Run this migration in your Supabase SQL Editor

-- ============================================================================
-- PART 1: Create client_member_role enum type
-- ============================================================================

DO $$ BEGIN
    CREATE TYPE client_member_role AS ENUM ('owner', 'admin', 'member', 'viewer');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

COMMENT ON TYPE client_member_role IS 'Role levels for client membership: owner > admin > member > viewer';

-- ============================================================================
-- PART 2: Create client_members junction table
-- ============================================================================

CREATE TABLE IF NOT EXISTS client_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role client_member_role NOT NULL DEFAULT 'member',
    invited_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    invited_at TIMESTAMPTZ DEFAULT NOW(),
    accepted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(client_id, user_id)
);

-- Create indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_client_members_client_id ON client_members(client_id);
CREATE INDEX IF NOT EXISTS idx_client_members_user_id ON client_members(user_id);
CREATE INDEX IF NOT EXISTS idx_client_members_role ON client_members(role);

-- Add comments
COMMENT ON TABLE client_members IS 'Junction table for user-client membership with roles';
COMMENT ON COLUMN client_members.role IS 'Permission level: owner (full control), admin (manage team), member (create/edit), viewer (read-only)';
COMMENT ON COLUMN client_members.invited_by IS 'User who invited this member';
COMMENT ON COLUMN client_members.accepted_at IS 'When the invitation was accepted (NULL if pending)';

-- ============================================================================
-- PART 3: Create helper functions for RLS policies
-- ============================================================================

-- Function: Check if user is a member of a client (any role)
CREATE OR REPLACE FUNCTION is_client_member(p_client_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM client_members
        WHERE client_id = p_client_id
        AND user_id = auth.uid()
        AND (accepted_at IS NOT NULL OR role = 'owner')  -- Owners are auto-accepted
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

COMMENT ON FUNCTION is_client_member(UUID) IS 'Returns true if the current user is a member of the specified client';

-- Function: Check if user has minimum role level
CREATE OR REPLACE FUNCTION has_client_role(p_client_id UUID, p_min_role client_member_role)
RETURNS BOOLEAN AS $$
DECLARE
    v_user_role client_member_role;
    v_role_level INT;
    v_min_level INT;
BEGIN
    -- Get user's role for this client
    SELECT role INTO v_user_role
    FROM client_members
    WHERE client_id = p_client_id
    AND user_id = auth.uid()
    AND (accepted_at IS NOT NULL OR role = 'owner');

    IF v_user_role IS NULL THEN
        RETURN FALSE;
    END IF;

    -- Map roles to numeric levels for comparison
    -- viewer=0, member=1, admin=2, owner=3
    v_role_level := CASE v_user_role
        WHEN 'viewer' THEN 0
        WHEN 'member' THEN 1
        WHEN 'admin' THEN 2
        WHEN 'owner' THEN 3
    END;

    v_min_level := CASE p_min_role
        WHEN 'viewer' THEN 0
        WHEN 'member' THEN 1
        WHEN 'admin' THEN 2
        WHEN 'owner' THEN 3
    END;

    RETURN v_role_level >= v_min_level;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

COMMENT ON FUNCTION has_client_role(UUID, client_member_role) IS 'Returns true if user has the minimum required role level';

-- Convenience function: Can write to client (member or higher)
CREATE OR REPLACE FUNCTION can_write_client(p_client_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN has_client_role(p_client_id, 'member');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

COMMENT ON FUNCTION can_write_client(UUID) IS 'Returns true if user can create/edit content (member role or higher)';

-- Convenience function: Can manage client (admin or higher)
CREATE OR REPLACE FUNCTION can_manage_client(p_client_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN has_client_role(p_client_id, 'admin');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

COMMENT ON FUNCTION can_manage_client(UUID) IS 'Returns true if user can manage client settings and team (admin role or higher)';

-- Convenience function: Is client owner
CREATE OR REPLACE FUNCTION is_client_owner(p_client_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN has_client_role(p_client_id, 'owner');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

COMMENT ON FUNCTION is_client_owner(UUID) IS 'Returns true if user is the owner of the client';

-- ============================================================================
-- PART 4: Add audit columns to existing tables
-- ============================================================================

-- Add created_by and updated_by to clients
ALTER TABLE clients
    ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS updated_by UUID REFERENCES auth.users(id) ON DELETE SET NULL;

-- Add created_by and updated_by to projects
ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS updated_by UUID REFERENCES auth.users(id) ON DELETE SET NULL;

-- Add created_by and updated_by to project_documents
ALTER TABLE project_documents
    ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS updated_by UUID REFERENCES auth.users(id) ON DELETE SET NULL;

-- Add created_by and updated_by to framework_questions
ALTER TABLE framework_questions
    ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS updated_by UUID REFERENCES auth.users(id) ON DELETE SET NULL;

-- Add created_by to gap_analysis_findings (no updated_by since findings are not updated)
ALTER TABLE gap_analysis_findings
    ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL;

-- ============================================================================
-- PART 5: Create trigger for auto-creating owner membership on client creation
-- ============================================================================

CREATE OR REPLACE FUNCTION auto_create_client_owner()
RETURNS TRIGGER AS $$
BEGIN
    -- Auto-create owner membership for the user who created the client
    INSERT INTO client_members (client_id, user_id, role, accepted_at, invited_by)
    VALUES (NEW.id, NEW.user_id, 'owner', NOW(), NEW.user_id)
    ON CONFLICT (client_id, user_id) DO NOTHING;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS trigger_auto_create_client_owner ON clients;
CREATE TRIGGER trigger_auto_create_client_owner
    AFTER INSERT ON clients
    FOR EACH ROW
    EXECUTE FUNCTION auto_create_client_owner();

COMMENT ON FUNCTION auto_create_client_owner() IS 'Automatically creates owner membership when a new client is created';

-- ============================================================================
-- PART 6: Create updated_at trigger for client_members
-- ============================================================================

CREATE OR REPLACE FUNCTION update_client_members_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_client_members_updated_at ON client_members;
CREATE TRIGGER trigger_client_members_updated_at
    BEFORE UPDATE ON client_members
    FOR EACH ROW
    EXECUTE FUNCTION update_client_members_updated_at();

-- ============================================================================
-- PART 7: Enable RLS on client_members table
-- ============================================================================

ALTER TABLE client_members ENABLE ROW LEVEL SECURITY;

-- Policy: Members can view other members of clients they belong to
CREATE POLICY "Members can view client team" ON client_members
    FOR SELECT USING (is_client_member(client_id));

-- Policy: Admins+ can invite new members
CREATE POLICY "Admins can invite members" ON client_members
    FOR INSERT WITH CHECK (can_manage_client(client_id));

-- Policy: Admins+ can update member roles (but not demote owners)
CREATE POLICY "Admins can update members" ON client_members
    FOR UPDATE USING (
        can_manage_client(client_id)
        -- Prevent demoting owners unless you're the owner
        AND (
            role != 'owner'
            OR is_client_owner(client_id)
        )
    );

-- Policy: Owners can remove members, or members can remove themselves
CREATE POLICY "Owners can remove members or self-remove" ON client_members
    FOR DELETE USING (
        is_client_owner(client_id)
        OR user_id = auth.uid()
    );

-- ============================================================================
-- PART 8: Replace RLS policies on existing tables
-- ============================================================================

-- Drop existing policies on clients table
DROP POLICY IF EXISTS "Users can view own clients" ON clients;
DROP POLICY IF EXISTS "Users can insert own clients" ON clients;
DROP POLICY IF EXISTS "Users can update own clients" ON clients;
DROP POLICY IF EXISTS "Users can delete own clients" ON clients;

-- New policies for clients table (membership-based)
CREATE POLICY "Members can view clients" ON clients
    FOR SELECT USING (is_client_member(id));

CREATE POLICY "Authenticated users can create clients" ON clients
    FOR INSERT WITH CHECK (auth.uid() IS NOT NULL AND auth.uid() = user_id);

CREATE POLICY "Admins can update clients" ON clients
    FOR UPDATE USING (can_manage_client(id));

CREATE POLICY "Owners can delete clients" ON clients
    FOR DELETE USING (is_client_owner(id));

-- Drop existing policies on projects table
DROP POLICY IF EXISTS "Users can view own projects" ON projects;
DROP POLICY IF EXISTS "Users can insert own projects" ON projects;
DROP POLICY IF EXISTS "Users can update own projects" ON projects;
DROP POLICY IF EXISTS "Users can delete own projects" ON projects;

-- New policies for projects table (membership-based)
CREATE POLICY "Members can view projects" ON projects
    FOR SELECT USING (is_client_member(client_id));

CREATE POLICY "Members can create projects" ON projects
    FOR INSERT WITH CHECK (can_write_client(client_id));

CREATE POLICY "Members can update projects" ON projects
    FOR UPDATE USING (can_write_client(client_id));

CREATE POLICY "Admins can delete projects" ON projects
    FOR DELETE USING (can_manage_client(client_id));

-- Drop existing policies on project_documents table
DROP POLICY IF EXISTS "Users can view own documents" ON project_documents;
DROP POLICY IF EXISTS "Users can insert own documents" ON project_documents;
DROP POLICY IF EXISTS "Users can update own documents" ON project_documents;
DROP POLICY IF EXISTS "Users can delete own documents" ON project_documents;

-- New policies for project_documents table (membership-based)
CREATE POLICY "Members can view documents" ON project_documents
    FOR SELECT USING (is_client_member(client_id));

CREATE POLICY "Members can upload documents" ON project_documents
    FOR INSERT WITH CHECK (can_write_client(client_id));

CREATE POLICY "Members can update documents" ON project_documents
    FOR UPDATE USING (can_write_client(client_id));

CREATE POLICY "Admins can delete documents" ON project_documents
    FOR DELETE USING (can_manage_client(client_id));

-- Drop existing policies on framework_questions table
DROP POLICY IF EXISTS "Users can view own framework questions" ON framework_questions;
DROP POLICY IF EXISTS "Users can insert own framework questions" ON framework_questions;
DROP POLICY IF EXISTS "Users can update own framework questions" ON framework_questions;
DROP POLICY IF EXISTS "Users can delete own framework questions" ON framework_questions;

-- New policies for framework_questions table (membership-based)
CREATE POLICY "Members can view questions" ON framework_questions
    FOR SELECT USING (is_client_member(client_id));

CREATE POLICY "Members can generate questions" ON framework_questions
    FOR INSERT WITH CHECK (can_write_client(client_id));

CREATE POLICY "Members can update questions" ON framework_questions
    FOR UPDATE USING (can_write_client(client_id));

CREATE POLICY "Admins can delete questions" ON framework_questions
    FOR DELETE USING (can_manage_client(client_id));

-- Drop existing policies on gap_analysis_findings table
DROP POLICY IF EXISTS "Users can view own gap findings" ON gap_analysis_findings;
DROP POLICY IF EXISTS "Users can insert own gap findings" ON gap_analysis_findings;
DROP POLICY IF EXISTS "Users can update own gap findings" ON gap_analysis_findings;
DROP POLICY IF EXISTS "Users can delete own gap findings" ON gap_analysis_findings;

-- New policies for gap_analysis_findings table (membership-based)
CREATE POLICY "Members can view findings" ON gap_analysis_findings
    FOR SELECT USING (is_client_member(client_id));

CREATE POLICY "Members can create findings" ON gap_analysis_findings
    FOR INSERT WITH CHECK (can_write_client(client_id));

CREATE POLICY "Members can update findings" ON gap_analysis_findings
    FOR UPDATE USING (can_write_client(client_id));

CREATE POLICY "Admins can delete findings" ON gap_analysis_findings
    FOR DELETE USING (can_manage_client(client_id));

-- ============================================================================
-- PART 9: Handle question_responses table (references framework_questions)
-- ============================================================================

-- Check if question_responses table exists before modifying
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'question_responses') THEN
        -- Add created_by column if not exists
        ALTER TABLE question_responses
            ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL;

        -- Drop existing policies
        DROP POLICY IF EXISTS "Users can view own responses" ON question_responses;
        DROP POLICY IF EXISTS "Users can insert own responses" ON question_responses;
        DROP POLICY IF EXISTS "Users can update own responses" ON question_responses;
        DROP POLICY IF EXISTS "Users can delete own responses" ON question_responses;

        -- New policies based on question's client_id
        -- (We need to join through framework_questions to get client_id)
        EXECUTE 'CREATE POLICY "Members can view responses" ON question_responses
            FOR SELECT USING (
                EXISTS (
                    SELECT 1 FROM framework_questions fq
                    WHERE fq.id = question_responses.question_id
                    AND is_client_member(fq.client_id)
                )
            )';

        EXECUTE 'CREATE POLICY "Members can submit responses" ON question_responses
            FOR INSERT WITH CHECK (
                EXISTS (
                    SELECT 1 FROM framework_questions fq
                    WHERE fq.id = question_responses.question_id
                    AND can_write_client(fq.client_id)
                )
            )';

        EXECUTE 'CREATE POLICY "Members can update responses" ON question_responses
            FOR UPDATE USING (
                EXISTS (
                    SELECT 1 FROM framework_questions fq
                    WHERE fq.id = question_responses.question_id
                    AND can_write_client(fq.client_id)
                )
            )';

        EXECUTE 'CREATE POLICY "Admins can delete responses" ON question_responses
            FOR DELETE USING (
                EXISTS (
                    SELECT 1 FROM framework_questions fq
                    WHERE fq.id = question_responses.question_id
                    AND can_manage_client(fq.client_id)
                )
            )';
    END IF;
END $$;
