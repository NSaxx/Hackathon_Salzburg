"""Geocode the touristic monuments and write them as map points for the frontend.

Run from the backend directory: python -m src.data.monument_geocode
"""

import json
import re
import time
from collections import Counter
from math import cos, hypot, sin, sqrt
from pathlib import Path

import pandas as pd
import requests

from address_to_coordinate import standard_url
from src.data.monument_data import DEFAULT_OUTPUT as MONUMENTS_CSV

DATASET_DIR = MONUMENTS_CSV.parent
CACHE_PATH = DATASET_DIR / "upperaustria_denkmal_geocode_cache.json"
OUTPUT_PATH = Path(__file__).resolve().parents[3] / "frontend" / "public" / "monuments.json"

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "HackathonSalzburg-monuments/1.0"
GEOCODE_DELAY = 0.2
NOMINATIM_DELAY = 1.1  # Nominatim's usage policy allows at most one request per second

UPPER_AUSTRIA_STATE_CODE = "4"
# lat/lon box around Upper Austria, rejects matches in another part of the country
SOUTH, NORTH, WEST, EAST = 47.46, 48.78, 12.74, 15.0
# A village or field name further than this from its municipality is a wrong match.
MAX_LOCALITY_KM = 15
STACK_SPACING = 0.0006  # degrees latitude, roughly 65 m
GOLDEN_ANGLE = 2.39996

ADDRESS = re.compile(r"^(?P<street>.+?)\s+(?P<number>\d+[a-zA-Z]?)\b.*?,\s*\d{4}\s+(?P<city>.+)$")
PARENTHESES = re.compile(r"\(([^)]*)\)")
LOCALITY = re.compile(r"^(?:Flur\s+)?(?P<name>.+?)(?:\s+GNR\b.*|\s+\d{4}\s.*|\s*,.*)?$")


def load_cache() -> dict[str, list[float] | None]:
    return json.loads(CACHE_PATH.read_text(encoding="utf-8")) if CACHE_PATH.exists() else {}


def in_upper_austria(point: list[float]) -> bool:
    return SOUTH <= point[0] <= NORTH and WEST <= point[1] <= EAST


def request_point(url: str, params: dict[str, str], headers: dict[str, str]) -> requests.Response | None:
    for attempt in range(3):
        try:
            return requests.get(url, params=params, headers=headers, timeout=20)
        except requests.exceptions.RequestException as error:
            print(f"retrying after {error}")
            time.sleep(2 * (attempt + 1))
    return None


def geocode_exact(cache: dict, street: str, number: str, city: str) -> list[float] | None:
    key = f"exact|{street}|{number}|{city}"
    if key not in cache:
        params = {"street": street, "streetNo": number, "state": UPPER_AUSTRIA_STATE_CODE, "city": city}
        response = request_point(standard_url, params, {})
        time.sleep(GEOCODE_DELAY)
        if response is None:
            return None  # network failure: leave uncached so a rerun tries again
        data = response.json() if response.ok else {}
        cache[key] = [data["lat"], data["lng"]] if "lat" in data else None
    return cache[key]


def distance_km(a: list[float], b: list[float]) -> float:
    return hypot((a[0] - b[0]) * 111, (a[1] - b[1]) * 74)


def geocode_place(cache: dict, query: str, settlement: bool = False) -> list[float] | None:
    key = f"{'settlement' if settlement else 'place'}|{query}"
    if key not in cache:
        params = {
            "q": query,
            "countrycodes": "at",
            "format": "jsonv2",
            "limit": "1",
            "viewbox": f"{WEST},{NORTH},{EAST},{SOUTH}",
            "bounded": "1",
        }
        if settlement:
            # Several towns share their name with a river (Enns, Steyr, Traun, ...).
            params["featureType"] = "settlement"
        response = request_point(NOMINATIM_URL, params, {"User-Agent": USER_AGENT})
        time.sleep(NOMINATIM_DELAY)
        if response is None:
            return None
        results = response.json() if response.ok else []
        cache[key] = [float(results[0]["lat"]), float(results[0]["lon"])] if results else None
    return cache[key]


def clean_address(address: str) -> tuple[str, list[str]]:
    """Remove register markers and parentheses, returning the text and the parenthesised parts."""
    address = re.sub(r"#MIG-\w+#|\bxxx\b", " ", address)
    districts = [part.strip() for part in PARENTHESES.findall(address)]
    return " ".join(PARENTHESES.sub(" ", address).split()), districts


def locate(cache: dict, address: object, municipality: str) -> tuple[list[float] | None, bool]:
    """Return (point, approximate) for a monument, preferring a house-level match."""
    text, districts = clean_address(address) if isinstance(address, str) else ("", [])
    municipality = re.split(r"[/,]", municipality)[0].strip()

    match = ADDRESS.match(text)
    if match:
        city = match["city"].split("/")[0].strip()
        for candidate in dict.fromkeys([city, *districts, municipality]):
            point = geocode_exact(cache, match["street"], match["number"], candidate)
            if point and in_upper_austria(point):
                return point, False

    places = [f"{district}, {municipality}" for district in districts]
    locality = LOCALITY.match(text)
    if text and not match and locality:
        places.append(f"{locality['name']}, {municipality}")

    home = geocode_place(cache, f"{municipality}, Oberösterreich", settlement=True)
    if home is None or not in_upper_austria(home):
        return None, True

    for place in dict.fromkeys(places):
        point = geocode_place(cache, place)
        if point and distance_km(point, home) <= MAX_LOCALITY_KM:
            return point, True
    return home, True


def spread_stacked(points: list[dict]) -> None:
    """Fan out monuments sharing one position, otherwise only the top one could be clicked."""
    seen: Counter[tuple[float, float]] = Counter()
    for point in points:
        position = (point["latitude"], point["longitude"])
        index = seen[position]
        seen[position] += 1
        if index:
            angle = index * GOLDEN_ANGLE
            offset = STACK_SPACING * sqrt(index)
            point["latitude"] = round(position[0] + offset * sin(angle), 5)
            point["longitude"] = round(position[1] + offset * cos(angle) * 1.5, 5)


def main() -> None:
    monuments = pd.read_csv(MONUMENTS_CSV, sep=";")
    cache = load_cache()
    points = []
    missing = 0

    for index, row in enumerate(monuments.itertuples(index=False), start=1):
        address = row.Adresse
        point, approximate = locate(cache, address, row.Gemeinde)
        if point is None:
            missing += 1
        else:
            cleaned = clean_address(address)[0] if isinstance(address, str) else row.Gemeinde
            points.append(
                {
                    "id": f"heris-{row[0]}",
                    "name": row.Objekttitel,
                    "category": row.category,
                    "address": cleaned,
                    "latitude": round(point[0], 5),
                    "longitude": round(point[1], 5),
                    "approximate": approximate,
                }
            )

        if index % 25 == 0:
            CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
            print(f"{index}/{len(monuments)}", flush=True)

    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    spread_stacked(points)
    OUTPUT_PATH.write_text(json.dumps(points, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    approximate_count = sum(point["approximate"] for point in points)
    print(f"wrote {len(points)} points ({approximate_count} approximate), {missing} not found")


if __name__ == "__main__":
    main()
