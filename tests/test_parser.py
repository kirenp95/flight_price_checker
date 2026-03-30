"""Unit tests for the FlySafair response parser."""

import json

import pytest

from flysafair_checker.models import FlightResult, ParseError
from flysafair_checker.parser import parse_flights


class TestParseFlightsEmpty:
    """Tests for empty/missing response handling."""

    def test_empty_string_raises_parse_error(self):
        with pytest.raises(ParseError):
            parse_flights("")

    def test_whitespace_only_raises_parse_error(self):
        with pytest.raises(ParseError):
            parse_flights("   \n  ")


class TestParseFlightsInvalidFormat:
    """Tests for unexpected response formats."""

    def test_random_text_raises_parse_error(self):
        with pytest.raises(ParseError):
            parse_flights("This is just random text with no relevant data.")

    def test_html_without_flysafair_markers_raises_parse_error(self):
        html = "<html><body><p>Hello world</p></body></html>"
        with pytest.raises(ParseError):
            parse_flights(html)

    def test_non_flight_html_raises_parse_error(self):
        html = "<html><body><h1>Some Other Airline</h1></body></html>"
        with pytest.raises(ParseError):
            parse_flights(html)


class TestParseFlightsNoResults:
    """Tests for valid FlySafair pages with no flights."""

    def test_flysafair_page_no_flights_returns_empty(self):
        html = """
        <html>
        <head><title>FlySafair - Flight Search</title></head>
        <body>
            <div class="no-results">
                <p>No flights available for the selected date.</p>
            </div>
        </body>
        </html>
        """
        result = parse_flights(html)
        assert result == []

    def test_flysafair_page_with_departure_station_no_flights(self):
        html = """
        <html>
        <body>
            <input name="DepartureStation" value="DUR" />
            <input name="ArrivalStation" value="JNB" />
            <div class="search-results">
                <p>No flights found</p>
            </div>
        </body>
        </html>
        """
        result = parse_flights(html)
        assert result == []


class TestParseFlightsFromHTML:
    """Tests for parsing flight data from HTML elements."""

    def test_parse_single_flight_card(self):
        html = """
        <html>
        <head><title>FlySafair Flight Search</title></head>
        <body>
            <div class="flight-result">
                <span class="flight-number">FA201</span>
                <span class="departure">06:30</span>
                <span class="arrival">07:40</span>
                <span class="price">R1,299</span>
            </div>
        </body>
        </html>
        """
        results = parse_flights(html)
        assert len(results) == 1
        assert results[0].flight_number == "FA201"
        assert results[0].departure_time == "06:30"
        assert results[0].arrival_time == "07:40"
        assert results[0].price == 1299

    def test_parse_multiple_flight_cards(self):
        html = """
        <html>
        <head><title>FlySafair</title></head>
        <body>
            <div class="flight-result">
                <span>FA201</span>
                <span>06:30</span> - <span>07:40</span>
                <span>R1,299</span>
            </div>
            <div class="flight-result">
                <span>FA203</span>
                <span>10:15</span> - <span>11:25</span>
                <span>R899</span>
            </div>
        </body>
        </html>
        """
        results = parse_flights(html)
        assert len(results) == 2
        assert results[0].flight_number == "FA201"
        assert results[1].flight_number == "FA203"
        assert results[1].price == 899

    def test_parse_flight_with_fare_class(self):
        html = """
        <html>
        <head><title>FlySafair</title></head>
        <body>
            <div class="fare-card">
                <div>FA301 06:00 07:10 R1,500</div>
            </div>
        </body>
        </html>
        """
        results = parse_flights(html)
        assert len(results) == 1
        assert results[0].flight_number == "FA301"
        assert results[0].price == 1500


