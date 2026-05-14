-- Migration 009: GIN index on custom_fields for JSONB containment queries

CREATE INDEX IF NOT EXISTS idx_work_items_custom_fields_gin
    ON work_items_current USING GIN (custom_fields);
