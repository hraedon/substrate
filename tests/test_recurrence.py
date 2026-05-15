from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from substrate._errors import ErrorCode, SubstrateError
from substrate._recurrence import compute_next_fire, validate_schedule, validate_template
from substrate._types import RecurrenceRule


class TestComputeNextFire:
    def test_interval_minutes(self):
        start = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
        next_fire = compute_next_fire(
            "interval", "PT5M", "UTC", start, None, None,
        )
        assert next_fire == start + timedelta(minutes=5)

    def test_interval_hours(self):
        start = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
        next_fire = compute_next_fire(
            "interval", "PT1H", "UTC", start, None, None,
        )
        assert next_fire == start + timedelta(hours=1)

    def test_interval_days(self):
        start = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
        next_fire = compute_next_fire(
            "interval", "P1D", "UTC", start, None, None,
        )
        assert next_fire == start + timedelta(days=1)

    def test_interval_respects_end_at(self):
        start = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
        end = start + timedelta(minutes=3)
        next_fire = compute_next_fire(
            "interval", "PT5M", "UTC", start, None, end,
        )
        assert next_fire is None

    def test_interval_with_last_fired(self):
        start = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
        last = start + timedelta(minutes=5)
        next_fire = compute_next_fire(
            "interval", "PT5M", "UTC", start, last, None,
        )
        assert next_fire == start + timedelta(minutes=10)

    def test_rrule_daily_first_occurrence_is_start(self):
        start = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
        next_fire = compute_next_fire(
            "rrule", "FREQ=DAILY", "UTC", start, None, None,
        )
        assert next_fire == start

    def test_rrule_next_after_first(self):
        start = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
        last = start
        next_fire = compute_next_fire(
            "rrule", "FREQ=DAILY", "UTC", start, last, None,
        )
        assert next_fire == start + timedelta(days=1)

    def test_rrule_with_end_at_before_start(self):
        start = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
        end = start - timedelta(hours=1)
        next_fire = compute_next_fire(
            "rrule", "FREQ=DAILY", "UTC", start, None, end,
        )
        assert next_fire is None

    def test_unknown_schedule_kind(self):
        with pytest.raises(SubstrateError) as exc_info:
            compute_next_fire("bogus", "", "UTC", datetime.now(UTC), None, None)
        assert exc_info.value.code == ErrorCode.RECURRENCE_SCHEDULE_INVALID


class TestValidateSchedule:
    def test_valid_interval(self):
        validate_schedule("interval", "PT10M")

    def test_valid_rrule(self):
        validate_schedule("rrule", "FREQ=HOURLY")

    def test_invalid_rrule(self):
        with pytest.raises(SubstrateError) as exc_info:
            validate_schedule("rrule", "not a rrule")
        assert exc_info.value.code == ErrorCode.RECURRENCE_SCHEDULE_INVALID

    def test_invalid_interval(self):
        with pytest.raises(SubstrateError) as exc_info:
            validate_schedule("interval", "xyz")
        assert exc_info.value.code == ErrorCode.RECURRENCE_SCHEDULE_INVALID


class TestValidateTemplate:
    def test_valid(self):
        validate_template({"custom_fields": {}})

    def test_not_dict(self):
        with pytest.raises(SubstrateError) as exc_info:
            validate_template("nope")
        assert exc_info.value.code == ErrorCode.RECURRENCE_TEMPLATE_INVALID


class TestRecurrenceRuleDataclass:
    def test_roundtrip(self):
        rule = RecurrenceRule(
            rule_id=uuid.uuid4(),
            workflow_name="test",
            workflow_version=1,
            work_item_type="feature",
            template={"custom_fields": {}},
            schedule_kind="interval",
            schedule_expr="PT1H",
            timezone="UTC",
            start_at=datetime.now(UTC),
            end_at=None,
            count_remaining=5,
            status="active",
            catchup_policy="fire_once",
            last_fired_at=None,
            next_fire_at=datetime.now(UTC),
            created_by="system",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        d = rule.to_dict()
        restored = RecurrenceRule.from_dict(d)
        assert restored.rule_id == rule.rule_id
        assert restored.workflow_name == rule.workflow_name
        assert restored.status == rule.status
