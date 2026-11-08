"""Build the Upper Austria Heritage Experience Graph data product.

Combines the TOURDATA exports with the BDA monument register and Wikidata.
Run from the backend directory: python -m src.data.build_data_product
"""

import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Iterator
from datetime import date, timedelta
from difflib import SequenceMatcher
from html import unescape
from math import cos, radians
from pathlib import Path
from statistics import median
from typing import Any

import numpy as np
import pandas as pd
import requests

from src.data.monument_data import DEFAULT_INPUT as FULL_REGISTER_CSV
from src.data.monument_geocode import (
    MONUMENTS_CSV,
    clean_address,
    in_upper_austria,
    load_cache,
    locate,
)

DATASET_DIR = MONUMENTS_CSV.parent
OUTPUT_DIR = Path(__file__).resolve().parents[3] / "data_product"
WIKIDATA_CACHE = DATASET_DIR / "upperaustria_denkmal_wikidata_cache.csv"

SOURCES = {
    "stay": "Accommodation (Vermieter.json).json",
    "gastro": "Gastronomy (Gastro.json).json",
    "tour": "Tours (Tour.json, gzip)",
    "event": "Events (Veranstaltung.json).json",
}
AREAS_FILE = "Tourism areas (Gebiet.json).json"

WIKIDATA_URL = "https://query.wikidata.org/sparql"
WIKIDATA_QUERY = """
SELECT ?i ?id ?iLabel ?c ?img ?article WHERE {
  ?i wdt:P2951 ?id; wdt:P131+ wd:Q41967 .
  OPTIONAL {?i wdt:P625 ?c}
  OPTIONAL {?i wdt:P18 ?img}
  OPTIONAL {?article schema:about ?i; schema:isPartOf <https://de.wikipedia.org/>}
  SERVICE wikibase:label { bd:serviceParam wikibase:language "de". }
}"""
USER_AGENT = "HackathonSalzburg-dataproduct/1.0"

# Link thresholds, in metres.
ON_ROUTE_M = 200
ON_ROUTE_HIGH_CONFIDENCE_M = 100
GASTRO_M = 1000
STAY_M = 2000
EVENT_NEAR_M = 150
EVENT_NAMED_M = 500
NEARBY_LIMIT = 3
WIKIDATA_NAME_M = 1500
WIKIDATA_NAME_APPROX_M = 6000
WIKIDATA_TYPE_M = 250
WIKIDATA_NAME_SCORE = 0.92
WIKIDATA_GENERIC_TITLE_M = 150
WIKIDATA_MAX_EXTRA_LABEL_WORDS = 3
SUSPECT_KM = 30
SUSPECT_MIN_NEIGHBOURS = 3
HORIZON_DAYS = 365
OPEN_IMAGE_LICENSES = {"CC0", "CC-BY", "CC-BY-SA"}

ORIGIN_LAT = 48.2
ORIGIN_LON = 13.8
METRES_PER_DEGREE_LAT = 110574.0
METRES_PER_DEGREE_LON = 111320.0 * cos(radians(ORIGIN_LAT))

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
WEEKDAY_ABBREVIATIONS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
GENERIC_CATEGORIES = {"Unterkünfte", "Veranstaltungszentren", "Veranstaltungszentrum", "Location"}

# Words which describe what a monument is or are too common to identify one.
TYPE_WORDS = {
    "pfarrkirche", "filialkirche", "wallfahrtskirche", "stiftskirche", "stiftspfarrkirche", "kirche",
    "kapelle", "schloss", "burg", "burgruine", "ruine", "rathaus", "pranger", "stift", "kloster",
    "basilika", "dom", "museum", "turm", "stadtmauer", "tor", "denkmal", "brunnen", "theater",
    "bahnhof", "buergerhaus", "gasthaus", "wohnhaus", "ansitz", "palais", "mariensaeule", "pestsaeule",
    "dreifaltigkeitssaeule", "klause", "marktbrunnen", "stadtbrunnen", "lichtsaeule", "totenleuchte", "befestigung",
}
GENERIC_WORDS = {
    "kath", "evang", "ehem", "hl", "st", "sankt", "der", "die", "das", "des", "dem", "den", "von",
    "am", "an", "im", "in", "zu", "zum", "zur", "und", "mit", "sog", "teil", "teile", "sieben",
    "schmerzen", "maria", "mariae", "mariä", "unserer", "lieben", "frau", "johannes", "martin",
    "michael", "stephan", "georg", "jakob", "peter", "paul", "nikolaus", "laurentius", "bartholomaeus",
    "aegidius", "oswald", "leonhard", "ulrich", "barbara", "anna", "katharina", "margaretha",
    "alte", "alter", "altes", "neue", "neuer", "neues", "ober", "unter", "oo", "ooe", "lager", "inneren", "aeusseren",
}
TYPE_HEADS = TYPE_WORDS - {"kirche", "museum", "turm", "denkmal", "brunnen", "bahnhof", "tor"}

Record = dict[str, Any]


def fold(text: str) -> str:
    """Lowercase, spell out umlauts and drop other accents so names compare reliably."""
    text = text.lower().translate(str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}))
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", fold(text)))


def distinctive(text: str, municipality: str = "") -> set[str]:
    """Tokens that can identify a monument, without type words or the municipality's name."""
    ignored = TYPE_WORDS | GENERIC_WORDS | tokens(municipality)
    return {t for t in tokens(text) if t not in ignored and len(t) >= 4 and not t.isdigit()}


def title_parts(title: str) -> list[str]:
    return [part.strip() for part in re.split(r"[,/;]|\s-\s", title) if part.strip()]


def to_metres(lat: Any, lon: Any) -> tuple[Any, Any]:
    return (lon - ORIGIN_LON) * METRES_PER_DEGREE_LON, (lat - ORIGIN_LAT) * METRES_PER_DEGREE_LAT


def clean(value: Any) -> str:
    return " ".join(unescape(value).split()) if isinstance(value, str) else ""


def attribute(item: Record, key: str) -> str:
    return next((a.get("value", "") for a in item["attributes"] if a.get("key") == key), "")


def number(item: Record, key: str) -> float | None:
    value = next((n.get("value") for n in item["numbers"] if n.get("type") == key), None)
    return value if value else None


def rating(item: Record, key: str) -> int | None:
    return next((r.get("value") for r in item["ratings"] if r.get("type") == key), None)