class TestParseFlightsFromJSON:
    """Tests for parsing flight data from JSON responses."""

    def test_parse_json_array(self):
        data = [
            {
                "flightNumber": "FA201",
                "departureTime": "06:30",
                "arrivalTime": "07:40",
                "price": 1299,
            },
            {
                "flightNumber": "FA203",
                "departureTime": "10:15",
                "arrivalTime": "11:25",
                "price": 899,
            },
        ]
        results = parse_flights(json.dumps(data))
        assert len(results) == 2
        assert results[0].flight_number == "FA201"
        assert results[1].price == 899

    def test_parse_json_with_flights_key(self):
        data = {
            "flights": [
                {
                    "FlightNumber": "FA201",
                    "DepartureTime": "06:30",
                    "ArrivalTime": "07:40",
                    "Price": 1299,
                }
            ]
        }
        results = parse_flights(json.dumps(data))
        assert len(results) == 1
        assert results[0].flight_number == "FA201"

    def test_parse_json_empty_flights_returns_empty(self):
        data = {"flights": []}
        results = parse_flights(json.dumps(data))
        assert results == []

    def test_parse_json_with_string_price(self):
        data = [
            {
                "flightNumber": "FA201",
                "departureTime": "06:30",
                "arrivalTime": "07:40",
                "price": "1,299",
            }
        ]
        results = parse_flights(json.dumps(data))
        assert len(results) == 1
        assert results[0].price == 1299


class TestParseFlightsFromEmbeddedJSON:
    """Tests for parsing flight data from JSON embedded in HTML script tags."""

    def test_parse_embedded_json_in_script(self):
        flights_json = json.dumps([
            {
                "flightNumber": "FA201",
                "departureTime": "06:30",
                "arrivalTime": "07:40",
                "price": 1299,
            }
        ])
        html = f"""
        <html>
        <head><title>FlySafair</title></head>
        <body>
            <script>var flights = {flights_json};</script>
        </body>
        </html>
        """
        results = parse_flights(html)
        assert len(results) == 1
        assert results[0].flight_number == "FA201"

import re

from hypothesis import given, settings, assume
from hypothesis.strategies import (
    composite,
    integers,
    lists,
    sampled_from,
    text,
)


@composite
def flight_json_dicts(draw):
    """Generate a valid flight JSON dict with realistic FlySafair data."""
    flight_num = "FA" + str(draw(integers(min_value=100, max_value=999)))
    dep_hour = draw(integers(min_value=0, max_value=23))
    dep_min = draw(integers(min_value=0, max_value=59))
    arr_hour = draw(integers(min_value=0, max_value=23))
    arr_min = draw(integers(min_value=0, max_value=59))
    price = draw(integers(min_value=1, max_value=50000))

    dep_time = f"{dep_hour:02d}:{dep_min:02d}"
    arr_time = f"{arr_hour:02d}:{arr_min:02d}"

    # Vary the JSON key naming convention
    key_style = draw(sampled_from(["camel", "pascal", "snake"]))
    if key_style == "camel":
        return {
            "flightNumber": flight_num,
            "departureTime": dep_time,
            "arrivalTime": arr_time,
            "price": price,
        }
    elif key_style == "pascal":
        return {
            "FlightNumber": flight_num,
            "DepartureTime": dep_time,
            "ArrivalTime": arr_time,
            "Price": price,
        }
    else:
        return {
            "flight_number": flight_num,
            "departure_time": dep_time,
            "arrival_time": arr_time,
            "price": price,
        }


@composite
def flysafair_json_responses(draw):
    """Generate a valid FlySafair-like JSON response string containing flights."""
    flights = draw(lists(flight_json_dicts(), min_size=1, max_size=10))

    # Vary the response structure: plain array or wrapped in a dict
    wrapper = draw(sampled_from(["array", "flights_key", "results_key"]))
    if wrapper == "array":
        return json.dumps(flights)
    elif wrapper == "flights_key":
        return json.dumps({"flights": flights})
    else:
        return json.dumps({"results": flights})


