-- Migration: add observations column to documentation_results
-- Apply with: psql $DATABASE_URL -f backend/migrations/add_observations_column.sql
-- Safe to run multiple times (uses IF NOT EXISTS guard via column check).

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'documentation_results'
           AND column_name = 'observations'
    ) THEN
        ALTER TABLE documentation_results ADD COLUMN observations JSONB;
    END IF;
END $$;
