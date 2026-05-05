CREATE UNIQUE INDEX idx_events_one_escalated ON events (work_item_id) WHERE transition = 'escalated';