def has(item: Record, *features: str) -> bool:
    return any(feature in item["features"] for feature in features)


def joined(values: Any) -> str:
    return "|".join(str(value) for value in dict.fromkeys(values))


def load_items(file_name: str) -> list[Record]:
    with open(DATASET_DIR / file_name, encoding="utf-8") as file:
        return json.load(file)["items"]


def load_wikidata() -> pd.DataFrame:
    if not WIKIDATA_CACHE.exists():
        response = requests.get(
            WIKIDATA_URL,
            params={"query": WIKIDATA_QUERY},
            headers={"Accept": "text/csv", "User-Agent": USER_AGENT},
            timeout=180,
        )
        response.raise_for_status()
        WIKIDATA_CACHE.write_bytes(response.content)
    frame = pd.read_csv(WIKIDATA_CACHE, dtype=str, keep_default_na=False)
    frame = frame[frame["c"].str.startswith("Point(")].drop_duplicates("i")
    points = frame["c"].str.extract(r"Point\(([-\d.]+) ([-\d.]+)\)").astype(float)
    frame = frame.assign(lon=points[0], lat=points[1], qid=frame["i"].str.rsplit("/", n=1).str[-1])
    return frame.reset_index(drop=True)


def recurrence(interval: Record, horizon: date) -> Iterator[date]:
    """Yield the start date of each occurrence of a TOURDATA time interval."""
    start = date.fromisoformat(interval["start"][:10])
    freq = interval.get("freq")
    if not freq:
        yield start
        return

    until = date.fromisoformat(interval["repeatUntil"][:10]) if interval.get("repeatUntil") else horizon
    until = min(until, horizon)
    step = interval.get("interval") or 1
    limit = interval.get("repeatCount")
    weekdays = {WEEKDAYS.index(day) for day in interval.get("weekdays", []) if day in WEEKDAYS}
    first_monday = start - timedelta(days=start.weekday())

    def matches(day: date) -> bool:
        if freq == "Daily":
            return (day - start).days % step == 0
        if freq == "Weekly":
            monday = day - timedelta(days=day.weekday())
            return (monday - first_monday).days // 7 % step == 0 and (not weekdays or day.weekday() in weekdays)
        if freq == "Yearly" and day.month != (interval.get("month") or start.month):
            return False
        if freq == "Monthly" and ((day.year - start.year) * 12 + day.month - start.month) % step:
            return False
        if interval.get("dayOfMonth"):
            return day.day == interval["dayOfMonth"]
        if interval.get("dayOrdinal") and interval.get("weekday") in WEEKDAYS:
            if day.weekday() != WEEKDAYS.index(interval["weekday"]):
                return False
            ordinal = interval["dayOrdinal"]
            if ordinal > 0:
                return (day.day - 1) // 7 + 1 == ordinal
            return (day + timedelta(days=-7 * ordinal)).month != day.month
        return day.day == start.day

    count = 0
    day = start
    while day <= until:
        if matches(day):
            count += 1
            if limit and count > limit:
                return
            yield day
        day += timedelta(days=1)


def opening_hours(item: Record, snapshot: date) -> str:
    """Weekly opening hours in force on the snapshot date, as 'Mo,Tu 08:00-20:30; Fr 10:00-12:00'."""
    slots: dict[tuple[str, str], set[int]] = defaultdict(set)
    for interval in item.get("timeIntervals") or []:
        if interval.get("freq") != "Weekly" or (interval.get("interval") or 1) != 1:
            continue
        begins = date.fromisoformat(interval["start"][:10])
        ends = date.fromisoformat(interval["repeatUntil"][:10]) if interval.get("repeatUntil") else None
        if begins > snapshot or (ends and ends < snapshot):
            continue
        slot = (interval["start"][11:16], interval["end"][11:16])
        slots[slot] |= {WEEKDAYS.index(day) for day in interval.get("weekdays", []) if day in WEEKDAYS}
    parts = [
        (min(days), f"{','.join(WEEKDAY_ABBREVIATIONS[d] for d in sorted(days))} {begin}-{end}")
        for (begin, end), days in slots.items()
        if days
    ]
    return "; ".join(text for _, text in sorted(parts))


def open_image(item: Record) -> tuple[str, str, str]:
    """Default image, only when its licence allows redistribution with attribution."""
    for media in item["media_objects"]:
        if media.get("rel") == "default" and media.get("license") in OPEN_IMAGE_LICENSES:
            return media["url"], media["license"], clean(media.get("author") or media.get("source"))
    return "", "", ""


def common_fields(item: Record, kind: str, regions: set[str]) -> Record:
    main = item["geo"].get("main") or {}
    categories = [c for c in item["categories"] if c not in GENERIC_CATEGORIES] or item["categories"]
    image, image_license, image_credit = open_image(item)
    interests = [f.removeprefix("AI_INTEREST_").lower() for f in item["features"] if f.startswith("AI_INTEREST_")]
    return {
        "place_id": item["global_id"],
        "kind": kind,
        "name": clean(item["title"]),
        "category": categories[0] if categories else "",
        "categories": joined(categories),
        "latitude": main.get("latitude"),
        "longitude": main.get("longitude"),
        "coord_precision": "source",
        "street": "",
        "zip": item.get("zip", ""),
        "municipality": attribute(item, "AssignOrt"),
        "gemeinde_code": attribute(item, "GEMKZF"),
        "district": item.get("district", ""),
        "state": attribute(item, "BUNDESLAND"),
        "region": joined(area for area in item["areas"] if area in regions),
        "tourism_board": attribute(item, "TV_Name"),
        "months_suitable": joined(s["month"] for s in item["seasons"] if s.get("suitable") == "Suitable"),
        "interests": joined(interests),
        "family_friendly": has(item, "OBJECT_FIT_FAMILIE", "OBJECT_FIT_FAMILIEN", "OBJECT_FIT_MITKIND", "OBJECT_FIT_KINDER"),
        "age_from": number(item, "OBJECT_FIT_KINDER_ALTERVON"),
        "age_to": number(item, "OBJECT_FIT_KINDER_ALTERBIS"),
        "weather_independent": has(item, "OBJECT_FIT_WETTERUNABHAENGIG"),
        "wheelchair_suitable": has(item, "ROLLSTUHLTAUGLICH"),
        "accessibility_score": rating(item, "Barrierefreiheit"),
        "pets_welcome": has(item, "OBJECT_FIT_HAUSTIERE"),
        "image_url": image,
        "image_license": image_license,
        "image_credit": image_credit,
        "source": "TOURDATA",
        "source_id": item["id"],
        "source_url": item.get("web", ""),
        "source_changed": item["changed"][:10],
        "source_quality_score": rating(item, "DataQuality"),
    }


