-- Add object_id to service_tickets for direct object reference.
-- Backfill from user's object_id for existing rows.
-- Run: psql -U <user> -d <database> -f add_service_ticket_object_id.sql

ALTER TABLE service_tickets
  ADD COLUMN IF NOT EXISTS object_id INTEGER REFERENCES objects(id);

-- Backfill: copy object_id from user for existing tickets
UPDATE service_tickets st
SET object_id = u.object_id
FROM users u
WHERE st.user_id = u.id
  AND st.object_id IS NULL
  AND u.object_id IS NOT NULL;
