"""Query layer over the schema.org datasets, shared by the REST API and the chatbot."""

import json
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from functools import cache, lru_cache
from math import asin, ceil, cos, floor, log2, radians, sin, sqrt
from typing import Any, Literal
from zlib import crc32
from zoneinfo import ZoneInfo

from src.schema_org_tourdata import (
    LICENCE_NAME,
    LICENCE_URL,
    MONUMENTS_CREDIT,
    SCHEMA_DIR,
    TOURDATA_CREDIT,
)

Dataset = Literal["gastronomy", "accommodation", "tours", "monuments", "areas"]
MapDataset = Literal["gastronomy", "events", "tours", "monuments"]
Interest = Literal[
    "kids",
    "rainy_day",
    "accessible",
    "culinary",
    "culture",
    "nature",
    "relaxation",
    "adventure",
    "budget",
    "pets",
]

PLACE_DATASETS = ("gastronomy", "accommodation", "tours", "monuments", "areas")
DEFAULT_RADIUS_KM = 25
MAX_LIMIT = 50
MAX_EVENT_WINDOW_DAYS = 92
MAP_DATASETS = ("gastronomy", "events", "tours", "monuments")
MAP_REGION = "Oberösterreich"
MAP_GRID_DIVISIONS = 12
DEFAULT_MAP_POINTS = 150
MAX_MAP_POINTS = 500
TIMEZONE = ZoneInfo("Europe/Vienna")

# Friendly filters mapped to the TOURDATA feature flags that express them.
INTEREST_FEATURES: dict[str, set[str]] = {
    "kids": {
        "AI_INTEREST_KIDS",
        "OBJECT_FIT_MITKIND",
        "OBJECT_FIT_KINDER",
        "OBJECT_FIT_FAMILIEN",
        "OBJECT_FIT_FAMILIE",
    },
    "rainy_day": {"AI_INTEREST_RAIN", "OBJECT_FIT_WETTERUNABHAENGIG"},
    "accessible": {"AI_INTEREST_ACCESSIBLE", "ROLLSTUHLTAUGLICH"},
    "culinary": {"AI_INTEREST_CULINARY"},
    "culture": {"AI_INTEREST_CULTURE"},
    "nature": {"AI_INTEREST_NATURE"},
    "relaxation": {"AI_INTEREST_RELAXATION"},
    "adventure": {"AI_INTEREST_ADVENTURE"},
    "budget": {"AI_INTEREST_BUDGET", "PRICE_FREE"},
    "pets": {"OBJECT_FIT_HAUSTIERE"},
}

BRIEF_PROPERTIES = {
    "difficulty",
    "distanceMetres",
    "durationSeconds",
    "ascentMetres",
    "roundTrip",
    "trailStatus",
    "notice",
    "locationPrecision",
    "priceFromEuro",
}
SUMMARY_LENGTH = 280

TOURDATA_SOURCE = {
    "provider": TOURDATA_CREDIT,
    "url": "https://datenwartung.tourdata.at/",
    "licence": LICENCE_NAME,
    "licenceUrl": LICENCE_URL,
    "updateFrequency": "Maintained continuously at source; refreshed here when the export is re-run",
}

SOURCES = {
    **dict.fromkeys(("gastronomy", "accommodation", "events", "tours", "areas"), TOURDATA_SOURCE),
    "monuments": {
        "provider": MONUMENTS_CREDIT,
        "url": "https://www.bda.gv.at/service/unterschutzstellung/denkmalverzeichnis/denkmalliste-gemaess-3-dmsg.html",
        "licence": LICENCE_NAME,
        "licenceUrl": LICENCE_URL,
        "note": "Positions come from geocode.at and OpenStreetMap Nominatim; OpenStreetMap-derived positions are ODbL",
        "updateFrequency": "Monument list published periodically by the BDA; refreshed here manually",
    },
    "weather": {
        "provider": "Open-Meteo, GeoSphere Austria model",
        "url": "https://open-meteo.com/en/docs/geosphere-austria-api",
        "licence": LICENCE_NAME,
        "licenceUrl": LICENCE_URL,
        "note": "The free API is for non-commercial use",
        "updateFrequency": "Live on request, cached for one hour",
    },
}


class DataNotBuiltError(RuntimeError):
    """The schema.org files have not been generated yet."""


