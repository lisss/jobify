from __future__ import annotations

from functools import lru_cache

import geonamescache

# Shown first when they match the query
REMOTE_LOCATIONS = [
    "Remote",
    "Remote worldwide",
    "Remote US",
    "Remote Europe",
    "Remote UK",
    "Remote EMEA",
    "Remote APAC",
    "Remote Americas",
    "Hybrid",
    "Worldwide",
    "Anywhere",
]

# Minimum population to count as a "main" city
MIN_CITY_POPULATION = 100_000

# Exclude from location typeahead
EXCLUDED_COUNTRY_CODES = {"RU", "BY"}
EXCLUDED_COUNTRY_NAMES = {"russia", "belarus"}


def _is_excluded_label(label: str) -> bool:
    lower = label.strip().lower()
    if lower in EXCLUDED_COUNTRY_NAMES:
        return True
    if "," in label:
        country = label.rsplit(",", 1)[-1].strip().lower()
        if country in EXCLUDED_COUNTRY_NAMES:
            return True
    return False


@lru_cache(maxsize=1)
def _location_catalog() -> list[tuple[str, int]]:
    """Return (label, rank_weight) pairs. Higher weight = more important."""
    gc = geonamescache.GeonamesCache()
    countries = {
        code: meta
        for code, meta in gc.get_countries().items()
        if code not in EXCLUDED_COUNTRY_CODES
        and (meta.get("name") or "").strip().lower() not in EXCLUDED_COUNTRY_NAMES
    }
    country_name = {code: meta["name"] for code, meta in countries.items()}

    entries: dict[str, int] = {}

    # Remote / flexible work options — highest priority weight
    for i, label in enumerate(REMOTE_LOCATIONS):
        entries[label] = 10_000_000 - i

    # Countries (useful as broad location filters)
    for meta in countries.values():
        name = (meta.get("name") or "").strip()
        if name and not _is_excluded_label(name):
            entries[name] = max(entries.get(name, 0), int(meta.get("population") or 0) // 10)

    # Capitals get a boost even if small
    for meta in countries.values():
        capital = (meta.get("capital") or "").strip()
        ccode = meta.get("iso") or ""
        if not capital:
            continue
        country = country_name.get(ccode, ccode)
        label = f"{capital}, {country}" if country else capital
        if _is_excluded_label(label):
            continue
        entries[label] = max(entries.get(label, 0), 500_000)
        entries[capital] = max(entries.get(capital, 0), 400_000)

    # Main cities by population
    for city in gc.get_cities().values():
        ccode = city.get("countrycode") or ""
        if ccode in EXCLUDED_COUNTRY_CODES:
            continue
        pop = int(city.get("population") or 0)
        if pop < MIN_CITY_POPULATION:
            continue
        name = (city.get("name") or "").strip()
        if not name:
            continue
        country = country_name.get(ccode, ccode)
        label = f"{name}, {country}" if country else name
        if _is_excluded_label(label):
            continue
        # Prefer "City, Country" form; also index bare city name with slightly lower weight
        entries[label] = max(entries.get(label, 0), pop)
        entries[name] = max(entries.get(name, 0), pop - 1)

    return sorted(entries.items(), key=lambda item: (-item[1], item[0]))


def suggest_city_locations(q: str = "", limit: int = 40) -> list[str]:
    """Typeahead over remote options + major world cities/countries."""
    needle = q.strip().lower()
    catalog = _location_catalog()
    limit = max(1, min(limit, 80))

    if not needle:
        # Lead with remote options, then fill the rest with largest cities
        remotes = [label for label, _ in catalog if label in set(REMOTE_LOCATIONS)]
        cities = [label for label, _ in catalog if "," in label]
        return (remotes + cities)[:limit]

    starts: list[tuple[int, str]] = []
    contains: list[tuple[int, str]] = []

    for label, weight in catalog:
        if _is_excluded_label(label):
            continue
        lower = label.lower()
        if lower.startswith(needle):
            starts.append((weight, label))
        elif needle in lower:
            contains.append((weight, label))

    # Prefer "City, Country" over bare "City", and prefix over substring
    def sort_key(item: tuple[int, str]) -> tuple:
        weight, label = item
        has_country = 0 if "," in label else 1
        return (has_country, -weight, label)

    starts.sort(key=sort_key)
    contains.sort(key=sort_key)

    seen: set[str] = set()
    bare_covered: set[str] = set()
    results: list[str] = []
    for _, label in starts + contains:
        lower = label.lower()
        if lower in seen:
            continue
        if "," in label:
            bare_covered.add(label.split(",", 1)[0].strip().lower())
        elif lower in bare_covered:
            continue
        seen.add(lower)
        results.append(label)
        if len(results) >= limit:
            break
    return results
