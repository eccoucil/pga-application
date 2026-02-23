-- Fix questionnaire_sessions foreign keys to cascade on parent deletion.
-- project_id and client_id were missing ON DELETE CASCADE (migration 011),
-- which blocked project and client deletion.

ALTER TABLE questionnaire_sessions
  DROP CONSTRAINT questionnaire_sessions_project_id_fkey,
  ADD CONSTRAINT questionnaire_sessions_project_id_fkey
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE;

ALTER TABLE questionnaire_sessions
  DROP CONSTRAINT questionnaire_sessions_client_id_fkey,
  ADD CONSTRAINT questionnaire_sessions_client_id_fkey
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE;
