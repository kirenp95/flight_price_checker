"""Formatter module for displaying flight results in a human-readable format."""

import datetime
import re

from flysafair_checker.models import FlightResult


def format_flight(flight: FlightResult, show_date: bool = False) -> str:
    """Format a single FlightResult as a human-readable line.

    Format: "FA000  06:30 → 07:40  R1,299"
    With show_date: "2026-04-06  FA000  06:30 → 07:40  R1,299"
    """
    date_prefix = f"{flight.flight_date}  " if show_date and flight.flight_date else ""
    return f"{date_prefix}{flight.flight_number}  {flight.departure_time} → {flight.arrival_time}  R{flight.price:,}"


def parse_formatted_flight(text: str) -> FlightResult:
    """Parse a formatted flight line back into a FlightResult.

    Expects format: "FA000  06:30 → 07:40  R1,299"
    Also handles date-prefixed format: "2026-04-06  FA000  06:30 → 07:40  R1,299"
    """
    # Try date-prefixed format first
    date_pattern = r"^(\d{4}-\d{2}-\d{2})\s{2}(\S+)\s{2}(\d{2}:\d{2})\s→\s([\d-]{2}:[\d-]{2})\s{2}R([\d,]+)$"
    date_match = re.match(date_pattern, text.strip())
    if date_match:
        flight_date = date_match.group(1)
        flight_number = date_match.group(2)
        departure_time = date_match.group(3)
        arrival_time = date_match.group(4)
        price = int(date_match.group(5).replace(",", ""))
        return FlightResult(
            flight_number=flight_number,
            departure_time=departure_time,
            arrival_time=arrival_time,
            price=price,
            flight_date=flight_date,
        )

    # Standard format without date
    pattern = r"^(\S+)\s{2}(\d{2}:\d{2})\s→\s([\d-]{2}:[\d-]{2})\s{2}R([\d,]+)$"
    match = re.match(pattern, text.strip())
    if not match:
        raise ValueError(f"Cannot parse flight line: {text!r}")
    flight_number = match.group(1)
    departure_time = match.group(2)
    arrival_time = match.group(3)
    price = int(match.group(4).replace(",", ""))
    return FlightResult(
        flight_number=flight_number,
        departure_time=departure_time,
        arrival_time=arrival_time,
        price=price,
    )


def format_results(
    results: list[FlightResult],
    route: tuple[str, str],
    date: datetime.date,
    end_date: datetime.date | None = None,
) -> str:
    """Format flight results as a human-readable string with header and summary.

    Results are sorted by price ascending before formatting.
    When end_date is provided, shows a date range header and includes
    flight dates in each line.
    """
    origin, destination = route
    date_str = date.strftime("%Y-%m-%d")
    is_range = end_date is not None and end_date != date
    lines: list[str] = []

    if is_range:
        end_str = end_date.strftime("%Y-%m-%d")
        lines.append(f"Flights from {origin} to {destination} from {date_str} to {end_str}")
    else:
        lines.append(f"Flights from {origin} to {destination} on {date_str}")
    lines.append("")

    if not results:
        lines.append("No flights found.")
        return "\n".join(lines)

    sorted_results = sorted(results, key=lambda f: f.price)

    for flight in sorted_results:
        lines.append(format_flight(flight, show_date=is_range))

    lines.append("")
    lines.append(f"{len(sorted_results)} flight(s) found.")

    return "\n".join(lines)