def build_stay(item: Record, regions: set[str], snapshot: date) -> Record:
    place = common_fields(item, "stay", regions)
    # Many stays are private homes: no street, and coordinates only to about 100 m.
    place["latitude"] = round(place["latitude"], 3)
    place["longitude"] = round(place["longitude"], 3)
    place["coord_precision"] = "rounded_100m"
    place["beds"] = number(item, "ROOMS_BETTEN_GESAMT")
    place["price_from_eur"] = number(item, "PREIS_AB")
    place["bookable_online"] = has(item, "BOOKING_FERATEL_BOOKABLE")
    return place


def build_gastro(item: Record, regions: set[str], snapshot: date) -> Record:
    place = common_fields(item, "gastro", regions)
    place["street"] = clean(item.get("street"))
    place["cuisines"] = joined(c for c in item["cuisine_types"] if c not in ("nicht spezifiziert", "Sonstiges"))
    place["opening_hours"] = opening_hours(item, snapshot)
    place["seats_indoor"] = number(item, "ROOM_SITZEINDOOR")
    place["seats_outdoor"] = number(item, "ROOM_SITZEGASTGARTEN")
    return place


def build_tour(item: Record, regions: set[str], snapshot: date) -> Record:
    place = common_fields(item, "tour", regions)
    place["status"] = attribute(item, "Status").lower()
    place["length_km"] = round(item["length"] / 1000, 2) if item.get("length") else None
    place["duration_min"] = round(item["duration"] / 60) if item.get("duration") else None
    place["ascent_m"] = item.get("totalAscent")
    place["round_trip"] = bool(item.get("roundTrip"))
    place["difficulty_score"] = rating(item, "Schwierigkeit")
    place["fitness_score"] = rating(item, "Kondition")
    place["panorama_score"] = rating(item, "Panorama")
    place["source_flag_cultural"] = has(item, "INFO_KULTURELL")
    return place


def build_event(item: Record, regions: set[str], snapshot: date) -> Record:
    place = common_fields(item, "event", regions)
    place["street"] = clean(item.get("street"))
    place["status"] = attribute(item, "Status").lower()
    place["next_start"] = attribute(item, "NextFixtureStart")
    place["next_end"] = attribute(item, "NextFixtureEnd")
    place["free_entry"] = has(item, "PRICE_FREE")
    place["bookable_online"] = has(item, "HasBookingLink")
    place["source_fixture_count"] = number(item, "FixtureCount")

    first_fixture = date.fromisoformat(place["next_start"][:10])
    horizon = snapshot + timedelta(days=HORIZON_DAYS)
    fixtures = {
        day
        for interval in item["timeIntervals"]
        for day in recurrence(interval, horizon)
        if first_fixture <= day <= horizon
    }
    place["fixture_days_12m"] = len(fixtures)
    place["months_active"] = joined(sorted({day.strftime("%Y-%m") for day in fixtures}))
    return place


BUILDERS = {"stay": build_stay, "gastro": build_gastro, "tour": build_tour, "event": build_event}


def monument_name_score(title: str, label: str, municipality: str) -> float:
    """1 if every identifying word of the Wikidata label is in a part of the title, else similarity."""
    label_tokens = distinctive(label, municipality)
    best = 0.0
    for part in title_parts(title):
        fits = len(tokens(label)) <= len(tokens(part)) + WIKIDATA_MAX_EXTRA_LABEL_WORDS
        if label_tokens and fits and label_tokens <= tokens(part):
            return 1.0
        best = max(best, SequenceMatcher(None, fold(part), fold(label)).ratio())
    return best


def same_type_head(title: str, label: str) -> bool:
    return bool(tokens(title_parts(title)[0]) & tokens(label) & TYPE_HEADS)


def match_wikidata(monuments: list[Record], wikidata: pd.DataFrame) -> None:
    """Attach Wikidata entries one to one, using name and distance. HERIS IDs do not match P2951."""
    wiki_x, wiki_y = to_metres(wikidata["lat"].to_numpy(), wikidata["lon"].to_numpy())
    labels = wikidata["iLabel"].tolist()
    candidates: list[tuple[int, float, int, int, str]] = []

    for index, monument in enumerate(monuments):
        if monument["latitude"] is None:
            continue
        x, y = to_metres(monument["latitude"], monument["longitude"])
        distances = np.hypot(wiki_x - x, wiki_y - y)
        precise = monument["coord_precision"] == "address"
        radius = WIKIDATA_NAME_M if precise else WIKIDATA_NAME_APPROX_M
        # A bare "Rathaus" or "Pestsäule" only identifies the entry standing right there.
        generic_title = not distinctive(monument["name"], monument["municipality"])
        for wiki_index in np.flatnonzero(distances <= radius):
            distance = float(distances[wiki_index])
            score = monument_name_score(monument["name"], labels[wiki_index], monument["municipality"])
            if score >= WIKIDATA_NAME_SCORE and generic_title and (not precise or distance > WIKIDATA_GENERIC_TITLE_M):
                continue
            if score >= WIKIDATA_NAME_SCORE:
                candidates.append((2, score - distance / 1e7, index, int(wiki_index), "name"))
            elif precise and distance <= WIKIDATA_TYPE_M and same_type_head(monument["name"], labels[wiki_index]):
                candidates.append((1, 1 - distance / 1e4, index, int(wiki_index), "type_and_distance"))

    taken_monuments: set[int] = set()
    taken_entries: set[int] = set()
    for _, _, index, wiki_index, method in sorted(candidates, reverse=True):
        if index in taken_monuments or wiki_index in taken_entries:
            continue
        taken_monuments.add(index)
        taken_entries.add(wiki_index)
        monument = monuments[index]
        entry = wikidata.iloc[wiki_index]
        monument["wikidata_id"] = entry["qid"]
        monument["wikidata_label"] = entry["iLabel"]
        monument["wikidata_match"] = method
        monument["wikipedia_url"] = entry["article"]
        if entry["img"]:
            monument["image_url"] = entry["img"].replace("http://", "https://", 1)
            monument["image_license"] = "see Wikimedia Commons file page"
            monument["image_credit"] = "Wikimedia Commons"
        x, y = to_metres(monument["latitude"], monument["longitude"])
        wx, wy = to_metres(entry["lat"], entry["lon"])
        monument["wikidata_offset_m"] = round(float(np.hypot(wx - x, wy - y)))
        if monument["coord_precision"] != "address" and method == "name":
            monument["latitude"] = float(entry["lat"])
            monument["longitude"] = float(entry["lon"])
            monument["coord_precision"] = "wikidata"


