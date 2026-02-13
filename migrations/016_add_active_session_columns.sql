-- Add columns needed for persisting active questionnaire sessions
-- so they survive backend restarts (e.g. Railway redeploys).
--
-- pending_tool_use_id: tracks which Claude tool_use the user must respond to
-- started_at_ms:       epoch millis for generation-time tracking

ALTER TABLE questionnaire_sessions
  ADD COLUMN IF NOT EXISTS pending_tool_use_id TEXT,
  ADD COLUMN IF NOT EXISTS started_at_ms BIGINT;
