-- Migration 015: Enable pgvector extension + create document_chunks table
-- Replaces Qdrant's pga_documents collection with PostgreSQL + pgvector

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Replace Qdrant's pga_documents collection
CREATE TABLE document_chunks (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id TEXT NOT NULL,
    project_id  UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    client_id   UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL DEFAULT 0,
    text        TEXT NOT NULL,
    token_count INT DEFAULT 0,
    doc_type    TEXT,
    framework   TEXT,
    control_ids JSONB DEFAULT '[]',
    filename    TEXT,
    field_name  TEXT,
    start_char  INT,
    end_char    INT,
    embedding   vector(1536) NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for filtered search (mirror Qdrant's keyword indexes)
CREATE INDEX idx_chunks_project ON document_chunks(project_id);
CREATE INDEX idx_chunks_document ON document_chunks(document_id);
CREATE INDEX idx_chunks_client ON document_chunks(client_id);
CREATE INDEX idx_chunks_doc_type ON document_chunks(doc_type);
CREATE INDEX idx_chunks_framework ON document_chunks(framework);

-- HNSW index for fast vector similarity search
CREATE INDEX idx_chunks_embedding ON document_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Similarity search function (replaces Qdrant search)
CREATE OR REPLACE FUNCTION match_document_chunks(
    query_embedding vector(1536),
    match_project_id UUID,
    match_threshold FLOAT DEFAULT 0.3,
    match_count INT DEFAULT 10,
    filter_framework TEXT DEFAULT NULL,
    filter_doc_type TEXT DEFAULT NULL,
    filter_document_ids TEXT[] DEFAULT NULL
)
RETURNS TABLE (
    id UUID, document_id TEXT, project_id UUID, client_id UUID,
    chunk_index INT, text TEXT, token_count INT, doc_type TEXT,
    framework TEXT, control_ids JSONB, filename TEXT, field_name TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT
        dc.id, dc.document_id, dc.project_id, dc.client_id,
        dc.chunk_index, dc.text, dc.token_count, dc.doc_type,
        dc.framework, dc.control_ids, dc.filename, dc.field_name,
        1 - (dc.embedding <=> query_embedding) AS similarity
    FROM document_chunks dc
    WHERE dc.project_id = match_project_id
      AND (1 - (dc.embedding <=> query_embedding)) >= match_threshold
      AND (filter_framework IS NULL OR dc.framework = filter_framework)
      AND (filter_doc_type IS NULL OR dc.doc_type = filter_doc_type)
      AND (filter_document_ids IS NULL OR dc.document_id = ANY(filter_document_ids))
    ORDER BY dc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Client extraction search (replaces search_company_extractions)
CREATE OR REPLACE FUNCTION match_client_extractions(
    query_embedding vector(1536),
    match_client_id UUID,
    match_count INT DEFAULT 10
)
RETURNS TABLE (
    id UUID, document_id TEXT, text TEXT, doc_type TEXT,
    filename TEXT, field_name TEXT, similarity FLOAT
)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT
        dc.id, dc.document_id, dc.text, dc.doc_type,
        dc.filename, dc.field_name,
        1 - (dc.embedding <=> query_embedding) AS similarity
    FROM document_chunks dc
    WHERE dc.client_id = match_client_id
      AND dc.doc_type IN ('llama_extraction', 'fallback_extraction')
    ORDER BY dc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
