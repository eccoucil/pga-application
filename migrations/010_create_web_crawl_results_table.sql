-- Migration: Create web_crawl_results table
-- Description: Stores results from web crawler agent including business context,
--               digital assets, and organization information extracted from websites
-- Created: 2024

CREATE TABLE IF NOT EXISTS web_crawl_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    web_domain TEXT NOT NULL,
    pages_crawled INTEGER NOT NULL DEFAULT 0,
    business_context JSONB,
    digital_assets JSONB DEFAULT '[]'::jsonb,
    organization_info JSONB,
    confidence_score FLOAT NOT NULL DEFAULT 0.0 CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_web_crawl_results_project_id ON web_crawl_results(project_id);
CREATE INDEX IF NOT EXISTS idx_web_crawl_results_client_id ON web_crawl_results(client_id);
CREATE INDEX IF NOT EXISTS idx_web_crawl_results_user_id ON web_crawl_results(user_id);
CREATE INDEX IF NOT EXISTS idx_web_crawl_results_created_at ON web_crawl_results(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_web_crawl_results_web_domain ON web_crawl_results(web_domain);

-- Update updated_at trigger
CREATE OR REPLACE FUNCTION update_web_crawl_results_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_web_crawl_results_updated_at
    BEFORE UPDATE ON web_crawl_results
    FOR EACH ROW
    EXECUTE FUNCTION update_web_crawl_results_updated_at();

-- Row Level Security (RLS)
ALTER TABLE web_crawl_results ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view crawl results for projects they have access to
CREATE POLICY "Users can view crawl results for their projects"
    ON web_crawl_results FOR SELECT
    USING (
        project_id IN (
            SELECT project_id 
            FROM client_members 
            WHERE user_id = auth.uid()
        )
    );

-- Policy: Users can create crawl results for projects they have access to
CREATE POLICY "Users can create crawl results for their projects"
    ON web_crawl_results FOR INSERT
    WITH CHECK (
        project_id IN (
            SELECT project_id 
            FROM client_members 
            WHERE user_id = auth.uid()
        )
    );

-- Policy: Users can update crawl results they created
CREATE POLICY "Users can update their own crawl results"
    ON web_crawl_results FOR UPDATE
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- Policy: Users can delete crawl results for projects they have access to
CREATE POLICY "Users can delete crawl results for their projects"
    ON web_crawl_results FOR DELETE
    USING (
        project_id IN (
            SELECT project_id 
            FROM client_members 
            WHERE user_id = auth.uid()
        )
    );

-- Comments for documentation
COMMENT ON TABLE web_crawl_results IS 'Stores results from web crawler agent including extracted business context, digital assets, and organization information';
COMMENT ON COLUMN web_crawl_results.business_context IS 'JSON object containing company name, industry, description, services, etc.';
COMMENT ON COLUMN web_crawl_results.digital_assets IS 'JSON array of digital assets (subdomains, portals, APIs) found during crawl';
COMMENT ON COLUMN web_crawl_results.organization_info IS 'JSON object containing contact info, certifications, partnerships, etc.';
COMMENT ON COLUMN web_crawl_results.confidence_score IS 'Confidence score (0.0-1.0) indicating quality of extraction';
