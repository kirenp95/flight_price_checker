"""Unit tests and property-based tests for the formatter module."""

import datetime

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from flysafair_checker.formatter import (
    format_flight,
    format_results,
    parse_formatted_flight,
)
from flysafair_checker.models import FlightResult


class TestFormatFlight:
    """Tests for format_flight function."""

    def test_basic_format(self):
        flight = FlightResult("FA201", "06:30", "07:40", 1299)
        result = format_flight(flight)
        assert result == "FA201  06:30 → 07:40  R1,299"

    def test_large_price_with_commas(self):
        flight = FlightResult("FA305", "14:00", "15:10", 12500)
        result = format_flight(flight)
        assert "R12,500" in result

    def test_small_price_no_comma(self):
        flight = FlightResult("FA100", "08:00", "09:00", 499)
        result = format_flight(flight)
        assert "R499" in result

    def test_contains_all_fields(self):
        flight = FlightResult("FA201", "06:30", "07:40", 1299)
        result = format_flight(flight)
        assert "FA201" in result
        assert "06:30" in result
        assert "07:40" in result
        assert "1,299" in result


class TestParseFormattedFlight:
    """Tests for parse_formatted_flight function."""

    def test_round_trip(self):
        flight = FlightResult("FA201", "06:30", "07:40", 1299)
        parsed = parse_formatted_flight(format_flight(flight))
        assert parsed == flight

    def test_parse_basic_line(self):
        result = parse_formatted_flight("FA201  06:30 → 07:40  R1,299")
        assert result.flight_number == "FA201"
        assert result.departure_time == "06:30"
        assert result.arrival_time == "07:40"
        assert result.price == 1299

    def test_invalid_format_raises_error(self):
        with pytest.raises(ValueError, match="Cannot parse"):
            parse_formatted_flight("not a flight line")

    def test_empty_string_raises_error(self):
        with pytest.raises(ValueError):
            parse_formatted_flight("")


class TestFormatResults:
    """Tests for format_results function."""

    def test_empty_results_shows_no_flights(self):
        result = format_results([], ("DUR", "JNB"), datetime.date(2025, 8, 15))
        assert "No flights found" in result

    def test_header_contains_route_and_date(self):
        flights = [FlightResult("FA201", "06:30", "07:40", 1299)]
        result = format_results(flights, ("DUR", "JNB"), datetime.date(2025, 8, 15))
        assert "DUR" in result
        assert "JNB" in result
        assert "2025-08-15" in result

    def test_flight_count_displayed(self):
        flights = [
            FlightResult("FA201", "06:30", "07:40", 1299),
            FlightResult("FA203", "10:00", "11:10", 999),
        ]
        result = format_results(flights, ("DUR", "JNB"), datetime.date(2025, 8, 15))
        assert "2 flight(s) found" in result

    def test_results_sorted_by_price(self):
        flights = [
            FlightResult("FA201", "06:30", "07:40", 1500),
            FlightResult("FA203", "10:00", "11:10", 800),
            FlightResult("FA205", "14:00", "15:10", 1200),
        ]
        result = format_results(flights, ("DUR", "JNB"), datetime.date(2025, 8, 15))
        lines = result.strip().split("\n")
        flight_lines = [l for l in lines if l.startswith("FA")]
        assert "FA203" in flight_lines[0]
        assert "FA205" in flight_lines[1]
        assert "FA201" in flight_lines[2]


# Hypothesis strategies for generating valid FlightResult objects
flight_numbers = st.builds(
    lambda n: f"FA{n:03d}",
    st.integers(min_value=100, max_value=999),
)

hh_mm_times = st.builds(
    lambda h, m: f"{h:02d}:{m:02d}",
    st.integers(min_value=0, max_value=23),
    st.integers(min_value=0, max_value=59),
)

flight_results_strategy = st.builds(
    FlightResult,
    flight_number=flight_numbers,
    departure_time=hh_mm_times,
    arrival_time=hh_mm_times,
    price=st.integers(min_value=1, max_value=99999),
)


