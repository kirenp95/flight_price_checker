"""Unit tests and property tests for the validators module."""

import datetime

import pytest
from hypothesis import given, settings, assume
from hypothesis.strategies import text, dates, integers, sampled_from, one_of, just

from flysafair_checker.models import SUPPORTED_ROUTES
from flysafair_checker.validators import validate_date, validate_route


class TestValidateRoute:
    """Tests for validate_route function."""

    def test_dur_jnb_returns_correct_tuple(self):
        assert validate_route("dur-jnb") == ("DUR", "JNB")

    def test_jnb_dur_returns_correct_tuple(self):
        assert validate_route("jnb-dur") == ("JNB", "DUR")

    def test_unsupported_route_raises_value_error(self):
        with pytest.raises(ValueError, match="Unsupported route"):
            validate_route("blq-fco")

    def test_error_message_lists_supported_routes(self):
        with pytest.raises(ValueError, match="dur-jnb") as exc_info:
            validate_route("invalid")
        assert "jnb-dur" in str(exc_info.value)

    def test_empty_string_raises_value_error(self):
        with pytest.raises(ValueError):
            validate_route("")

    def test_uppercase_route_raises_value_error(self):
        with pytest.raises(ValueError):
            validate_route("DUR-JNB")


class TestValidateDate:
    """Tests for validate_date function."""

    def test_future_date_returns_date_object(self):
        future = datetime.date.today() + datetime.timedelta(days=30)
        result = validate_date(future.isoformat())
        assert result == future

    def test_today_is_valid(self):
        today = datetime.date.today()
        result = validate_date(today.isoformat())
        assert result == today

    def test_past_date_raises_value_error(self):
        past = datetime.date.today() - datetime.timedelta(days=1)
        with pytest.raises(ValueError, match="past"):
            validate_date(past.isoformat())

    def test_invalid_format_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid date format"):
            validate_date("15-08-2025")

    def test_error_shows_expected_format(self):
        with pytest.raises(ValueError, match="YYYY-MM-DD"):
            validate_date("not-a-date")

    def test_empty_string_raises_value_error(self):
        with pytest.raises(ValueError):
            validate_date("")

    def test_invalid_calendar_date_raises_value_error(self):
        with pytest.raises(ValueError):
            validate_date("2025-13-01")


# Feature: flysafair-price-checker, Property 1: Route validation correctness
# Validates: Requirements 1.3, 1.4
class TestRouteValidationCorrectnessProperty:
    """Property test: for any string input, validate_route succeeds iff the input
    is a supported route key; errors list supported routes."""

    @given(route=text())
    @settings(max_examples=100)
    def test_route_validation_correctness(self, route: str):
        supported_keys = set(SUPPORTED_ROUTES.keys())

        if route in supported_keys:
            result = validate_route(route)
            assert result == SUPPORTED_ROUTES[route]
        else:
            with pytest.raises(ValueError) as exc_info:
                validate_route(route)
            error_msg = str(exc_info.value)
            for key in supported_keys:
                assert key in error_msg


# Feature: flysafair-price-checker, Property 2: Date validation correctness
# Validates: Requirements 2.1, 2.2
class TestDateValidationCorrectnessProperty:
    """Property test: for any valid future YYYY-MM-DD string, validate_date returns
    the correct date; invalid inputs raise ValueError."""

    @given(date=dates(min_value=datetime.date.today(), max_value=datetime.date(2099, 12, 31)))
    @settings(max_examples=100)
    def test_valid_future_date_returns_correct_date(self, date: datetime.date):
        """Valid current/future dates in YYYY-MM-DD format are accepted and returned correctly."""
        date_str = date.isoformat()
        result = validate_date(date_str)
        assert result == date

    @given(date=dates(min_value=datetime.date(1900, 1, 1), max_value=datetime.date.today() - datetime.timedelta(days=1)))
    @settings(max_examples=100)
    def test_past_date_raises_value_error(self, date: datetime.date):
        """Past dates in valid YYYY-MM-DD format raise ValueError."""
        date_str = date.isoformat()
        with pytest.raises(ValueError, match="past"):
            validate_date(date_str)

    @given(s=text())
    @settings(max_examples=100)
    def test_arbitrary_string_either_valid_or_raises(self, s: str):
        """For any arbitrary string, validate_date either returns a valid future date or raises ValueError."""
        try:
            result = validate_date(s)
            assert isinstance(result, datetime.date)
            assert result >= datetime.date.today()
            assert result.isoformat() == s
        except ValueError:
            pass  # Expected for invalid inputs
