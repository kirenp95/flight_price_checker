"""Parser for FlySafair flight search responses."""

import json
import re

from bs4 import BeautifulSoup

from flysafair_checker.models import FlightResult, ParseError

# Patterns for extracting flight data
_TIME_RE = re.compile(r"^\d{2}:\d{2}$")
_FLIGHT_NUM_RE = re.compile(r"^FA\d+$")
_PRICE_RE = re.compile(r"R?\s*([\d,.\s]+)")

# Markers that indicate the response is a FlySafair flight search page
_FLYSAFAIR_MARKERS = [
    "flysafair",
    "FlySafair",
    "flight",
    "DepartureStation",
    "ArrivalStation",
]

# CSS selectors / class patterns commonly used for flight result elements
_FLIGHT_CARD_SELECTORS = [
    "[class*='flight']",
    "[class*='Flight']",
    "[class*='result']",
    "[class*='Result']",
    "[class*='fare']",
    "[class*='Fare']",
    "[class*='journey']",
    "[class*='Journey']",
    "[class*='segment']",
    "[class*='Segment']",
    "[class*='option']",
    "[class*='Option']",
    "[data-flight]",
    ".flight-row",
    ".flight-card",
    ".fare-card",
]


def parse_flights(raw_response: str) -> list[FlightResult]:
    """Parse FlySafair HTML/JSON response into a list of FlightResult objects.

    Attempts to extract flight data from the response by:
    1. Checking for the Sabre ezyCommerce API JSON format (routes/flights)
    2. Checking for embedded JSON flight data in script tags
    3. Parsing HTML flight card elements

    Args:
        raw_response: Raw HTML/JSON response string from FlySafair.

    Returns:
        List of FlightResult objects. Empty list if no flights are found
        on a valid FlySafair page.

    Raises:
        ParseError: If the response format is unexpected or cannot be parsed.
    """
    if not raw_response or not raw_response.strip():
        raise ParseError("Empty response received.")

    # Try API JSON format first (routes -> flights structure)
    api_flights = _try_parse_api_json(raw_response)
    if api_flights is not None:
        return api_flights

    # Try legacy JSON (in case the response is pure JSON with old format)
    flights = _try_parse_json(raw_response)
    if flights is not None:
        return flights

    # Parse as HTML
    try:
        soup = BeautifulSoup(raw_response, "html.parser")
    except Exception as exc:
        raise ParseError(f"Failed to parse response as HTML: {exc}") from exc

    # Verify this looks like a FlySafair page
    if not _is_flysafair_page(soup, raw_response):
        raise ParseError(
            "Response does not appear to be a FlySafair flight search page."
        )

    # Try to extract flights from embedded JSON in script tags
    flights = _extract_from_scripts(soup)
    if flights is not None:
        return flights

    # Try to extract flights from HTML flight cards
    flights = _extract_from_html(soup)
    if flights is not None:
        return flights

    # Page looks like FlySafair but no flight data found — likely no flights available
    return []


# ---------------------------------------------------------------------------
# Sabre ezyCommerce API format parsing (primary path)
# ---------------------------------------------------------------------------

def _try_parse_api_json(raw_response: str) -> list[FlightResult] | None:
    """Try to parse the response as a Sabre ezyCommerce SearchShop API JSON response.

    Returns a list of FlightResult if successful, or None if the response
    doesn't match the API format.
    """
    stripped = raw_response.strip()
    if not stripped.startswith("{"):
        return None

    try:
        data = json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        return None

    if not isinstance(data, dict) or "routes" not in data:
        return None

    routes = data["routes"]
    if not isinstance(routes, list):
        return None

    results: list[FlightResult] = []
    for route in routes:
        if not isinstance(route, dict):
            continue
        flights = route.get("flights")
        if not isinstance(flights, list):
            continue
        for flight in flights:
            parsed = _api_flight_to_result(flight)
            if parsed is not None:
                results.append(parsed)

    return results


