"""HTTP fetcher for FlySafair flight data with retry logic."""

import datetime

import requests

from flysafair_checker.models import FetchError

FLYSAFAIR_API_HOST = "https://api-production-safair-booksecure.ezyflight.se"
FLYSAFAIR_SEARCH_SHOP_URL = f"{FLYSAFAIR_API_HOST}/api/v1/Availability/SearchShop"

REQUEST_TIMEOUT = 15  # seconds

DEFAULT_HEADERS = {
    "Content-Type": "application/json",
    "Tenant-Identifier": "f0fb7f8d0f5e6fc0df2506194e74e94367f1a351de7aee12685e5a1da70464ff",
    "AppContext": "ibe",
    "X-ClientVersion": "0.5.3963",
    "Origin": "https://www.flysafair.co.za",
    "Referer": "https://www.flysafair.co.za/",
}


def fetch_flights(origin: str, destination: str, date: datetime.date, end_date: datetime.date | None = None) -> str:
    """Fetch raw JSON response from FlySafair SearchShop API.

    Makes an HTTP POST request to the Sabre ezyCommerce API with the given
    route and date parameters. Retries once on timeout.

    Args:
        origin: Origin airport code (e.g. "DUR").
        destination: Destination airport code (e.g. "JNB").
        date: Travel date (start date for range queries).
        end_date: Optional end date for date range queries. If omitted,
            fetches flights for a single date.

    Returns:
        Raw JSON response body as a string.

    Raises:
        FetchError: On connection failure or repeated timeout.
    """
    payload = {
        "languageCode": "en-GB",
        "currency": "ZAR",
        "passengers": [{"code": "ADT", "count": 1}],
        "routes": [
            {
                "fromAirport": origin,
                "toAirport": destination,
                "startDate": date.strftime("%Y-%m-%d"),
                "endDate": (end_date or date).strftime("%Y-%m-%d"),
            }
        ],
    }

    last_error: Exception | None = None

    for attempt in range(2):  # initial attempt + one retry
        try:
            response = requests.post(
                FLYSAFAIR_SEARCH_SHOP_URL,
                headers=DEFAULT_HEADERS,
                json=payload,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            return response.text
        except requests.exceptions.Timeout as exc:
            last_error = exc
            if attempt == 0:
                # Retry once on timeout
                continue
        except requests.exceptions.ConnectionError as exc:
            raise FetchError(
                "Unable to connect to FlySafair. "
                "Please check your internet connection and try again later."
            ) from exc
        except requests.exceptions.HTTPError as exc:
            raise FetchError(
                f"FlySafair returned an error (HTTP {exc.response.status_code}). "
                "Please try again later."
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise FetchError(
                f"Failed to retrieve flight data: {exc}"
            ) from exc

    # If we get here, both attempts timed out
    raise FetchError(
        "Request to FlySafair timed out after retrying. "
        "Please try again later."
    ) from last_error
