-- Migration: Add grounding_source and batch_id columns to framework_questions
-- Purpose: Anti-hallucination tracking - store quote from control text that grounds each question
-- Date: 2026-01-23

-- Add grounding_source column for anti-hallucination tracking
ALTER TABLE framework_questions
ADD COLUMN IF NOT EXISTS grounding_source TEXT;

-- Add batch_id column for batch processing tracking
ALTER TABLE framework_questions
ADD COLUMN IF NOT EXISTS batch_id TEXT;

-- Add index for efficient batch queries
CREATE INDEX IF NOT EXISTS idx_framework_questions_batch
ON framework_questions(framework, batch_id);

-- Add index for grounding_source queries (useful for quality audits)
CREATE INDEX IF NOT EXISTS idx_framework_questions_grounding
ON framework_questions(framework, grounding_source)
WHERE grounding_source IS NOT NULL;

-- Comment on columns
COMMENT ON COLUMN framework_questions.grounding_source IS 'Quote from control text that grounds this question - anti-hallucination tracking';
COMMENT ON COLUMN framework_questions.batch_id IS 'Batch identifier for tracking question generation batches';
