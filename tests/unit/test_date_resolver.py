"""Unit tests for the M2 date resolver."""

from datetime import datetime, timedelta

from backend.modules.m2_temporal.date_resolver import DateResolver


def test_none_date_returns_no_date_label():
    resolved, status = DateResolver().validate_and_fix(None)
    assert resolved is None
    assert "sem data" in status


def test_date_before_1800_rejected():
    resolved, status = DateResolver().validate_and_fix(datetime(1750, 6, 1))
    assert resolved is None
    assert "1800" in status


def test_unix_epoch_rejected():
    resolved, status = DateResolver().validate_and_fix(datetime(1970, 1, 1))
    assert resolved is None
    assert "epoch" in status


def test_future_date_rejected():
    future = datetime.utcnow() + timedelta(days=365)
    resolved, status = DateResolver().validate_and_fix(future)
    assert resolved is None
    assert "futuro" in status


def test_reasonable_past_date_accepted():
    date = datetime(2010, 5, 3)
    resolved, status = DateResolver().validate_and_fix(date)
    assert resolved == date
    assert status == "válida"


def test_estimate_decade_from_clues():
    assert DateResolver().estimate_decade(["tinha um walkman nos anos 80"]) == "1980s"
    assert DateResolver().estimate_decade(["nada relevante"]) is None


def test_sort_events_places_dated_before_undated():
    class E:
        def __init__(self, id, date):
            self.id = id
            self.event_date = date

    events = [E(1, None), E(2, datetime(2000, 1, 1)), E(3, datetime(1990, 1, 1))]
    ordered = DateResolver().sort_events(events)
    assert [e.id for e in ordered] == [3, 2, 1]
