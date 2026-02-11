-- Migration: Create project_documents table for document upload tracking
-- Run this migration in your Supabase SQL Editor

-- Create project_documents table
CREATE TABLE IF NOT EXISTS project_documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

  -- Document metadata from intake API
  filename TEXT NOT NULL,
  format TEXT NOT NULL,
  character_count INTEGER DEFAULT 0,
  word_count INTEGER DEFAULT 0,
  num_chunks INTEGER DEFAULT 0,
  extraction_confidence FLOAT,
  processing_time_ms FLOAT,
  metadata JSONB DEFAULT '{}',
  intake_document_id TEXT,

  -- Status
  status TEXT NOT NULL DEFAULT 'ready'
    CHECK (status IN ('uploading', 'processing', 'ready', 'error')),
  error_message TEXT,

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for faster lookups by project
CREATE INDEX IF NOT EXISTS idx_project_documents_project_id ON project_documents(project_id);

-- Create index for faster lookups by client
CREATE INDEX IF NOT EXISTS idx_project_documents_client_id ON project_documents(client_id);

-- Create index for faster lookups by user
CREATE INDEX IF NOT EXISTS idx_project_documents_user_id ON project_documents(user_id);

-- Create index for status filtering
CREATE INDEX IF NOT EXISTS idx_project_documents_status ON project_documents(status);

-- Enable Row Level Security
ALTER TABLE project_documents ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Users can only see their own documents
CREATE POLICY "Users can view own documents" ON project_documents
  FOR SELECT USING (auth.uid() = user_id);

-- RLS Policy: Users can insert their own documents
CREATE POLICY "Users can insert own documents" ON project_documents
  FOR INSERT WITH CHECK (auth.uid() = user_id);

-- RLS Policy: Users can update their own documents
CREATE POLICY "Users can update own documents" ON project_documents
  FOR UPDATE USING (auth.uid() = user_id);

-- RLS Policy: Users can delete their own documents
CREATE POLICY "Users can delete own documents" ON project_documents
  FOR DELETE USING (auth.uid() = user_id);

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_project_documents_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to auto-update updated_at
CREATE TRIGGER trigger_update_project_documents_updated_at
  BEFORE UPDATE ON project_documents
  FOR EACH ROW
  EXECUTE FUNCTION update_project_documents_updated_at();

-- Add comments to document columns
COMMENT ON TABLE project_documents IS 'Stores uploaded document metadata for compliance assessment projects';
COMMENT ON COLUMN project_documents.filename IS 'Original filename of the uploaded document';
COMMENT ON COLUMN project_documents.format IS 'File format (pdf, docx, txt, pptx, xlsx)';
COMMENT ON COLUMN project_documents.character_count IS 'Number of characters extracted from document';
COMMENT ON COLUMN project_documents.word_count IS 'Number of words extracted from document';
COMMENT ON COLUMN project_documents.num_chunks IS 'Number of chunks the document was split into';
COMMENT ON COLUMN project_documents.extraction_confidence IS 'Confidence score of text extraction (0-1)';
COMMENT ON COLUMN project_documents.processing_time_ms IS 'Time taken to process the document in milliseconds';
COMMENT ON COLUMN project_documents.metadata IS 'Additional metadata from document processing';
COMMENT ON COLUMN project_documents.intake_document_id IS 'Document ID returned from the intake API';
COMMENT ON COLUMN project_documents.status IS 'Processing status: uploading, processing, ready, error';
COMMENT ON COLUMN project_documents.error_message IS 'Error message if processing failed';
