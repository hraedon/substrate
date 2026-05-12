-- Migration 008: add max_retries to hook_dead_letter so requeue preserves retry policy

ALTER TABLE hook_dead_letter ADD COLUMN max_retries INTEGER NOT NULL DEFAULT 3;
