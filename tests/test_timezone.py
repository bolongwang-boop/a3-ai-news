from datetime import datetime, timedelta

from src.timezone import UTC_TZ, SYDNEY_TZ, get_week_range_sydney, is_within_sydney_range, utc_to_sydney_str


class TestGetWeekRangeSydney:
    def test_returns_utc_datetimes(self):
        from_utc, to_utc = get_week_range_sydney(7)
        assert from_utc.tzinfo is not None
        assert to_utc.tzinfo is not None

    def test_from_is_before_to(self):
        from_utc, to_utc = get_week_range_sydney(7)
        assert from_utc < to_utc

    def test_range_spans_approximately_n_days(self):
        from_utc, to_utc = get_week_range_sydney(7)
        delta = to_utc - from_utc
        # Should be between 7 and 8 days (from midnight N days ago to now)
        assert 7 <= delta.days <= 8

    def test_from_is_midnight_sydney(self):
        from_utc, _ = get_week_range_sydney(7)
        sydney_dt = from_utc.astimezone(SYDNEY_TZ)
        assert sydney_dt.hour == 0
        assert sydney_dt.minute == 0
        assert sydney_dt.second == 0


class TestUtcToSydneyStr:
    def test_includes_timezone_abbreviation(self):
        utc_dt = datetime(2026, 2, 20, 0, 0, 0, tzinfo=UTC_TZ)
        result = utc_to_sydney_str(utc_dt)
        # February is AEDT (daylight saving)
        assert "AEDT" in result or "AEST" in result

    def test_format_is_readable(self):
        utc_dt = datetime(2026, 7, 1, 0, 0, 0, tzinfo=UTC_TZ)
        result = utc_to_sydney_str(utc_dt)
        # Should contain date and time components
        assert "2026-07-01" in result


class TestIsWithinSydneyRange:
    def test_within_range(self):
        now = datetime.now(UTC_TZ)
        from_utc = now - timedelta(days=7)
        to_utc = now
        published = now - timedelta(days=3)
        assert is_within_sydney_range(published, from_utc, to_utc) is True

    def test_before_range(self):
        now = datetime.now(UTC_TZ)
        from_utc = now - timedelta(days=7)
        to_utc = now
        published = now - timedelta(days=10)
        assert is_within_sydney_range(published, from_utc, to_utc) is False

    def test_after_range(self):
        now = datetime.now(UTC_TZ)
        from_utc = now - timedelta(days=7)
        to_utc = now - timedelta(days=1)
        published = now
        assert is_within_sydney_range(published, from_utc, to_utc) is False

    def test_naive_datetime_treated_as_utc(self):
        now = datetime.now(UTC_TZ)
        from_utc = now - timedelta(days=7)
        to_utc = now
        # Naive datetime (no tzinfo) should be treated as UTC
        published = (now - timedelta(days=3)).replace(tzinfo=None)
        assert is_within_sydney_range(published, from_utc, to_utc) is True

    def test_boundary_inclusive(self):
        now = datetime.now(UTC_TZ)
        from_utc = now - timedelta(days=7)
        to_utc = now
        # Exactly at boundaries should be included
        assert is_within_sydney_range(from_utc, from_utc, to_utc) is True
        assert is_within_sydney_range(to_utc, from_utc, to_utc) is True
