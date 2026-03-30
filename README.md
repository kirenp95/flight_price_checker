# flysafair_checker

A Python package that fetches live FlySafair flight prices for routes between
Durban (DUR), Johannesburg (JNB), and Cape Town (CPT). It scrapes the FlySafair
website, parses available flights, and returns structured price and schedule data.

## Installation

From the `flight_price_checker/` directory:

```
pip install -e .
```

## CLI Usage

```
python -m flysafair_checker dur-jnb 2026-04-13
python -m flysafair_checker cpt-jnb 2026-04-13
python -m flysafair_checker both 2026-04-13
```

Or via the console script:

```
flysafair-checker dur-jnb 2026-04-13
```

## Module Usage

```python
import datetime
from flysafair_checker.fetcher import fetch_flights
from flysafair_checker.parser import parse_flights
from flysafair_checker.validators import validate_route, validate_date

origin, dest = validate_route("dur-jnb")
date = validate_date("2026-04-13")

raw = fetch_flights(origin, dest, date)
flights = parse_flights(raw)

for flight in flights:
    print(f"{flight.flight_number}  {flight.departure_time} -> {flight.arrival_time}  R{flight.price}")
```

## Supported Routes

- `dur-jnb` -- Durban to Johannesburg
- `jnb-dur` -- Johannesburg to Durban
- `cpt-jnb` -- Cape Town to Johannesburg
- `jnb-cpt` -- Johannesburg to Cape Town
- `cpt-dur` -- Cape Town to Durban
- `dur-cpt` -- Durban to Cape Town
- `both` -- fetches all routes

## Dependencies

- requests
- beautifulsoup4

## Dev Dependencies

- hypothesis
- pytest

## Running Tests

```
pip install -e ".[dev]"
pytest
```

## Project Structure

- `models.py` -- Data classes and route definitions
- `validators.py` -- Input validation for routes and dates
- `fetcher.py` -- HTTP requests to the FlySafair website
- `parser.py` -- HTML parsing and flight data extraction
- `formatter.py` -- Terminal output formatting
- `__main__.py` -- CLI entry point