@composite
def flysafair_html_responses(draw):
    """Generate a valid FlySafair-like HTML response with flight cards."""
    flights = draw(lists(flight_json_dicts(), min_size=1, max_size=10))

    cards = []
    for f in flights:
        # Extract values regardless of key style
        fn = f.get("flightNumber") or f.get("FlightNumber") or f.get("flight_number")
        dep = f.get("departureTime") or f.get("DepartureTime") or f.get("departure_time")
        arr = f.get("arrivalTime") or f.get("ArrivalTime") or f.get("arrival_time")
        price = f.get("price") or f.get("Price")
        cards.append(
            f'<div class="flight-result">'
            f"<span>{fn}</span> "
            f"<span>{dep}</span> - <span>{arr}</span> "
            f"<span>R{price:,}</span>"
            f"</div>"
        )

    card_html = "\n".join(cards)
    return (
        f"<html><head><title>FlySafair</title></head>"
        f"<body>{card_html}</body></html>"
    )


_TIME_PATTERN = re.compile(r"^\d{2}:\d{2}$")


# Feature: flysafair-price-checker, Property 3: Parsed flights contain all required fields
# Validates: Requirements 3.2, 7.1
class TestParsedFlightsHaveAllFieldsProperty:
    """Property test: every FlightResult from parse_flights has non-empty
    flight_number, valid HH:MM times, and positive price."""

    @given(response=flysafair_json_responses())
    @settings(max_examples=100)
    def test_json_parsed_flights_have_all_required_fields(self, response: str):
        """**Validates: Requirements 3.2, 7.1**"""
        results = parse_flights(response)
        assume(len(results) > 0)

        for flight in results:
            # Non-empty flight number
            assert isinstance(flight.flight_number, str)
            assert len(flight.flight_number) > 0

            # Valid HH:MM departure time
            assert isinstance(flight.departure_time, str)
            assert _TIME_PATTERN.match(flight.departure_time), (
                f"departure_time {flight.departure_time!r} is not HH:MM"
            )

            # Valid HH:MM arrival time
            assert isinstance(flight.arrival_time, str)
            assert _TIME_PATTERN.match(flight.arrival_time), (
                f"arrival_time {flight.arrival_time!r} is not HH:MM"
            )

            # Positive integer price
            assert isinstance(flight.price, int)
            assert flight.price > 0

    @given(response=flysafair_html_responses())
    @settings(max_examples=100)
    def test_html_parsed_flights_have_all_required_fields(self, response: str):
        """**Validates: Requirements 3.2, 7.1**"""
        results = parse_flights(response)
        assume(len(results) > 0)

        for flight in results:
            assert isinstance(flight.flight_number, str)
            assert len(flight.flight_number) > 0
            assert isinstance(flight.departure_time, str)
            assert _TIME_PATTERN.match(flight.departure_time), (
                f"departure_time {flight.departure_time!r} is not HH:MM"
            )
            assert isinstance(flight.arrival_time, str)
            assert _TIME_PATTERN.match(flight.arrival_time), (
                f"arrival_time {flight.arrival_time!r} is not HH:MM"
            )
            assert isinstance(flight.price, int)
            assert flight.price > 0


# Feature: flysafair-price-checker, Property 8: Invalid responses raise ParseError
# Validates: Requirements 6.1
class TestInvalidResponseRaisesParseErrorProperty:
    """Property test: random/malformed strings passed to parse_flights raise
    ParseError rather than returning corrupt data."""

    @given(response=text())
    @settings(max_examples=100)
    def test_random_strings_raise_parse_error(self, response: str):
        """**Validates: Requirements 6.1**

        Any arbitrary string that is not a valid FlySafair response should
        raise ParseError. We filter out strings containing FlySafair markers
        or valid JSON flight data.
        """
        lower = response.lower()
        flysafair_markers = [
            "flysafair",
            "flight",
            "departurestation",
            "arrivalstation",
        ]
        assume(not any(marker in lower for marker in flysafair_markers))

        stripped = response.strip()
        assume(not (stripped.startswith("{") or stripped.startswith("[")))

        with pytest.raises(ParseError):
            parse_flights(response)