# Feature: flysafair-price-checker, Property 4: Formatted flight contains all fields
class TestFormattedFlightContainsAllFields:
    """Property test: for any valid FlightResult, format_flight output contains all fields.

    **Validates: Requirements 4.1, 7.2**
    """

    @given(flight=flight_results_strategy)
    @settings(max_examples=100)
    def test_formatted_flight_contains_all_fields(self, flight: FlightResult):
        """For any valid FlightResult, format_flight output contains flight_number,
        departure_time, arrival_time, and price as substrings."""
        result = format_flight(flight)

        assert flight.flight_number in result, (
            f"flight_number {flight.flight_number!r} not found in {result!r}"
        )
        assert flight.departure_time in result, (
            f"departure_time {flight.departure_time!r} not found in {result!r}"
        )
        assert flight.arrival_time in result, (
            f"arrival_time {flight.arrival_time!r} not found in {result!r}"
        )
        assert str(flight.price) in result.replace(",", ""), (
            f"price {flight.price} not found in {result!r}"
        )

# Strategies for format_results arguments
route_strategy = st.sampled_from([("DUR", "JNB"), ("JNB", "DUR")])

future_dates = st.builds(
    lambda d: datetime.date(2025, 8, 15) + datetime.timedelta(days=d),
    st.integers(min_value=0, max_value=365),
)

flight_result_lists = st.lists(flight_results_strategy, min_size=0, max_size=20)


# Feature: flysafair-price-checker, Property 5: Results sorted by price ascending
class TestResultsSortedByPriceAscending:
    """Property test: for any list of FlightResult objects, formatted results are ordered
    by price ascending.

    **Validates: Requirements 4.2**
    """

    @given(
        flights=flight_result_lists,
        route=route_strategy,
        date=future_dates,
    )
    @settings(max_examples=100)
    def test_results_sorted_by_price_ascending(
        self,
        flights: list[FlightResult],
        route: tuple[str, str],
        date: datetime.date,
    ):
        """For any list of FlightResult objects, format_results output has prices
        in ascending order."""
        output = format_results(flights, route, date)

        if not flights:
            assert "No flights found" in output
            return

        # Extract flight lines from the output and parse prices
        lines = output.strip().split("\n")
        prices = []
        for line in lines:
            try:
                parsed = parse_formatted_flight(line)
                prices.append(parsed.price)
            except ValueError:
                continue  # Skip header/summary lines

        assert len(prices) == len(flights), (
            f"Expected {len(flights)} flight lines but found {len(prices)}"
        )

        for i in range(len(prices) - 1):
            assert prices[i] <= prices[i + 1], (
                f"Prices not sorted: {prices[i]} > {prices[i + 1]} at index {i}"
            )



# Feature: flysafair-price-checker, Property 6: Results header contains route, date, and flight count
class TestResultsHeaderContainsMetadata:
    """Property test: for any list of FlightResult objects, route tuple, and date,
    format_results output contains origin, destination, date string, and correct flight count.

    **Validates: Requirements 4.3, 4.4**
    """

    @given(
        flights=flight_result_lists,
        route=route_strategy,
        date=future_dates,
    )
    @settings(max_examples=100)
    def test_results_header_contains_route_date_and_flight_count(
        self,
        flights: list[FlightResult],
        route: tuple[str, str],
        date: datetime.date,
    ):
        """For any list of FlightResult objects, route, and date, format_results output
        contains the origin airport code, destination airport code, the formatted date
        string, and the correct count of flights."""
        output = format_results(flights, route, date)
        origin, destination = route
        date_str = date.strftime("%Y-%m-%d")

        # Header must contain origin, destination, and date
        assert origin in output, (
            f"Origin {origin!r} not found in output"
        )
        assert destination in output, (
            f"Destination {destination!r} not found in output"
        )
        assert date_str in output, (
            f"Date {date_str!r} not found in output"
        )

        # Flight count must be correct
        if not flights:
            assert "No flights found" in output, (
                "Expected 'No flights found' for empty results"
            )
        else:
            expected_count = f"{len(flights)} flight(s) found"
            assert expected_count in output, (
                f"Expected count {expected_count!r} not found in output"
            )


# Feature: flysafair-price-checker, Property 7: FlightResult format/parse round-trip
class TestFlightResultFormatParseRoundTrip:
    """Property test: for any valid FlightResult, parse_formatted_flight(format_flight(flight))
    equals the original.

    **Validates: Requirements 7.3**
    """

    @given(flight=flight_results_strategy)
    @settings(max_examples=100)
    def test_flight_result_format_parse_roundtrip(self, flight: FlightResult):
        """For any valid FlightResult, formatting and then parsing back produces
        a FlightResult equal to the original."""
        formatted = format_flight(flight)
        parsed = parse_formatted_flight(formatted)
        assert parsed == flight, (
            f"Round-trip failed: original={flight!r}, formatted={formatted!r}, parsed={parsed!r}"
        )