@dataclass(slots=True)
class Entry:
    id: str
    dataset: str
    node: dict[str, Any]
    latitude: float | None
    longitude: float | None
    title: str
    categories: str
    locality: str
    body: str
    features: frozenset[str]


@dataclass(slots=True)
class Store:
    entries: dict[str, Entry]
    metadata: dict[str, dict[str, Any]]


def fold(text: object) -> str:
    """Lower-case and strip accents so 'Schloß', 'muehle' and 'Mühle' compare sensibly."""
    value = str(text or "").lower().replace("ß", "ss")
    value = value.replace("ä", "a").replace("ö", "o").replace("ü", "u")
    value = value.replace("ae", "a").replace("oe", "o").replace("ue", "u")
    return "".join(c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c))


def where_of(node: dict[str, Any]) -> dict[str, Any]:
    """Events keep their address and position on the nested location."""
    return node.get("location") or node


def identifier_of(node: dict[str, Any]) -> str:
    identifier = node["identifier"]
    return f"heris-{identifier['value']}" if identifier["propertyID"] == "HERIS-ID" else identifier["value"]


def make_entry(dataset: str, node: dict[str, Any]) -> Entry:
    where = where_of(node)
    geo = where.get("geo") or {}
    address = where.get("address") or {}
    areas = " ".join(a["name"] for a in where.get("containedInPlace") or [])
    return Entry(
        id=identifier_of(node),
        dataset=dataset,
        node=node,
        latitude=geo.get("latitude"),
        longitude=geo.get("longitude"),
        title=fold(node.get("name")),
        categories=fold(f"{node.get('keywords', '')} {node.get('additionalType', '')}"),
        locality=fold(f"{address.get('addressLocality', '')} {areas} {where.get('name', '')}"),
        body=fold(f"{node.get('disambiguatingDescription', '')} {node.get('description', '')}"),
        features=frozenset(f["name"] for f in where.get("amenityFeature") or []),
    )


@cache
def store() -> Store:
    files = sorted(SCHEMA_DIR.glob("*.jsonld")) if SCHEMA_DIR.exists() else []
    if not files:
        raise DataNotBuiltError("Run `python -m src.schema_org_tourdata` to build the datasets")

    entries: dict[str, Entry] = {}
    metadata: dict[str, dict[str, Any]] = {}
    for path in files:
        document = json.loads(path.read_text(encoding="utf-8"))
        metadata[path.stem] = {
            "name": document["name"],
            "numberOfItems": document["numberOfItems"],
            "dateModified": document.get("dateModified"),
        }
        for element in document["itemListElement"]:
            entry = make_entry(path.stem, element["item"])
            entries[entry.id] = entry
    return Store(entries, metadata)


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * 6371 * asin(sqrt(a))


def score(entry: Entry, tokens: list[str]) -> int:
    """Rank a text match; every token has to occur somewhere, or the entry scores zero."""
    total = 0
    for token in tokens:
        points = (
            4 * (token in entry.title)
            + 3 * (token in entry.categories)
            + 2 * (token in entry.locality)
            + (token in entry.body)
        )
        if not points:
            return 0
        total += points
    return total


def matches_interests(entry: Entry, interests: list[str] | None) -> bool:
    return all(entry.features & INTEREST_FEATURES[interest] for interest in interests or [])


def clamp_limit(limit: int) -> int:
    return max(1, min(limit, MAX_LIMIT))


def distance_of(entry: Entry, latitude: float | None, longitude: float | None) -> float | None:
    if latitude is None or longitude is None or entry.latitude is None or entry.longitude is None:
        return None
    return distance_km(latitude, longitude, entry.latitude, entry.longitude)


def brief(entry: Entry, distance: float | None = None, dates: list[str] | None = None) -> dict[str, Any]:
    """A token-friendly subset of the schema.org node; the full node comes from get_place."""
    node = entry.node
    where = where_of(node)
    summary = node.get("disambiguatingDescription") or node.get("description") or ""
    shown = [p for p in where.get("additionalProperty") or [] if p["name"] in BRIEF_PROPERTIES]
    return {
        key: value
        for key, value in {
            "@type": node["@type"],
            "identifier": entry.id,
            "dataset": entry.dataset,
            "name": node.get("name"),
            "additionalType": node.get("additionalType"),
            "disambiguatingDescription": summary[:SUMMARY_LENGTH],
            "address": where.get("address"),
            "location": where.get("name") if where is not node else None,
            "geo": where.get("geo"),
            "url": node.get("url"),
            "servesCuisine": node.get("servesCuisine"),
            "additionalProperty": shown,
            "eventStatus": node.get("eventStatus"),
            "isAccessibleForFree": node.get("isAccessibleForFree"),
            "matchingDates": dates,
            "distanceKm": None if distance is None else round(distance, 1),
        }.items()
        if value not in ("", None, [])
    }


