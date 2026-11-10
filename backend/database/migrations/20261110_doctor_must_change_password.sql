-- Migration: Add must_change_password to users table
-- Date: 2026-11-10
-- Purpose: Support mandatory first-login password changes for newly created doctor accounts.
-- Compatibility: Existing accounts (patients, doctors, admins) default to FALSE so they are not disrupted.

ALTER TABLE users ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN users.must_change_password IS 'Identifies whether the account must change its password upon next login (e.g. temporary password for new doctors).';

