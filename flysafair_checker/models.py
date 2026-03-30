"""Data models, route constants, and custom exceptions for FlySafair Price Checker."""

from dataclasses import dataclass


@dataclass
class FlightResult:
    """A single flight option with schedule and pricing information."""

    flight_number: str
    departure_time: str  # HH:MM format
    arrival_time: str  # HH:MM format
    price: int  # Price in ZAR (whole rands)
    flight_date: str = ""  # YYYY-MM-DD, extracted from API response


SUPPORTED_ROUTES: dict[str, tuple[str, str]] = {
    "dur-jnb": ("DUR", "JNB"),
    "jnb-dur": ("JNB", "DUR"),
    "cpt-jnb": ("CPT", "JNB"),
    "jnb-cpt": ("JNB", "CPT"),
    "cpt-dur": ("CPT", "DUR"),
    "dur-cpt": ("DUR", "CPT"),
}


class FetchError(Exception):
    """Raised when flight data cannot be retrieved from FlySafair."""


class ParseError(Exception):
    """Raised when the FlySafair response cannot be parsed."""
