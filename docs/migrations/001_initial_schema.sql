-- =============================================
-- IKIP — Initial Database Schema
-- Migration: 001_initial_schema.sql
-- =============================================
-- Run this in: Supabase Dashboard → SQL Editor → New Query
-- =============================================


-- =============================================
-- USERS TABLE
-- Extends Supabase Auth with profile fields.
-- Auth itself is managed by Supabase auth.users.
-- =============================================
CREATE TABLE IF NOT EXISTS public.users (
    id          UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email       TEXT NOT NULL UNIQUE,
    name        TEXT,
    role        TEXT NOT NULL DEFAULT 'engineer'
                    CHECK (role IN ('admin', 'engineer', 'operator', 'viewer')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();


-- =============================================
-- DOCUMENTS TABLE
-- Stores metadata for all uploaded documents.
-- Raw files live in Supabase Storage (bucket: documents).
-- AI output (graph, embeddings) lives in Neo4j / Pinecone.
-- =============================================
CREATE TABLE IF NOT EXISTS public.documents (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID REFERENCES public.users(id) ON DELETE SET NULL,
    filename            TEXT NOT NULL,
    original_filename   TEXT NOT NULL,
    storage_path        TEXT NOT NULL,
    file_type           TEXT NOT NULL,
    file_size           BIGINT NOT NULL DEFAULT 0,
    upload_time         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status              TEXT NOT NULL DEFAULT 'queued'
                            CHECK (status IN (
                                'queued', 'uploading', 'uploaded', 'processing',
                                'parsing', 'ocr_running', 'extracting',
                                'building_graph', 'generating_embeddings',
                                'summarizing', 'compliance_check',
                                'completed', 'failed'
                            )),
    processing_stage    TEXT,
    summary             TEXT,
    language            TEXT DEFAULT 'en',
    document_type       TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER documents_updated_at
    BEFORE UPDATE ON public.documents
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

-- Index for common queries
CREATE INDEX IF NOT EXISTS documents_user_id_idx    ON public.documents(user_id);
CREATE INDEX IF NOT EXISTS documents_status_idx     ON public.documents(status);
CREATE INDEX IF NOT EXISTS documents_file_type_idx  ON public.documents(file_type);
CREATE INDEX IF NOT EXISTS documents_upload_time_idx ON public.documents(upload_time DESC);


-- =============================================
-- PROCESSING JOBS TABLE
-- Tracks each stage of the AI processing pipeline.
-- One document can have multiple jobs (one per pipeline stage).
-- =============================================
CREATE TABLE IF NOT EXISTS public.processing_jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     UUID NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
    job_type        TEXT NOT NULL
                        CHECK (job_type IN (
                            'parsing', 'ocr', 'knowledge_extraction',
                            'ontology_update', 'graph_build',
                            'embedding_generation', 'summarization',
                            'compliance_analysis'
                        )),
    status          TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    execution_time  FLOAT,       -- Duration in seconds
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS processing_jobs_document_id_idx ON public.processing_jobs(document_id);
CREATE INDEX IF NOT EXISTS processing_jobs_status_idx      ON public.processing_jobs(status);


-- =============================================
-- ROW LEVEL SECURITY (RLS)
-- Enable RLS so users can only see their own data.
-- Service role key (used by backend) bypasses RLS.
-- =============================================
ALTER TABLE public.users         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.documents     ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.processing_jobs ENABLE ROW LEVEL SECURITY;

-- Users can read/update their own profile
CREATE POLICY "users_own_profile" ON public.users
    FOR ALL USING (auth.uid() = id);

-- Users can CRUD their own documents
CREATE POLICY "users_own_documents" ON public.documents
    FOR ALL USING (auth.uid() = user_id);

-- Users can read processing jobs for their documents
CREATE POLICY "users_own_processing_jobs" ON public.processing_jobs
    FOR SELECT USING (
        document_id IN (
            SELECT id FROM public.documents WHERE user_id = auth.uid()
        )
    );


-- =============================================
-- STORAGE BUCKET
-- Create the documents storage bucket if it doesn't exist.
-- Run this separately if needed.
-- =============================================
-- INSERT INTO storage.buckets (id, name, public)
-- VALUES ('documents', 'documents', false)
-- ON CONFLICT (id) DO NOTHING;


-- =============================================
-- VERIFICATION 
-- After running, verify tables were created:
-- =============================================
-- SELECT table_name FROM information_schema.tables
-- WHERE table_schema = 'public'
-- ORDER BY table_name;
