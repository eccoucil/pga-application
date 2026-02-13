-- Migration: Update project status values
-- Old values: planning, in-progress, completed, on-hold
-- New values: started, on-going, completed

-- 1. Drop the old CHECK constraint first (must happen before data updates)
ALTER TABLE projects DROP CONSTRAINT IF EXISTS projects_status_check;

-- 2. Update existing rows to new status values
UPDATE projects SET status = 'started' WHERE status = 'planning';
UPDATE projects SET status = 'on-going' WHERE status = 'in-progress';
UPDATE projects SET status = 'started' WHERE status = 'on-hold';

-- 3. Add the new CHECK constraint
ALTER TABLE projects ADD CONSTRAINT projects_status_check
  CHECK (status IN ('started', 'on-going', 'completed'));

-- 4. Update the default value
ALTER TABLE projects ALTER COLUMN status SET DEFAULT 'started';
