"""Input validation for route and date arguments."""

import datetime

from flysafair_checker.models import SUPPORTED_ROUTES


def validate_route(route: str) -> tuple[str, str]:
    """Validate route string.

    Returns (origin, destination) tuple for supported routes.
    Raises ValueError with supported routes listed for invalid input.
    """
    if route in SUPPORTED_ROUTES:
        return SUPPORTED_ROUTES[route]
    supported = ", ".join(SUPPORTED_ROUTES.keys())
    raise ValueError(f"Unsupported route: '{route}'. Supported routes: {supported}")


def validate_date(date_str: str) -> datetime.date:
    """Validate date string in YYYY-MM-DD format.

    Returns datetime.date for valid current or future dates.
    Raises ValueError for invalid format or past dates.
    """
    try:
        date = datetime.date.fromisoformat(date_str)
    except (ValueError, TypeError):
        raise ValueError(
            f"Invalid date format: '{date_str}'. Expected format: YYYY-MM-DD"
        )

    if date < datetime.date.today():
        raise ValueError(
            f"Date '{date_str}' is in the past. Please provide today's date or a future date."
        )

    return date