def item_list(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "license": LICENCE_URL,
        "numberOfItems": len(items),
        "itemListElement": [
            {"@type": "ListItem", "position": position, "item": item}
            for position, item in enumerate(items, start=1)
        ],
    }


def search_places(
    query: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    radius_km: float | None = None,
    datasets: list[str] | None = None,
    interests: list[str] | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Find places by text and/or position; results are nearest first without a text query."""
    tokens = [token for token in re.split(r"\W+", fold(query)) if token]
    wanted = set(datasets or PLACE_DATASETS)
    has_position = latitude is not None and longitude is not None
    radius = radius_km if radius_km is not None else DEFAULT_RADIUS_KM

    results = []
    for entry in store().entries.values():
        if entry.dataset not in wanted or not matches_interests(entry, interests):
            continue
        distance = distance_of(entry, latitude, longitude)
        if has_position and (distance is None or distance > radius):
            continue
        relevance = score(entry, tokens) if tokens else 0
        if tokens and not relevance:
            continue
        results.append((-relevance, distance if distance is not None else 0.0, entry.id, entry, distance))

    results.sort(key=lambda row: row[:3])
    return item_list([brief(row[3], row[4]) for row in results[: clamp_limit(limit)]])


def get_place(place_id: str) -> dict[str, Any] | None:
    """Return the complete schema.org node for one place or event."""
    entry = store().entries.get(place_id)
    if entry is None:
        return None
    return {"@context": "https://schema.org", "license": LICENCE_URL, **entry.node}


def today() -> date:
    return datetime.now(TIMEZONE).date()


def schedule_dates(schedule: dict[str, Any], first: date, last: date) -> set[date]:
    """Return the days within [first, last] on which a schema.org Schedule takes place."""
    start = date.fromisoformat(schedule["startDate"])
    stop = date.fromisoformat(schedule.get("endDate") or schedule["startDate"])
    frequency = schedule.get("repeatFrequency")
    weekdays = {
        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"].index(day.rsplit("/", 1)[1])
        for day in schedule.get("byDay") or []
    } or {start.weekday()}
    week_zero = start - timedelta(days=start.weekday())

    found = set()
    day = max(first, start)
    while day <= min(last, stop):
        if frequency is None:
            found.add(day)
        else:
            step, unit = int(frequency[1:-1]), frequency[-1]
            months = (day.year - start.year) * 12 + day.month - start.month
            if (
                (unit == "D" and (day - start).days % step == 0)
                or (unit == "W" and day.weekday() in weekdays and (day - week_zero).days // 7 % step == 0)
                or (unit == "M" and day.day == start.day and months % step == 0)
                or (unit == "Y" and (day.month, day.day) == (start.month, start.day) and (day.year - start.year) % step == 0)
            ):
                found.add(day)
        day += timedelta(days=1)
    return found


def find_events(
    latitude: float | None = None,
    longitude: float | None = None,
    radius_km: float | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    query: str | None = None,
    interests: list[str] | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Find events taking place within a date range, soonest first."""
    first = date_from or today()
    last = min(date_to or first + timedelta(days=14), first + timedelta(days=MAX_EVENT_WINDOW_DAYS))
    tokens = [token for token in re.split(r"\W+", fold(query)) if token]
    has_position = latitude is not None and longitude is not None
    radius = radius_km if radius_km is not None else DEFAULT_RADIUS_KM

    results = []
    for entry in store().entries.values():
        if entry.dataset != "events" or not matches_interests(entry, interests):
            continue
        distance = distance_of(entry, latitude, longitude)
        if has_position and (distance is None or distance > radius):
            continue
        if tokens and not score(entry, tokens):
            continue
        days = sorted(set().union(*(schedule_dates(s, first, last) for s in entry.node.get("eventSchedule") or [])))
        if days:
            results.append((days[0], distance if distance is not None else 0.0, entry.id, entry, distance, days))

    results.sort(key=lambda row: row[:3])
    return item_list(
        [brief(row[3], row[4], [d.isoformat() for d in row[5][:5]]) for row in results[: clamp_limit(limit)]]
    )


@dataclass(slots=True)
class MapPoint:
    id: str
    dataset: str
    name: str
    category: str | None
    address: str | None
    latitude: float
    longitude: float
    approximate: bool
    rank: int


def map_point(entry: Entry) -> MapPoint:
    where = where_of(entry.node)
    address = where.get("address") or {}
    town = " ".join(filter(None, [address.get("postalCode"), address.get("addressLocality")]))
    precision = next((p["value"] for p in where.get("additionalProperty") or [] if p["name"] == "locationPrecision"), None)
    return MapPoint(
        id=entry.id,
        dataset=entry.dataset,
        name=entry.node["name"],
        category=entry.node.get("additionalType"),
        address=", ".join(filter(None, [address.get("streetAddress"), town])) or None,
        latitude=entry.latitude,
        longitude=entry.longitude,
        approximate=precision == "approximate",
        rank=crc32(entry.id.encode()),
    )


def belongs_on_map(entry: Entry, first: date, last: date) -> bool:
    where = where_of(entry.node)
    if entry.dataset not in MAP_DATASETS or entry.latitude is None or entry.longitude is None:
        return False
    if (where.get("address") or {}).get("addressRegion") != MAP_REGION:
        return False  # TOURDATA also lists places just across the border
    if entry.dataset != "events":
        return True
    if entry.node.get("eventStatus") == "https://schema.org/EventCancelled":
        return False
    return any(schedule_dates(s, first, last) for s in entry.node.get("eventSchedule") or [])


@lru_cache(maxsize=1)
def map_index(day: date) -> list[MapPoint]:
    """All mappable points as of a given day; events only count while they are coming up."""
    last = day + timedelta(days=MAX_EVENT_WINDOW_DAYS)
    return [map_point(e) for e in store().entries.values() if belongs_on_map(e, day, last)]


def grid_size(span: float) -> float:
    """A power of two, so that grid cells don't shift while the map is panned."""
    return 2.0 ** ceil(log2(max(span, 1e-6) / MAP_GRID_DIVISIONS))


def thin_out(points: list[MapPoint], limit: int, lat_size: float, lon_size: float) -> list[MapPoint]:
    """Pick at most `limit` points, spread over the view and balanced between datasets.

    Each grid cell contributes its first point before any cell contributes a second, and a
    cell alternates between datasets. Ranks are hashes, so the same points win on every request.
    """
    cells: dict[tuple[int, int], dict[str, list[MapPoint]]] = defaultdict(lambda: defaultdict(list))
    for point in points:
        cells[floor(point.latitude / lat_size), floor(point.longitude / lon_size)][point.dataset].append(point)

    ranked = []
    for key, by_dataset in cells.items():
        cell_rank = crc32(str(key).encode())
        order = sorted(by_dataset, key=lambda name: crc32(f"{key}{name}".encode()))
        for dataset_index, name in enumerate(order):
            for position, point in enumerate(sorted(by_dataset[name], key=lambda p: p.rank)):
                ranked.append((position * len(order) + dataset_index, cell_rank, point.rank, point))

    ranked.sort(key=lambda row: row[:3])
    return [row[3] for row in ranked[:limit]]


def map_points(
    south: float,
    west: float,
    north: float,
    east: float,
    datasets: list[str] | None = None,
    limit: int = DEFAULT_MAP_POINTS,
) -> dict[str, Any]:
    """Return a capped, evenly spread set of the points within a map view."""
    wanted = set(datasets or MAP_DATASETS)
    in_view = [
        p
        for p in map_index(today())
        if p.dataset in wanted and south <= p.latitude <= north and west <= p.longitude <= east
    ]
    shown = thin_out(in_view, limit, grid_size(north - south), grid_size(east - west))
    return {
        "license": LICENCE_URL,
        "numberOfItems": len(in_view),
        "shown": len(shown),
        "points": [
            {
                "id": p.id,
                "dataset": p.dataset,
                "name": p.name,
                "category": p.category,
                "address": p.address,
                "latitude": p.latitude,
                "longitude": p.longitude,
                "approximate": p.approximate,
            }
            for p in shown
        ],
    }


def sources() -> list[dict[str, Any]]:
    """Describe every dataset: origin, licence, update frequency and current size."""
    metadata = store().metadata
    return [
        {"dataset": key, **metadata.get(key, {}), **details} for key, details in SOURCES.items()
    ]
