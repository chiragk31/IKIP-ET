-- Migration: 002_knowledge_extractions.sql
-- Epic 3 — AI Knowledge Extraction
-- Creates the knowledge_extractions table for CKO metadata

-- ============================================================
-- Table: knowledge_extractions
-- ============================================================
-- Stores metadata about each AI extraction run.
-- The full CKO JSON is stored in Supabase Storage at:
--   knowledge/{document_id}/cko.json
-- ============================================================

CREATE TABLE IF NOT EXISTS knowledge_extractions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id             UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    storage_path            TEXT NOT NULL DEFAULT '',
    model_version           TEXT NOT NULL DEFAULT '',
    prompt_version          TEXT NOT NULL DEFAULT '1.0',
    confidence              FLOAT NOT NULL DEFAULT 0.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    entity_count            INTEGER NOT NULL DEFAULT 0,
    relationship_count      INTEGER NOT NULL DEFAULT 0,
    measurement_count       INTEGER NOT NULL DEFAULT 0,
    procedure_count         INTEGER NOT NULL DEFAULT 0,
    risk_count              INTEGER NOT NULL DEFAULT 0,
    extraction_time_seconds FLOAT NOT NULL DEFAULT 0.0,
    extraction_timestamp    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status                  TEXT NOT NULL DEFAULT 'completed' CHECK (status IN ('completed', 'failed', 'partial')),
    error_message           TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Unique constraint: one extraction record per document (upsert target)
CREATE UNIQUE INDEX IF NOT EXISTS knowledge_extractions_document_id_key
    ON knowledge_extractions(document_id);

-- Index for querying by status
CREATE INDEX IF NOT EXISTS knowledge_extractions_status_idx
    ON knowledge_extractions(status);

-- Index for querying by confidence
CREATE INDEX IF NOT EXISTS knowledge_extractions_confidence_idx
    ON knowledge_extractions(confidence);

-- Automatically update updated_at
CREATE OR REPLACE FUNCTION update_knowledge_extractions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS knowledge_extractions_updated_at ON knowledge_extractions;
CREATE TRIGGER knowledge_extractions_updated_at
    BEFORE UPDATE ON knowledge_extractions
    FOR EACH ROW
    EXECUTE FUNCTION update_knowledge_extractions_updated_at();

-- ============================================================
-- Row Level Security (RLS)
-- ============================================================
-- Deferred until authentication is implemented (Epic 11)
-- Auth is not enforced during development phase
ALTER TABLE knowledge_extractions ENABLE ROW LEVEL SECURITY;

-- Permissive policy for development (all authenticated users can read/write)
DROP POLICY IF EXISTS knowledge_extractions_dev_policy ON knowledge_extractions;
CREATE POLICY knowledge_extractions_dev_policy ON knowledge_extractions
    USING (true)
    WITH CHECK (true);
