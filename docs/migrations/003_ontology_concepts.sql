-- Migration: 003_ontology_concepts.sql
-- Description: Create table for newly discovered ontology concepts

CREATE TABLE IF NOT EXISTS public.ontology_concepts (
    id UUID PRIMARY KEY,
    concept_name TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT,
    confidence FLOAT,
    justification TEXT,
    source_document_id UUID REFERENCES public.documents(id) ON DELETE CASCADE,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    
    -- Ensure we don't get duplicates of the exact same concept name
    CONSTRAINT unique_concept_name UNIQUE (concept_name)
);

-- RLS policies
ALTER TABLE public.ontology_concepts ENABLE ROW LEVEL SECURITY;

-- Allow read access for authenticated users
CREATE POLICY "Allow read access for authenticated users" 
ON public.ontology_concepts FOR SELECT TO authenticated USING (true);

-- Allow service role to manage concepts
CREATE POLICY "Allow service role full access" 
ON public.ontology_concepts USING (auth.role() = 'service_role');
