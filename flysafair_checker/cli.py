"""Command-line interface for FlySafair Price Checker."""

import argparse
import sys

from flysafair_checker.fetcher import fetch_flights
from flysafair_checker.formatter import format_results
from flysafair_checker.models import SUPPORTED_ROUTES, FetchError, ParseError
from flysafair_checker.parser import parse_flights
from flysafair_checker.validators import validate_date, validate_route


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments: route (dur-jnb | jnb-dur | both), date (YYYY-MM-DD), optional --to end date."""
    parser = argparse.ArgumentParser(
        description="Check FlySafair flight prices for DUR↔JNB, CPT↔JNB, and CPT↔DUR routes.",
    )
    parser.add_argument(
        "route",
        choices=list(SUPPORTED_ROUTES.keys()) + ["both"],
        help="Route to check (e.g. dur-jnb, cpt-jnb) or 'both' for all routes",
    )
    parser.add_argument(
        "date",
        help="Travel date in YYYY-MM-DD format",
    )
    parser.add_argument(
        "--to",
        dest="end_date",
        default=None,
        help="End date for date range (YYYY-MM-DD). If omitted, fetches single date.",
    )
    return parser.parse_args(args)

def main(args: list[str] | None = None) -> int:
    """Entry point. Returns exit code (0 = success, 1 = error)."""
    try:
        parsed = parse_args(args)
        date = validate_date(parsed.date)

        end_date = None
        if parsed.end_date:
            end_date = validate_date(parsed.end_date)
            if end_date < date:
                raise ValueError(
                    f"End date '{parsed.end_date}' is before start date '{parsed.date}'."
                )

        if parsed.route == "both":
            routes = list(SUPPORTED_ROUTES.items())
        else:
            origin, dest = validate_route(parsed.route)
            routes = [(parsed.route, (origin, dest))]

        for route_key, (origin, dest) in routes:
            raw = fetch_flights(origin, dest, date, end_date=end_date)
            flights = parse_flights(raw)
            output = format_results(flights, (origin, dest), date, end_date=end_date)
            print(output)

    except (ValueError, FetchError, ParseError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0
