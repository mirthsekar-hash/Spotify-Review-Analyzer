-- Spotify Review Discovery Engine — initial schema (Phase 1.2)
-- Run in Supabase SQL Editor: https://supabase.com/dashboard → SQL → New query

CREATE EXTENSION IF NOT EXISTS vector;

-- ---------------------------------------------------------------------------
-- Core tables
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source TEXT NOT NULL CHECK (source IN ('playstore', 'appstore', 'reddit')),
    text TEXT NOT NULL,
    rating SMALLINT CHECK (rating IS NULL OR (rating >= 1 AND rating <= 5)),
    review_date TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}',
    content_hash TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    analyzed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS review_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_id UUID UNIQUE NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
    sentiment TEXT CHECK (sentiment IN ('positive', 'negative', 'neutral', 'mixed')),
    primary_problem TEXT,
    recommendation_complaint BOOLEAN NOT NULL DEFAULT false,
    user_goal TEXT,
    listening_behavior TEXT,
    user_segment TEXT,
    discovery_challenge TEXT,
    confidence_score REAL CHECK (confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS themes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    theme_name TEXT UNIQUE NOT NULL,
    frequency INT NOT NULL DEFAULT 0,
    impact_score REAL,
    representative_review_ids UUID[] NOT NULL DEFAULT '{}',
    affected_segments TEXT[] NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS segments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    segment_name TEXT UNIQUE NOT NULL,
    size INT NOT NULL DEFAULT 0,
    listening_goals JSONB NOT NULL DEFAULT '[]',
    discovery_behavior JSONB NOT NULL DEFAULT '[]',
    top_frustrations JSONB NOT NULL DEFAULT '[]',
    recommendation_trust_score REAL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS root_causes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    root_cause TEXT UNIQUE NOT NULL,
    frequency INT NOT NULL DEFAULT 0,
    supporting_evidence_ids UUID[] NOT NULL DEFAULT '{}',
    affected_segments TEXT[] NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS unmet_needs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    need TEXT UNIQUE NOT NULL,
    frequency INT NOT NULL DEFAULT 0,
    opportunity_score REAL,
    supporting_review_ids UUID[] NOT NULL DEFAULT '{}',
    suggested_ai_solutions JSONB NOT NULL DEFAULT '[]',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_id UUID UNIQUE NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
    embedding vector(768) NOT NULL,
    model TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS theme_reviews (
    theme_id UUID NOT NULL REFERENCES themes(id) ON DELETE CASCADE,
    review_id UUID NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
    PRIMARY KEY (theme_id, review_id)
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL CHECK (status IN ('running', 'success', 'partial', 'failed')),
    stats JSONB NOT NULL DEFAULT '{}'
);

-- Future: interview validation (Phase 4.4)
CREATE TABLE IF NOT EXISTS interview_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    insight TEXT NOT NULL,
    linked_theme_id UUID REFERENCES themes(id) ON DELETE SET NULL,
    validation_pct REAL,
    confidence_score REAL,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Indexes
-- ---------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_reviews_source ON reviews(source);
CREATE INDEX IF NOT EXISTS idx_reviews_analyzed ON reviews(analyzed_at);
CREATE INDEX IF NOT EXISTS idx_reviews_content_hash ON reviews(content_hash);
CREATE INDEX IF NOT EXISTS idx_analysis_segment ON review_analysis(user_segment);
CREATE INDEX IF NOT EXISTS idx_analysis_review_id ON review_analysis(review_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started ON pipeline_runs(started_at DESC);

CREATE INDEX IF NOT EXISTS idx_embeddings_vector
    ON embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- ---------------------------------------------------------------------------
-- Vector similarity search (RAG)
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION match_reviews(
    query_embedding vector(768),
    match_count INT DEFAULT 15
)
RETURNS TABLE (review_id UUID, similarity FLOAT)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.review_id,
        1 - (e.embedding <=> query_embedding) AS similarity
    FROM embeddings e
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