def _api_flight_to_result(flight: dict) -> FlightResult | None:
    """Convert a single API flight object to a FlightResult.

    Supports two formats:
    1. SearchShop: carrierCode, flightNumber, departureDate, arrivalDate, fares[]
    2. FindLowestFare (legacy): date, pricePerPassenger, isSoldOut, key
    """
    if not isinstance(flight, dict):
        return None

    # --- SearchShop format (has carrierCode + flightNumber) ---
    if "carrierCode" in flight or "departureDate" in flight:
        if flight.get("soldOut", False):
            return None

        # Extract price from fares array — cheapest non-sold-out fare
        price: int | None = None
        fares = flight.get("fares")
        if isinstance(fares, list):
            available_prices: list[float] = []
            for fare in fares:
                if isinstance(fare, dict) and not fare.get("soldOut", False):
                    fare_price = fare.get("price")
                    if fare_price is not None:
                        try:
                            available_prices.append(float(fare_price))
                        except (ValueError, TypeError):
                            continue
            if available_prices:
                price = int(round(min(available_prices)))

        # Fall back to pricePerPassenger if no fares array
        if price is None:
            price_raw = flight.get("pricePerPassenger")
            if price_raw is not None:
                try:
                    price = int(round(float(price_raw)))
                except (ValueError, TypeError):
                    pass

        if price is None or price <= 0:
            return None

        # Flight number: carrierCode + flightNumber (e.g. "FA668")
        carrier = flight.get("carrierCode", "FA")
        flt_num = flight.get("flightNumber", "")
        flight_number = f"{carrier}{flt_num}" if flt_num else "FA-UNK"

        # Departure time from departureDate ISO string
        dep_str = flight.get("departureDate", "")
        dep_time = _extract_time_from_iso(dep_str) if dep_str else None
        if dep_time is None:
            return None

        # Extract date from departureDate (e.g. "2026-04-06T06:00:00")
        dep_date_str = dep_str[:10] if len(dep_str) >= 10 else ""

        # Arrival time from arrivalDate ISO string
        arr_str = flight.get("arrivalDate", "")
        arr_time = _extract_time_from_iso(arr_str) if arr_str else "--:--"

        return FlightResult(
            flight_number=flight_number,
            departure_time=dep_time,
            arrival_time=arr_time,
            price=price,
            flight_date=dep_date_str,
        )

    # --- Legacy FindLowestFare format ---
    if flight.get("isSoldOut", False):
        return None

    price_raw = flight.get("pricePerPassenger")
    if price_raw is None:
        return None
    try:
        price_legacy = int(round(float(price_raw)))
    except (ValueError, TypeError):
        return None
    if price_legacy <= 0:
        return None

    date_str = flight.get("date")
    if not date_str or not isinstance(date_str, str):
        return None
    dep_time = _extract_time_from_iso(date_str)
    if dep_time is None:
        return None

    # Extract date from the date field (e.g. "2026-04-06T06:00:00")
    legacy_date_str = date_str[:10] if len(date_str) >= 10 else ""

    key = flight.get("key", "")
    fare_class = flight.get("fareClass", "")
    fare_basis = flight.get("fareBasisCode", "")

    flight_id = ""
    if isinstance(key, str) and ":" in key:
        flight_id = key.split(":")[0]

    if flight_id:
        flight_number = f"FA{flight_id}"
    elif fare_basis:
        flight_number = f"FA-{fare_basis}"
    elif fare_class:
        flight_number = f"FA-{fare_class}"
    else:
        flight_number = "FA-UNK"

    return FlightResult(
        flight_number=flight_number,
        departure_time=dep_time,
        arrival_time="--:--",
        price=price_legacy,
        flight_date=legacy_date_str,
    )


def _extract_time_from_iso(iso_str: str) -> str | None:
    """Extract HH:MM time from an ISO datetime string like '2026-04-06T06:00:00'."""
    match = re.search(r"T(\d{2}):(\d{2})", iso_str)
    if match:
        return f"{match.group(1)}:{match.group(2)}"
    return None


# ---------------------------------------------------------------------------
# Legacy JSON format parsing (backward-compatible)
# ---------------------------------------------------------------------------

def _try_parse_json(raw_response: str) -> list[FlightResult] | None:
    """Try to parse the response as a JSON object containing flight data.

    Returns a list of FlightResult if successful, or None if the response
    is not JSON or doesn't contain flight data.
    """
    stripped = raw_response.strip()
    if not (stripped.startswith("{") or stripped.startswith("[")):
        return None

    try:
        data = json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        return None

    return _extract_flights_from_json(data)


def _extract_flights_from_json(data: object) -> list[FlightResult] | None:
    """Extract FlightResult objects from a parsed JSON structure.

    Handles both a list of flight objects and a dict with a flights key.
    Returns None if the structure doesn't contain recognisable flight data.
    """
    flights_list: list[dict] | None = None

    if isinstance(data, list):
        flights_list = data
    elif isinstance(data, dict):
        # Look for a key that contains flight data
        for key in ("flights", "Flights", "results", "Results", "data", "Data"):
            if key in data and isinstance(data[key], list):
                flights_list = data[key]
                break

    if flights_list is None:
        return None

    results: list[FlightResult] = []
    for item in flights_list:
        flight = _json_item_to_flight(item)
        if flight is not None:
            results.append(flight)

    return results if results or flights_list else None


