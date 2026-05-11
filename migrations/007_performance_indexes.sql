CREATE INDEX idx_events_link_type ON events (work_item_id, ((payload)->>'link_type'))
WHERE transition IN ('link_created', 'link_removed');

CREATE INDEX idx_hook_queue_poll ON hook_queue (status, next_retry_at, id)
WHERE status = 'pending';
