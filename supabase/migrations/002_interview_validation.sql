-- Phase 4.4: interview validation indexes (table created in 001_initial_schema.sql)

CREATE INDEX IF NOT EXISTS idx_interview_insights_theme
    ON interview_insights(linked_theme_id);

CREATE INDEX IF NOT EXISTS idx_interview_insights_created
    ON interview_insights(created_at DESC);