def build_monuments(snapshot: date) -> list[Record]:
    register = pd.read_csv(MONUMENTS_CSV, sep=";", dtype=str, keep_default_na=False)
    cache = load_cache()
    monuments = []
    for row in register.to_dict("records"):
        point, approximate = locate(cache, row["Adresse"] or None, row["Gemeinde"])
        valid = point is not None and in_upper_austria(point)
        address = clean_address(row["Adresse"])[0]
        monuments.append(
            {
                "place_id": f"heris-{row['HERIS-ID']}",
                "kind": "monument",
                "name": clean(row["Objekttitel"]),
                "category": row["category"],
                "categories": row["category"],
                "latitude": point[0] if valid else None,
                "longitude": point[1] if valid else None,
                "coord_precision": ("locality" if approximate else "address") if valid else "none",
                "street": address.split(",")[0] if "," in address else "",
                "zip": (re.search(r",\s*(\d{4})\b", address) or [None, ""])[1],
                "municipality": row["Gemeinde"],
                "state": row["Bundesland"],
                "protection_status": row["Denkmalschutz Status"],
                "cadastral_community": row["KG"],
                "wikidata_id": "",
                "wikidata_label": "",
                "wikidata_match": "",
                "wikipedia_url": "",
                "wikidata_offset_m": None,
                "image_url": "",
                "image_license": "",
                "image_credit": "",
                "source": "BDA Denkmalverzeichnis",
                "source_id": row["HERIS-ID"],
                "source_url": "https://www.bda.gv.at/service/unterschutzstellung/denkmalverzeichnis/denkmalliste-gemaess-3-dmsg.html",
                "source_changed": "",
            }
        )
    return monuments


