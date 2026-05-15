from __future__ import annotations

import time
from typing import Any

import structlog
from prometheus_client import CollectorRegistry, Counter

log = structlog.get_logger()


class Metrics:
    def __init__(self, registry: CollectorRegistry | None = None) -> None:
        self._registry = registry or CollectorRegistry()
        self._counters: dict[str, Counter] = {}

    def _counter(self, name: str, doc: str) -> Counter:
        if name not in self._counters:
            self._counters[name] = Counter(
                name, doc, ["project"], registry=self._registry
            )
        return self._counters[name]

    @property
    def registry(self) -> CollectorRegistry:
        return self._registry

    def inc(self, name: str, project: str, amount: int = 1) -> None:
        counters = {
            "events_appended": ("substrate_events_appended_total", "Events appended"),
            "claims_acquired": ("substrate_claims_acquired_total", "Claims acquired"),
            "claims_expired": ("substrate_claims_expired_total", "Claims expired"),
            "claims_stolen": ("substrate_claims_stolen_total", "Claims stolen"),
            "claims_released": ("substrate_claims_released_total", "Claims released"),
            "transitions_accepted": (
                "substrate_transitions_accepted_total",
                "Transitions accepted",
            ),
            "transitions_rejected": (
                "substrate_transitions_rejected_total",
                "Transitions rejected",
            ),
            "idempotency_collisions": (
                "substrate_idempotency_collisions_total",
                "Idempotency key collisions",
            ),
            "expected_seq_mismatches": (
                "substrate_expected_seq_mismatches_total",
                "Expected event_seq mismatches",
            ),
            "replay_drift_count": (
                "substrate_replay_drift_total",
                "Replay drift detections",
            ),
            "links_created": ("substrate_links_created_total", "Links created"),
            "links_removed": ("substrate_links_removed_total", "Links removed"),
            "work_items_created": (
                "substrate_work_items_created_total",
                "Work items created",
            ),
            "workflows_registered": (
                "substrate_workflows_registered_total",
                "Workflows registered",
            ),
            "hooks_dispatched": (
                "substrate_hooks_dispatched_total",
                "Hooks dispatched",
            ),
            "hooks_succeeded": (
                "substrate_hooks_succeeded_total",
                "Hooks succeeded",
            ),
            "hooks_failed": (
                "substrate_hooks_failed_total",
                "Hooks failed",
            ),
            "hooks_dead_lettered": (
                "substrate_hooks_dead_lettered_total",
                "Hooks dead-lettered",
            ),
            "validators_succeeded": (
                "substrate_validators_succeeded_total",
                "Validators succeeded",
            ),
            "validators_failed": (
                "substrate_validators_failed_total",
                "Validators failed",
            ),
            "validators_timed_out": (
                "substrate_validators_timed_out_total",
                "Validators timed out",
            ),
            "validators_near_timeout": (
                "substrate_validators_near_timeout_total",
                "Validators near timeout (>= 80% of threshold)",
            ),
            "escalations": (
                "substrate_escalations_total",
                "Escalations",
            ),
            "recurrence_fires_total": (
                "substrate_recurrence_fires_total",
                "Recurrence fires",
            ),
            "recurrence_fires_skipped": (
                "substrate_recurrence_fires_skipped_total",
                "Recurrence fires skipped (catch-up policy)",
            ),
            "recurrence_rules_registered": (
                "substrate_recurrence_rules_registered_total",
                "Recurrence rules registered",
            ),
        }
        if name in counters:
            metric_name, doc = counters[name]
            self._counter(metric_name, doc).labels(project=project).inc(amount)
        else:
            log.warning("metrics.unknown_counter", name=name)


def log_operation(
    project: str,
    operation: str,
    outcome: str,
    *,
    work_item_id: str | None = None,
    actor_id: str | None = None,
    duration: float | None = None,
    **kwargs: Any,
) -> None:
    event = {
        "project_id": project,
        "operation": operation,
        "outcome": outcome,
        **({"work_item_id": work_item_id} if work_item_id else {}),
        **({"actor_id": actor_id} if actor_id else {}),
        **({"duration_s": round(duration, 4)} if duration is not None else {}),
        **kwargs,
    }
    if outcome == "error":
        log.error("substrate.operation", **event)
    elif outcome == "rejected":
        log.warning("substrate.operation", **event)
    else:
        log.info("substrate.operation", **event)


class OpTimer:
    def __init__(self, project: str, operation: str) -> None:
        self._project = project
        self._operation = operation
        self._start = time.monotonic()

    def elapsed(self) -> float:
        return time.monotonic() - self._start

    def log(
        self,
        outcome: str,
        *,
        work_item_id: str | None = None,
        actor_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        log_operation(
            self._project,
            self._operation,
            outcome,
            work_item_id=work_item_id,
            actor_id=actor_id,
            duration=self.elapsed(),
            **kwargs,
        )
