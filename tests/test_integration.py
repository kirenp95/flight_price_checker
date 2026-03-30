"""Integration tests that hit the real FlySafair API.

Run with: pytest -m integration
Skip with: pytest -m "not integration"
"""

import datetime

import pytest

from flysafair_checker.fetcher import fetch_flights
from flysafair_checker.parser import parse_flights
from flysafair_checker.models import FlightResult


pytestmark = pytest.mark.integration


def _assert_valid_flights(flights: list[FlightResult]) -> None:
    """Shared assertions for a list of parsed flights."""
    assert len(flights) > 0

    for flight in flights:
        assert isinstance(flight, FlightResult)
        assert flight.flight_number.startswith("FA")
        assert flight.price > 0
        assert ":" in flight.departure_time
        assert ":" in flight.arrival_time


class TestLiveFetch:
    """Tests that fetch real data from FlySafair for today's date."""

    def test_dur_jnb_returns_flights(self):
        """Fetch DUR->JNB for today and verify we get valid results."""
        date = datetime.date.today() + datetime.timedelta(days=7)
        raw = fetch_flights("DUR", "JNB", date)

        assert raw is not None
        assert len(raw) > 0

        flights = parse_flights(raw)
        _assert_valid_flights(flights)

    def test_jnb_cpt_returns_flights(self):
        """Fetch JNB->CPT for today and verify we get valid results."""
        date = datetime.date.today() + datetime.timedelta(days=7)
        raw = fetch_flights("JNB", "CPT", date)

        assert raw is not None
        assert len(raw) > 0

        flights = parse_flights(raw)
        _assert_valid_flights(flights)