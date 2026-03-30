"""Unit tests for the fetcher module."""

import datetime
from unittest.mock import patch, MagicMock

import pytest
import requests

from flysafair_checker.fetcher import fetch_flights, FLYSAFAIR_SEARCH_SHOP_URL, REQUEST_TIMEOUT
from flysafair_checker.models import FetchError


class TestFetchFlightsRetryOnTimeout:
    """Verify that fetch_flights retries exactly once on timeout (Req 6.2)."""

    @patch("flysafair_checker.fetcher.requests.post")
    def test_retries_once_on_timeout_then_raises_fetch_error(self, mock_post):
        """Two consecutive timeouts should result in exactly 2 calls and a FetchError."""
        mock_post.side_effect = requests.exceptions.Timeout("timed out")

        with pytest.raises(FetchError, match="timed out after retrying"):
            fetch_flights("DUR", "JNB", datetime.date(2025, 8, 15))

        assert mock_post.call_count == 2

    @patch("flysafair_checker.fetcher.requests.post")
    def test_succeeds_on_retry_after_first_timeout(self, mock_post):
        """First call times out, second call succeeds — should return the response."""
        mock_response = MagicMock()
        mock_response.text = '{"routes": []}'
        mock_response.raise_for_status = MagicMock()

        mock_post.side_effect = [
            requests.exceptions.Timeout("timed out"),
            mock_response,
        ]

        result = fetch_flights("DUR", "JNB", datetime.date(2025, 8, 15))

        assert result == '{"routes": []}'
        assert mock_post.call_count == 2


class TestFetchFlightsConnectionFailure:
    """Verify that connection errors raise FetchError immediately (Req 3.3)."""

    @patch("flysafair_checker.fetcher.requests.post")
    def test_connection_error_raises_fetch_error(self, mock_post):
        mock_post.side_effect = requests.exceptions.ConnectionError("no connection")

        with pytest.raises(FetchError, match="Unable to connect"):
            fetch_flights("DUR", "JNB", datetime.date(2025, 8, 15))

        # Connection errors should NOT retry — only one call
        assert mock_post.call_count == 1


class TestFetchFlightsSuccess:
    """Verify that a successful fetch returns the raw response string (Req 3.1)."""

    @patch("flysafair_checker.fetcher.requests.post")
    def test_successful_fetch_returns_response_text(self, mock_post):
        mock_response = MagicMock()
        mock_response.text = '{"routes": [{"flights": []}]}'
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = fetch_flights("JNB", "DUR", datetime.date(2025, 9, 1))

        assert result == '{"routes": [{"flights": []}]}'
        assert mock_post.call_count == 1
        mock_response.raise_for_status.assert_called_once()
