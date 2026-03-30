"""Unit tests for the CLI module."""

import datetime
from unittest.mock import patch

import pytest

from flysafair_checker.cli import main, parse_args
from flysafair_checker.models import FetchError, FlightResult, ParseError


class TestParseArgs:
    """Tests for parse_args argument parsing."""

    def test_dur_jnb_route_accepted(self):
        result = parse_args(["dur-jnb", "2025-09-01"])
        assert result.route == "dur-jnb"
        assert result.date == "2025-09-01"

    def test_jnb_dur_route_accepted(self):
        result = parse_args(["jnb-dur", "2025-09-01"])
        assert result.route == "jnb-dur"
        assert result.date == "2025-09-01"

    def test_both_route_accepted(self):
        result = parse_args(["both", "2025-09-01"])
        assert result.route == "both"
        assert result.date == "2025-09-01"

    def test_invalid_route_raises_system_exit(self):
        with pytest.raises(SystemExit):
            parse_args(["blq-fco", "2025-09-01"])

    def test_no_arguments_raises_system_exit(self):
        with pytest.raises(SystemExit):
            parse_args([])

    def test_missing_date_raises_system_exit(self):
        with pytest.raises(SystemExit):
            parse_args(["dur-jnb"])

    def test_to_argument_accepted(self):
        result = parse_args(["dur-jnb", "2025-09-01", "--to", "2025-09-05"])
        assert result.route == "dur-jnb"
        assert result.date == "2025-09-01"
        assert result.end_date == "2025-09-05"

    def test_to_argument_defaults_to_none(self):
        result = parse_args(["dur-jnb", "2025-09-01"])
        assert result.end_date is None


class TestMain:
    """Tests for main entry point and error exit codes."""

    @patch("flysafair_checker.cli.fetch_flights")
    @patch("flysafair_checker.cli.parse_flights")
    @patch("flysafair_checker.cli.format_results")
    def test_successful_run_returns_zero(self, mock_format, mock_parse, mock_fetch):
        future = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()
        mock_fetch.return_value = "<html></html>"
        mock_parse.return_value = [FlightResult("FA201", "06:00", "07:10", 799)]
        mock_format.return_value = "formatted output"

        exit_code = main(["dur-jnb", future])
        assert exit_code == 0

    @patch("flysafair_checker.cli.fetch_flights")
    @patch("flysafair_checker.cli.parse_flights")
    @patch("flysafair_checker.cli.format_results")
    def test_both_route_calls_fetch_twice(self, mock_format, mock_parse, mock_fetch):
        future = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()
        mock_fetch.return_value = "<html></html>"
        mock_parse.return_value = []
        mock_format.return_value = "no flights"

        exit_code = main(["both", future])
        assert exit_code == 0
        assert mock_fetch.call_count == 6

    def test_invalid_date_returns_one(self):
        exit_code = main(["dur-jnb", "not-a-date"])
        assert exit_code == 1

    def test_past_date_returns_one(self):
        past = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        exit_code = main(["dur-jnb", past])
        assert exit_code == 1

    @patch("flysafair_checker.cli.fetch_flights", side_effect=FetchError("timeout"))
    def test_fetch_error_returns_one(self, mock_fetch):
        future = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()
        exit_code = main(["dur-jnb", future])
        assert exit_code == 1

    @patch("flysafair_checker.cli.fetch_flights", return_value="<html></html>")
    @patch("flysafair_checker.cli.parse_flights", side_effect=ParseError("bad html"))
    def test_parse_error_returns_one(self, mock_parse, mock_fetch):
        future = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()
        exit_code = main(["dur-jnb", future])
        assert exit_code == 1

    def test_end_date_before_start_date_returns_one(self):
        start = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()
        end = (datetime.date.today() + datetime.timedelta(days=3)).isoformat()
        exit_code = main(["dur-jnb", start, "--to", end])
        assert exit_code == 1

    @patch("flysafair_checker.cli.fetch_flights")
    @patch("flysafair_checker.cli.parse_flights")
    @patch("flysafair_checker.cli.format_results")
    def test_date_range_passes_end_date(self, mock_format, mock_parse, mock_fetch):
        start = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()
        end = (datetime.date.today() + datetime.timedelta(days=10)).isoformat()
        mock_fetch.return_value = "<html></html>"
        mock_parse.return_value = [FlightResult("FA201", "06:00", "07:10", 799)]
        mock_format.return_value = "formatted output"

        exit_code = main(["dur-jnb", start, "--to", end])
        assert exit_code == 0
        # Verify end_date was passed to fetch_flights
        call_kwargs = mock_fetch.call_args
        assert call_kwargs[1]["end_date"] == datetime.date.fromisoformat(end)