def _json_item_to_flight(item: object) -> FlightResult | None:
    """Convert a single JSON object to a FlightResult, or None if not possible."""
    if not isinstance(item, dict):
        return None

    flight_number = _get_json_field(item, ("flightNumber", "FlightNumber", "flight_number", "number"))
    departure = _get_json_field(item, ("departureTime", "DepartureTime", "departure_time", "departure"))
    arrival = _get_json_field(item, ("arrivalTime", "ArrivalTime", "arrival_time", "arrival"))
    price_raw = _get_json_field(item, ("price", "Price", "fare", "Fare", "amount", "Amount"))

    if not all([flight_number, departure, arrival, price_raw is not None]):
        return None

    try:
        price = _parse_price(str(price_raw))
    except (ValueError, TypeError):
        return None

    dep_time = _normalize_time(str(departure))
    arr_time = _normalize_time(str(arrival))

    if dep_time is None or arr_time is None:
        return None

    return FlightResult(
        flight_number=str(flight_number),
        departure_time=dep_time,
        arrival_time=arr_time,
        price=price,
    )


def _get_json_field(data: dict, keys: tuple[str, ...]) -> object | None:
    """Return the value for the first matching key found in data."""
    for key in keys:
        if key in data:
            return data[key]
    return None


# ---------------------------------------------------------------------------
# HTML parsing (backward-compatible)
# ---------------------------------------------------------------------------

def _is_flysafair_page(soup: BeautifulSoup, raw_response: str) -> bool:
    """Check whether the response looks like a FlySafair page."""
    text_lower = raw_response.lower()
    return any(marker.lower() in text_lower for marker in _FLYSAFAIR_MARKERS)


def _extract_from_scripts(soup: BeautifulSoup) -> list[FlightResult] | None:
    """Look for flight data embedded in <script> tags as JSON."""
    for script in soup.find_all("script"):
        if not script.string:
            continue

        # Look for JSON arrays or objects in script content
        for match in re.finditer(r'(\[{.*?}\]|\{"flights".*?\})', script.string, re.DOTALL):
            try:
                data = json.loads(match.group(0))
                result = _extract_flights_from_json(data)
                if result is not None:
                    return result
            except (json.JSONDecodeError, ValueError):
                continue

    return None


def _extract_from_html(soup: BeautifulSoup) -> list[FlightResult] | None:
    """Extract flight data from HTML elements using CSS selectors."""
    # Try each selector to find flight card elements
    for selector in _FLIGHT_CARD_SELECTORS:
        try:
            cards = soup.select(selector)
        except Exception:
            continue

        if not cards:
            continue

        results: list[FlightResult] = []
        for card in cards:
            flight = _parse_flight_card(card)
            if flight is not None:
                results.append(flight)

        if results:
            return results

    return None


def _parse_flight_card(card) -> FlightResult | None:
    """Try to extract a FlightResult from an HTML element."""
    text = card.get_text(separator=" ", strip=True)

    # Try to find flight number (FA followed by digits)
    flight_num_match = re.search(r"\b(FA\d{2,5})\b", text)
    if not flight_num_match:
        return None

    # Try to find times (HH:MM pattern)
    times = re.findall(r"\b(\d{2}:\d{2})\b", text)
    if len(times) < 2:
        return None

    # Try to find price (R followed by digits, or just digits near currency context)
    price_match = re.search(r"R\s*([\d,.\s]+)", text)
    if not price_match:
        # Try bare number patterns
        price_match = re.search(r"([\d,]+)\s*(?:ZAR|zar|Rand|rand)?", text)
    if not price_match:
        return None

    try:
        price = _parse_price(price_match.group(1))
    except (ValueError, TypeError):
        return None

    return FlightResult(
        flight_number=flight_num_match.group(1),
        departure_time=times[0],
        arrival_time=times[1],
        price=price,
    )


# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------

def _parse_price(raw: str) -> int:
    """Parse a price string into an integer (ZAR whole rands)."""
    cleaned = re.sub(r"[R\s,]", "", str(raw))
    if "." in cleaned:
        cleaned = cleaned.split(".")[0]
    if not cleaned or not cleaned.isdigit():
        raise ValueError(f"Cannot parse price: {raw!r}")
    value = int(cleaned)
    if value <= 0:
        raise ValueError(f"Price must be positive, got {value}")
    return value


def _normalize_time(raw: str) -> str | None:
    """Normalize a time string to HH:MM format. Returns None if invalid."""
    raw = raw.strip()
    if _TIME_RE.match(raw):
        return raw
    match = re.search(r"(\d{2}:\d{2})", raw)
    if match:
        return match.group(1)
    return None