ALTER TABLE hook_queue DROP CONSTRAINT hook_queue_event_id_fkey;

DROP INDEX IF EXISTS idx_events_actor_id;
DROP INDEX IF EXISTS idx_events_timestamp;
DROP INDEX IF EXISTS idx_events_transition;
DROP INDEX IF EXISTS idx_events_workflow;
DROP INDEX IF EXISTS idx_events_link_type;
DROP INDEX IF EXISTS idx_events_one_escalated;

ALTER TABLE events RENAME TO events_legacy;

CREATE TABLE events (
    event_id UUID NOT NULL,
    work_item_id UUID NOT NULL,
    event_seq INTEGER NOT NULL,
    actor_id TEXT NOT NULL,
    actor_kind TEXT NOT NULL CHECK (actor_kind IN ('agent', 'human', 'system')),
    actor_metadata JSONB,
    key_id TEXT NOT NULL,
    workflow_name TEXT NOT NULL,
    workflow_version INTEGER NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
    transition TEXT,
    payload JSONB,
    payload_canonical_hash BYTEA NOT NULL,
    signature BYTEA NOT NULL,
    canonical_envelope BYTEA,
    PRIMARY KEY (event_id, timestamp),
    UNIQUE (work_item_id, event_seq, timestamp)
) PARTITION BY RANGE (timestamp);

CREATE TABLE events_default PARTITION OF events DEFAULT;

CREATE TABLE events_y2026_m01 PARTITION OF events
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

CREATE TABLE events_y2026_m02 PARTITION OF events
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');

CREATE TABLE events_y2026_m03 PARTITION OF events
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');

CREATE TABLE events_y2026_m04 PARTITION OF events
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');

CREATE TABLE events_y2026_m05 PARTITION OF events
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');

CREATE TABLE events_y2026_m06 PARTITION OF events
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');

CREATE TABLE events_y2026_m07 PARTITION OF events
    FOR VALUES FROM ('2026-07-01') TO ('2026-08-01');

CREATE INDEX idx_events_actor_id ON events (actor_id);
CREATE INDEX idx_events_timestamp ON events (timestamp);
CREATE INDEX idx_events_transition ON events (transition);
CREATE INDEX idx_events_workflow ON events (workflow_name, workflow_version);
CREATE INDEX idx_events_link_type ON events (work_item_id, ((payload)->>'link_type'))
WHERE transition IN ('link_created', 'link_removed');

CREATE UNIQUE INDEX idx_events_one_escalated ON events (work_item_id, timestamp)
WHERE transition = 'escalated';

INSERT INTO events (
    event_id, work_item_id, event_seq, actor_id, actor_kind, actor_metadata,
    key_id, workflow_name, workflow_version, timestamp, transition, payload,
    payload_canonical_hash, signature, canonical_envelope
)
SELECT
    event_id, work_item_id, event_seq, actor_id, actor_kind, actor_metadata,
    key_id, workflow_name, workflow_version, timestamp, transition, payload,
    payload_canonical_hash, signature, canonical_envelope
FROM events_legacy;

DROP TABLE events_legacy;