def assign_municipality_codes(monuments: list[Record], tourdata: list[Record]) -> dict[str, tuple[str, str]]:
    """Give monuments the code, district, region and board of their municipality from TOURDATA."""
    by_name: dict[str, Counter[tuple[str, str]]] = defaultdict(Counter)
    context: dict[str, Counter[tuple[str, str, str]]] = defaultdict(Counter)
    for place in tourdata:
        if place["state"] == "Oberösterreich" and place["gemeinde_code"]:
            by_name[fold(place["municipality"])][(place["gemeinde_code"], place["municipality"])] += 1
            context[place["gemeinde_code"]][(place["district"], place["region"], place["tourism_board"])] += 1
    names = {name: counts.most_common(1)[0][0] for name, counts in by_name.items()}

    def lookup(name: str) -> tuple[str, str] | None:
        key = fold(name)
        if key in names:
            return names[key]
        first = fold(re.split(r"[/,]", name)[0].strip())
        if first in names:
            return names[first]
        matches = [value for known, value in names.items() if known.startswith(first + " ") or first.startswith(known + " ")]
        return matches[0] if len({m[0] for m in matches}) == 1 else None

    resolved: dict[str, tuple[str, str]] = {}
    for monument in monuments:
        found = lookup(monument["municipality"])
        code = found[0] if found else ""
        monument["gemeinde_code"] = code
        district, region, board = context[code].most_common(1)[0][0] if code else ("", "", "")
        monument["district"], monument["region"], monument["tourism_board"] = district, region, board
        if found:
            resolved[monument["municipality"]] = found

    register = pd.read_csv(FULL_REGISTER_CSV, sep=";", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    for name in register["Gemeinde"].unique():
        found = lookup(name)
        if found:
            resolved[name] = found
    return resolved


def flag_suspect_coordinates(places: list[Record]) -> None:
    """Flag points far from the other places in their municipality; they get no spatial links.

    Tours are exempt: their point is a route start, which long routes have outside their municipality.
    """
    groups: dict[str, list[Record]] = defaultdict(list)
    for place in places:
        place["geo_suspect"] = False
        if place.get("gemeinde_code") and place["latitude"] is not None and place["kind"] != "tour":
            groups[place["gemeinde_code"]].append(place)
    for members in groups.values():
        if len(members) <= SUSPECT_MIN_NEIGHBOURS:
            continue
        mid_x, mid_y = to_metres(median(p["latitude"] for p in members), median(p["longitude"] for p in members))
        for place in members:
            x, y = to_metres(place["latitude"], place["longitude"])
            place["geo_suspect"] = bool(np.hypot(x - mid_x, y - mid_y) > SUSPECT_KM * 1000)


def spatial_links(
    monuments: list[Record], places: list[Record], kind: str, radius: float, relation: str, count_column: str,
) -> list[Record]:
    targets = [
        p for p in places
        if p["kind"] == kind and p["latitude"] is not None and not p["geo_suspect"] and p.get("status") != "cancelled"
    ]
    target_x, target_y = to_metres(np.array([t["latitude"] for t in targets]), np.array([t["longitude"] for t in targets]))
    links = []
    for monument in monuments:
        x, y = to_metres(monument["latitude"], monument["longitude"])
        distances = np.hypot(target_x - x, target_y - y)
        monument[count_column] = int((distances <= radius).sum())
        nearest = np.argsort(distances)[:NEARBY_LIMIT]
        links += [
            link(monument["place_id"], targets[i]["place_id"], relation, "spatial", "medium", float(distances[i]))
            for i in nearest
            if distances[i] <= radius
        ]
    return links


def link(
    source: str, target: str, relation: str, method: str, confidence: str,
    distance: float | None = None, along_route_km: float | None = None,
) -> Record:
    return {
        "from_id": source,
        "to_id": target,
        "relation": relation,
        "method": method,
        "confidence": confidence,
        "distance_m": round(distance) if distance is not None else None,
        "along_route_km": along_route_km,
    }


def route_links(monuments: list[Record], tours: list[Record], places_by_id: dict[str, Record]) -> tuple[list[Record], int]:
    """Find monuments within reach of each tour's route, and how far along the route they are."""
    xs, ys = to_metres(np.array([m["latitude"] for m in monuments]), np.array([m["longitude"] for m in monuments]))
    links = []
    parsed = 0
    for tour in tours:
        place = places_by_id.get(tour["global_id"])
        geometry = (tour["geo"].get("geometry") or {}).get("value")
        if not geometry or place is None or place["geo_suspect"]:
            continue
        values = np.array(geometry.split(), dtype=float)
        if len(values) < 4:
            continue
        points = values[: len(values) // 2 * 2].reshape(-1, 2)
        parsed += 1
        px, py = to_metres(points[:, 0], points[:, 1])
        near = np.flatnonzero(
            (xs >= px.min() - ON_ROUTE_M) & (xs <= px.max() + ON_ROUTE_M)
            & (ys >= py.min() - ON_ROUTE_M) & (ys <= py.max() + ON_ROUTE_M)
        )
        if near.size == 0:
            continue
        dx, dy = np.diff(px), np.diff(py)
        lengths = np.hypot(dx, dy)
        cumulative = np.concatenate(([0.0], np.cumsum(lengths)))
        squared = np.maximum(lengths**2, 1e-9)
        for index in near:
            along = np.clip(((xs[index] - px[:-1]) * dx + (ys[index] - py[:-1]) * dy) / squared, 0, 1)
            distance = np.hypot(px[:-1] + along * dx - xs[index], py[:-1] + along * dy - ys[index])
            best = int(np.argmin(distance))
            if distance[best] <= ON_ROUTE_M:
                confidence = "high" if distance[best] <= ON_ROUTE_HIGH_CONFIDENCE_M else "medium"
                position = (cumulative[best] + along[best] * lengths[best]) / 1000
                links.append(
                    link(tour["global_id"], monuments[index]["place_id"], "passes_monument", "route_geometry",
                         confidence, float(distance[best]), round(float(position), 2))
                )
    return links, parsed


def event_links(monuments: list[Record], events: list[Record], places_by_id: dict[str, Record]) -> list[Record]:
    """Tie events to monuments: named in title or venue text, otherwise simply very close."""
    usable = [e for e in events if (p := places_by_id[e["global_id"]])["status"] != "cancelled" and not p["geo_suspect"]]
    event_x, event_y = to_metres(
        np.array([places_by_id[e["global_id"]]["latitude"] for e in usable]),
        np.array([places_by_id[e["global_id"]]["longitude"] for e in usable]),
    )
    texts = [
        " " + " ".join(sorted(tokens(e["title"] + " " + " ".join(t["value"] for t in e["texts"] if t.get("rel") == "venues")))) + " "
        for e in usable
    ]
    links = []
    for monument in monuments:
        x, y = to_metres(monument["latitude"], monument["longitude"])
        distances = np.hypot(event_x - x, event_y - y)
        names = [d for part in title_parts(monument["name"]) if (d := distinctive(part, monument["municipality"]))]
        for index in np.flatnonzero(distances <= EVENT_NAMED_M):
            named = any(all(f" {token} " in texts[index] for token in name) for name in names)
            if named:
                links.append(link(usable[index]["global_id"], monument["place_id"], "held_at_monument", "name_and_distance", "high", float(distances[index])))
            elif distances[index] <= EVENT_NEAR_M:
                links.append(link(usable[index]["global_id"], monument["place_id"], "near_monument", "spatial", "low", float(distances[index])))
    return links


def curated_links(items: dict[str, list[Record]], known: set[str]) -> list[Record]:
    """Relations TOURDATA editors maintained themselves, between entities in this catalogue."""
    relation_names = {
        "Relation_Meine Empfehlungen": "recommends",
        "Relation_Veranstaltungsort": "has_venue",
        "Relation_Meine Betriebe": "same_operator",
        "Relation_Tourenvarianten": "route_variant",
    }
    links = []
    for records in items.values():
        for item in records:
            for sub in item["subitems"]:
                prefix = sub.get("type", "").rsplit("_", 1)[0]
                target = re.sub(r"^tourdata_(\w+?)_", lambda m: f"tourdata_{m[1].lower()}_", sub.get("ref") or "")
                if prefix in relation_names and target in known and target != item["global_id"]:
                    relation = relation_names[prefix]
                    # Venues list their events too: always store event -> venue.
                    reverse = relation == "has_venue" and target.startswith("tourdata_event_")
                    source, destination = (target, item["global_id"]) if reverse else (item["global_id"], target)
                    links.append(link(source, destination, relation, "tourdata_curated", "high"))
    return links


def build_alerts(items: dict[str, list[Record]], snapshot: date, known: set[str]) -> list[Record]:
    alerts = []
    for records in items.values():
        for item in records:
            if item["global_id"] not in known:
                continue
            for sub in item["subitems"]:
                if sub.get("type") != "Akutmeldung":
                    continue
                values = {a["key"]: a["value"] for a in sub["attributes"]}
                begins, ends = values.get("VALID_FROM", ""), values.get("VALID_UNTIL", "")
                active = (not begins or begins <= snapshot.isoformat()) and (not ends or ends >= snapshot.isoformat())
                alerts.append(
                    {
                        "place_id": item["global_id"],
                        "alert_id": sub["id"],
                        "title": clean(sub["title"]),
                        "alert_type": values.get("OBJECT_TYP", ""),
                        "valid_from": begins,
                        "valid_until": ends,
                        "open_ended": not ends,
                        "active_on_snapshot": active,
                    }
                )
    return alerts


def month_columns(snapshot: date) -> list[str]:
    return [f"{snapshot.year + (snapshot.month - 1 + i) // 12}-{(snapshot.month - 1 + i) % 12 + 1:02d}" for i in range(12)]


def build_municipalities(
    places: list[Record], links: list[Record], names: dict[str, tuple[str, str]], snapshot: date,
) -> list[Record]:
    months = month_columns(snapshot)
    register = pd.read_csv(FULL_REGISTER_CSV, sep=";", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    protected = Counter(names[name][0] for name in register["Gemeinde"] if name in names)
    display = {code: name for code, name in names.values()}

    linked_to: dict[str, set[str]] = defaultdict(set)
    for item in links:
        if item["relation"] == "passes_monument":
            linked_to[item["to_id"]].add("tour")
        elif item["relation"] in ("near_gastro", "near_stay"):
            linked_to[item["from_id"]].add(item["relation"])

    groups: dict[str, list[Record]] = defaultdict(list)
    for place in places:
        if place.get("gemeinde_code") and place.get("state") == "Oberösterreich":
            groups[place["gemeinde_code"]].append(place)
            display.setdefault(place["gemeinde_code"], place["municipality"])

    rows = []
    for code, members in sorted(groups.items()):
        count = lambda kind: sum(1 for p in members if p["kind"] == kind)  # noqa: E731
        by_kind = {kind: [p for p in members if p["kind"] == kind] for kind in ("monument", "tour", "gastro", "stay", "event")}
        monuments = by_kind["monument"]
        beds = sum(p.get("beds") or 0 for p in by_kind["stay"])
        fixtures = Counter(month for p in by_kind["event"] if p["status"] != "cancelled" for month in str(p["months_active"]).split("|") if month)
        offers = [p for p in members if p["kind"] != "monument"]
        row = {
            "gemeinde_code": code,
            "municipality": display[code],
            "district": Counter(p["district"] for p in members if p["district"]).most_common(1)[0][0] if any(p["district"] for p in members) else "",
            "region": Counter(p["region"] for p in members if p["region"]).most_common(1)[0][0] if any(p["region"] for p in members) else "",
            "monuments_protected": protected.get(code, 0),
            "monuments_touristic": count("monument"),
            "monuments_on_a_tour": sum(1 for m in monuments if "tour" in linked_to[m["place_id"]]),
            "monuments_with_food_1km": sum(1 for m in monuments if "near_gastro" in linked_to[m["place_id"]]),
            "monuments_with_stay_2km": sum(1 for m in monuments if "near_stay" in linked_to[m["place_id"]]),
            "tours": count("tour"),
            "tour_km": round(sum(p.get("length_km") or 0 for p in by_kind["tour"]), 1),
            "gastro": count("gastro"),
            "stays": count("stay"),
            "beds": int(beds),
            "events": count("event"),
            "family_offers": sum(1 for p in offers if p.get("family_friendly")),
            "weather_independent_offers": sum(1 for p in offers if p.get("weather_independent")),
            "wheelchair_offers": sum(1 for p in offers if p.get("wheelchair_suitable")),
            "monuments_per_1000_beds": round(count("monument") / beds * 1000, 2) if beds else None,
        }
        row.update({f"event_series_active_{month}": fixtures.get(month, 0) for month in months})
        rows.append(row)
    return rows


def monument_cards(
    monuments: list[Record], links: list[Record], places_by_id: dict[str, Record], alerts: list[Record],
) -> list[Record]:
    """One self-contained record per monument, ready for retrieval by an AI assistant."""
    outgoing: dict[str, list[Record]] = defaultdict(list)
    incoming: dict[str, list[Record]] = defaultdict(list)
    for item in links:
        outgoing[item["from_id"]].append(item)
        incoming[item["to_id"]].append(item)
    active: dict[str, list[str]] = defaultdict(list)
    for alert in alerts:
        if alert["active_on_snapshot"]:
            active[alert["place_id"]].append(alert["title"])

    def summary(place_id: str, distance: int | None, **extra: Any) -> Record:
        place = places_by_id[place_id]
        return {"id": place_id, "name": place["name"], "category": place["category"], "distance_m": distance, "url": place["source_url"], **extra}

    cards = []
    for monument in monuments:
        place_id = monument["place_id"]
        routes = sorted((l for l in incoming[place_id] if l["relation"] == "passes_monument"), key=lambda l: l["distance_m"])
        events = sorted(
            (l for l in incoming[place_id] if l["relation"] in ("held_at_monument", "near_monument")),
            key=lambda l: (l["relation"], places_by_id[l["from_id"]]["next_start"]),
        )
        nearby = lambda relation: [l for l in outgoing[place_id] if l["relation"] == relation]  # noqa: E731
        cards.append(
            {
                "id": place_id,
                "name": monument["name"],
                "category": monument["category"],
                "protection_status": monument["protection_status"],
                "municipality": monument["municipality"],
                "gemeinde_code": monument["gemeinde_code"],
                "region": monument["region"],
                "latitude": monument["latitude"],
                "longitude": monument["longitude"],
                "coord_precision": monument["coord_precision"],
                "wikidata_id": monument["wikidata_id"] or None,
                "wikipedia_url": monument["wikipedia_url"] or None,
                "image_url": monument["image_url"] or None,
                "on_tours": [
                    summary(
                        l["from_id"], l["distance_m"], km_from_start=l["along_route_km"],
                        length_km=places_by_id[l["from_id"]]["length_km"],
                        status=places_by_id[l["from_id"]]["status"],
                        active_alerts=active[l["from_id"]],
                    )
                    for l in routes[:10]
                ],
                "food_nearby": [
                    summary(
                        l["to_id"], l["distance_m"],
                        cuisines=places_by_id[l["to_id"]]["cuisines"],
                        opening_hours=places_by_id[l["to_id"]]["opening_hours"],
                    )
                    for l in nearby("near_gastro")
                ],
                "stays_nearby": [
                    summary(l["to_id"], l["distance_m"], beds=places_by_id[l["to_id"]]["beds"])
                    for l in nearby("near_stay")
                ],
                "events": [
                    summary(
                        l["from_id"], l["distance_m"], relation=l["relation"],
                        next_start=places_by_id[l["from_id"]]["next_start"],
                        status=places_by_id[l["from_id"]]["status"],
                    )
                    for l in events[:10]
                ],
            }
        )
    return cards


def json_ld(monuments: list[Record], links: list[Record], places_by_id: dict[str, Record]) -> Record:
    """Schema.org graph: every monument, plus each tour as a trip with monuments in route order."""
    graph: list[Record] = []
    for monument in monuments:
        node: Record = {
            "@id": f"urn:heritage-experience-graph:{monument['place_id']}",
            "@type": ["LandmarksOrHistoricalBuildings", "TouristAttraction"],
            "name": monument["name"],
            "identifier": {"@type": "PropertyValue", "propertyID": "HERIS-ID", "value": monument["source_id"]},
            "additionalType": monument["category"],
            "address": {
                "@type": "PostalAddress",
                "addressLocality": monument["municipality"],
                "addressRegion": "Oberösterreich",
                "addressCountry": "AT",
            },
        }
        if monument["latitude"] is not None:
            node["geo"] = {"@type": "GeoCoordinates", "latitude": monument["latitude"], "longitude": monument["longitude"]}
        same_as = [
            f"https://www.wikidata.org/wiki/{monument['wikidata_id']}" if monument["wikidata_id"] else "",
            monument["wikipedia_url"],
        ]
        if any(same_as):
            node["sameAs"] = [url for url in same_as if url]
        if monument["image_url"]:
            node["image"] = monument["image_url"]
        graph.append(node)

    routes: dict[str, list[Record]] = defaultdict(list)
    for item in links:
        if item["relation"] == "passes_monument":
            routes[item["from_id"]].append(item)
    for tour_id, stops in routes.items():
        tour = places_by_id[tour_id]
        ordered = sorted(stops, key=lambda stop: stop["along_route_km"])
        graph.append(
            {
                "@id": tour["source_url"],
                "@type": "TouristTrip",
                "name": tour["name"],
                "url": tour["source_url"],
                "additionalType": tour["category"],
                "itinerary": {
                    "@type": "ItemList",
                    "itemListOrder": "https://schema.org/ItemListOrderAscending",
                    "itemListElement": [
                        {
                            "@type": "ListItem",
                            "position": position,
                            "item": {"@id": f"urn:heritage-experience-graph:{stop['to_id']}"},
                        }
                        for position, stop in enumerate(ordered, start=1)
                    ],
                },
            }
        )
    return {"@context": "https://schema.org", "@graph": graph}


PLACE_COLUMNS = [
    "place_id", "kind", "name", "category", "categories", "latitude", "longitude", "coord_precision", "geo_suspect",
    "street", "zip", "municipality", "gemeinde_code", "district", "state", "region", "tourism_board",
    "months_suitable", "months_active", "interests", "family_friendly", "age_from", "age_to", "weather_independent",
    "wheelchair_suitable", "accessibility_score", "pets_welcome", "status", "length_km", "duration_min", "ascent_m",
    "round_trip", "difficulty_score", "fitness_score", "panorama_score", "source_flag_cultural", "monuments_on_route",
    "monument_categories_on_route", "cuisines", "opening_hours", "seats_indoor", "seats_outdoor", "beds",
    "price_from_eur", "bookable_online", "next_start", "next_end", "free_entry", "fixture_days_12m", "source_fixture_count",
    "protection_status", "cadastral_community", "wikidata_id", "wikidata_label", "wikidata_match", "wikidata_offset_m",
    "wikipedia_url", "tours_passing", "gastro_within_1km", "stays_within_2km", "events_linked", "active_alerts",
    "image_url", "image_license", "image_credit", "source", "source_id", "source_url", "source_changed", "source_quality_score",
]
INTEGER_COLUMNS = [
    "age_from", "age_to", "accessibility_score", "duration_min", "ascent_m", "difficulty_score", "fitness_score",
    "panorama_score", "monuments_on_route", "seats_indoor", "seats_outdoor", "beds", "fixture_days_12m",
    "source_fixture_count", "wikidata_offset_m", "tours_passing", "gastro_within_1km", "stays_within_2km",
    "events_linked", "active_alerts", "source_quality_score",
]

CONTACT_PATTERNS = {
    "email address": re.compile(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", re.I),
    "phone number": re.compile(r"\+43[\s\d/()-]{6,}"),
}


def write_csv(rows: list[Record], columns: list[str], path: Path, integers: list[str]) -> None:
    frame = pd.DataFrame(rows).reindex(columns=columns)
    for column in integers:
        frame[column] = pd.to_numeric(frame[column]).astype("Int64")
    frame.to_csv(path, index=False, encoding="utf-8", quoting=csv.QUOTE_MINIMAL, lineterminator="\n")


def validate(places: list[Record], links: list[Record], alerts: list[Record], output_files: list[Path]) -> dict[str, Any]:
    """Raise on any integrity failure, so a broken build can never be published."""
    identifiers = [place["place_id"] for place in places]
    known = set(identifiers)
    assert len(known) == len(identifiers), "place_id is not unique"
    assert all(item["from_id"] in known and item["to_id"] in known for item in links), "link to an unknown place"
    assert all(alert["place_id"] in known for alert in alerts), "alert on an unknown place"
    assert all(item["from_id"] != item["to_id"] for item in links), "self-link"
    triples = [(item["from_id"], item["to_id"], item["relation"]) for item in links]
    assert len(set(triples)) == len(triples), "duplicate link"
    for place in places:
        if place["latitude"] is not None:
            assert -90 <= place["latitude"] <= 90 and -180 <= place["longitude"] <= 180, place["place_id"]

    contact_hits: dict[str, int] = {}
    for path in output_files:
        text = path.read_text(encoding="utf-8")
        for label, pattern in CONTACT_PATTERNS.items():
            found = len(pattern.findall(text))
            assert not found, f"{found} x {label} in {path.name}"
            contact_hits[f"{path.name}: {label}"] = found
    return {"checks_passed": True, "contact_detail_matches": sum(contact_hits.values())}


def completeness(places: list[Record], columns: list[str]) -> dict[str, float]:
    filled = {column: sum(1 for p in places if p.get(column) not in (None, "")) for column in columns}
    return {column: round(count / len(places), 3) for column, count in filled.items()}


def fixture_agreement(events: list[Record]) -> dict[str, Any]:
    comparable = [e for e in events if e["fixture_days_12m"] and e.get("source_fixture_count") and e["status"] != "cancelled"]
    exact = sum(1 for e in comparable if e["fixture_days_12m"] == e["source_fixture_count"])
    within = sum(1 for e in comparable if abs(e["fixture_days_12m"] - e["source_fixture_count"]) <= 1)
    return {"events_compared": len(comparable), "exact_share": round(exact / len(comparable), 3), "within_one_share": round(within / len(comparable), 3)}


def main() -> None:
    items = {kind: load_items(file_name) for kind, file_name in SOURCES.items()}
    regions = {area["title"] for area in load_items(AREAS_FILE)}
    snapshot = max(date.fromisoformat(item["changed"][:10]) for records in items.values() for item in records)

    tourdata = [BUILDERS[kind](item, regions, snapshot) for kind, records in items.items() for item in records]
    monuments = build_monuments(snapshot)
    names = assign_municipality_codes(monuments, tourdata)
    match_wikidata(monuments, load_wikidata())

    places = tourdata + monuments
    flag_suspect_coordinates(places)
    by_id = {place["place_id"]: place for place in places}

    linkable = [m for m in monuments if m["coord_precision"] in ("address", "wikidata") and not m["geo_suspect"]]
    links: list[Record] = []
    routes, tours_parsed = route_links(linkable, items["tour"], by_id)
    links += routes
    links += spatial_links(linkable, places, "gastro", GASTRO_M, "near_gastro", "gastro_within_1km")
    links += spatial_links(linkable, places, "stay", STAY_M, "near_stay", "stays_within_2km")
    links += event_links(linkable, items["event"], by_id)
    links += curated_links(items, set(by_id))
    unique: dict[tuple[str, str, str], Record] = {(l["from_id"], l["to_id"], l["relation"]): l for l in links}
    links = list(unique.values())

    alerts = build_alerts(items, snapshot, set(by_id))

    counts: Counter[tuple[str, str]] = Counter()
    categories_on_route: dict[str, Counter[str]] = defaultdict(Counter)
    for item in links:
        counts[(item["from_id"], item["relation"])] += 1
        counts[(item["to_id"], item["relation"])] += 1
        if item["relation"] == "passes_monument":
            categories_on_route[item["from_id"]][by_id[item["to_id"]]["category"]] += 1
    active_alerts = Counter(a["place_id"] for a in alerts if a["active_on_snapshot"])
    for place in places:
        identifier = place["place_id"]
        place["active_alerts"] = active_alerts[identifier]
        if place["kind"] == "tour":
            place["monuments_on_route"] = counts[(identifier, "passes_monument")]
            place["monument_categories_on_route"] = joined(c for c, _ in categories_on_route[identifier].most_common())
        elif place["kind"] == "monument":
            place["tours_passing"] = counts[(identifier, "passes_monument")]
            place["events_linked"] = counts[(identifier, "held_at_monument")] + counts[(identifier, "near_monument")]

    OUTPUT_DIR.mkdir(exist_ok=True)
    places_path = OUTPUT_DIR / "places.csv"
    links_path = OUTPUT_DIR / "links.csv"
    alerts_path = OUTPUT_DIR / "alerts.csv"
    municipalities_path = OUTPUT_DIR / "municipalities.csv"
    cards_path = OUTPUT_DIR / "monument_cards.jsonl"
    graph_path = OUTPUT_DIR / "heritage_graph.jsonld"

    write_csv(places, PLACE_COLUMNS, places_path, INTEGER_COLUMNS)
    write_csv(links, list(next(iter(links))), links_path, ["distance_m"])
    write_csv(alerts, list(next(iter(alerts))), alerts_path, [])
    municipalities = build_municipalities(places, links, names, snapshot)
    write_csv(municipalities, list(next(iter(municipalities))), municipalities_path, [])
    cards = monument_cards(monuments, links, by_id, alerts)
    cards_path.write_text("".join(json.dumps(card, ensure_ascii=False) + "\n" for card in cards), encoding="utf-8")
    graph_path.write_text(json.dumps(json_ld(monuments, links, by_id), ensure_ascii=False, indent=1), encoding="utf-8")

    outputs = [places_path, links_path, alerts_path, municipalities_path, cards_path, graph_path]
    checks = validate(places, links, alerts, outputs)

    tours = [p for p in places if p["kind"] == "tour"]
    with_monuments = [t for t in tours if t["monuments_on_route"]]
    events = [p for p in places if p["kind"] == "event"]
    offsets = [m["wikidata_offset_m"] for m in monuments if m["wikidata_match"] and m["coord_precision"] == "address"]
    report = {
        "snapshot_date": snapshot.isoformat(),
        "places_by_kind": dict(Counter(p["kind"] for p in places)),
        "links_by_relation": dict(Counter(l["relation"] for l in links)),
        "links_by_confidence": dict(Counter(l["confidence"] for l in links)),
        "alerts": {"total": len(alerts), "active_on_snapshot": sum(1 for a in alerts if a["active_on_snapshot"])},
        "municipalities": len(municipalities),
        "integrity": checks,
        "monuments": {
            "coord_precision": dict(Counter(m["coord_precision"] for m in monuments)),
            "linkable": len(linkable),
            "without_municipality_code": sum(1 for m in monuments if not m["gemeinde_code"]),
            "wikidata_match": dict(Counter(m["wikidata_match"] or "unmatched" for m in monuments)),
            "median_geocode_vs_wikidata_offset_m": median(offsets) if offsets else None,
            "with_tour": sum(1 for m in monuments if m["tours_passing"]),
            "with_food_1km": sum(1 for m in monuments if m.get("gastro_within_1km")),
            "with_stay_2km": sum(1 for m in monuments if m.get("stays_within_2km")),
            "with_event": sum(1 for m in monuments if m["events_linked"]),
        },
        "tours": {
            "route_geometries_used": tours_parsed,
            "with_monument": len(with_monuments),
            "with_monument_but_not_flagged_cultural": sum(1 for t in with_monuments if not t["source_flag_cultural"]),
            "status": dict(Counter(t["status"] for t in tours)),
        },
        "events": {"status": dict(Counter(e["status"] for e in events)), "recurrence_vs_source_fixture_count": fixture_agreement(events)},
        "geo_suspect_places": sum(1 for p in places if p["geo_suspect"]),
        "outside_upper_austria": sum(1 for p in places if p.get("state") != "Oberösterreich"),
        "completeness": {
            kind: completeness([p for p in places if p["kind"] == kind], columns)
            for kind, columns in {
                "tour": ["length_km", "duration_min", "difficulty_score", "months_suitable", "image_url"],
                "gastro": ["cuisines", "opening_hours", "months_suitable", "image_url"],
                "stay": ["beds", "price_from_eur", "months_suitable", "image_url"],
                "event": ["next_start", "months_active", "image_url"],
                "monument": ["latitude", "gemeinde_code", "wikidata_id", "wikipedia_url", "image_url"],
            }.items()
        },
    }
    (OUTPUT_DIR / "quality_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
