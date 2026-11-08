"""Convert the TOURDATA exports and the monuments into schema.org JSON-LD.

Every dataset is written to dataset/schema_org/<name>.jsonld in the same ItemList
shape as the monuments dataset.

Run from the backend directory: python -m src.schema_org_tourdata
"""

import html
import json
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from src.data.monument_data import DATASET_DIR

SCHEMA_DIR = DATASET_DIR / "schema_org"

LICENCE_NAME = "CC BY 4.0"
LICENCE_URL = "https://creativecommons.org/licenses/by/4.0/"
TOURDATA_CREDIT = "TOURDATA, Upper Austria Tourism"
MONUMENTS_CREDIT = "Bundesdenkmalamt"
MONUMENTS_JSONLD = DATASET_DIR / "upperaustria_denkmal_touristic.jsonld"
MONUMENT_POINTS = Path(__file__).resolve().parents[2] / "frontend" / "public" / "monuments.json"

TOURDATA_FILES = {
    "gastronomy": "Gastronomy (Gastro.json).json",
    "accommodation": "Accommodation (Vermieter.json).json",
    "events": "Events (Veranstaltung.json).json",
    "tours": "Tours (Tour.json, gzip)",  # plain JSON despite the name
    "areas": "Tourism areas (Gebiet.json).json",
}

GASTRONOMY_TYPES = {
    "Restaurant": "Restaurant",
    "Gasthaus/Wirtshaus": "Restaurant",
    "Pizzeria": "Restaurant",
    "Almwirtschaft/Hütte": "Restaurant",
    "Jausenstation": "Restaurant",
    "Rasthaus/Autobahnraststätte": "Restaurant",
    "Haubenlokal": "Restaurant",
    "Skihütte": "Restaurant",
    "Bergrestaurant": "Restaurant",
    "Kaffeehaus/Café": "CafeOrCoffeeShop",
    "Buffet/Imbiss/Fastfood": "FastFoodRestaurant",
    "Bar/Pub": "BarOrPub",
    "Mostschänke": "BarOrPub",
    "Vinothek": "BarOrPub",
    "Konditorei": "Bakery",
    "Eisdiele/Eissalon": "IceCreamShop",
    "Heuriger/Buschenschank": "Winery",
    "Diskothek/Tanzlokal": "NightClub",
    "Nachtclub": "NightClub",
}

ACCOMMODATION_TYPES = {
    "Hotel": "Hotel",
    "Hotel garni": "Hotel",
    "Gasthof": "Hotel",
    "Motel": "Motel",
    "Pension": "BedAndBreakfast",
    "Privatzimmer": "BedAndBreakfast",
    "Bauernhof": "BedAndBreakfast",
    "Ferienwohnung": "VacationRental",
    "Ferienhaus": "VacationRental",
    "Campingplatz": "Campground",
    "Jugendherberge/Jugendgästehaus/Herberge": "Hostel",
}

# Checked in order, the first category found decides the type.
EVENT_TYPES = {
    "Konzert": "MusicEvent",
    "Musikveranstaltung": "MusicEvent",
    "Theater": "TheaterEvent",
    "Kabarett": "ComedyEvent",
    "Ausstellung": "ExhibitionEvent",
    "Kulinarisches": "FoodEvent",
    "Sportveranstaltung": "SportsEvent",
    "Fest": "Festival",
    "Markt, Messe": "SaleEvent",
    "Lesung": "LiteraryEvent",
    "Vorträge": "EducationEvent",
    "Kurs": "EducationEvent",
}

EVENT_STATUS = {
    "scheduled": "https://schema.org/EventScheduled",
    "rescheduled": "https://schema.org/EventRescheduled",
    "cancelled": "https://schema.org/EventCancelled",
    "postponed": "https://schema.org/EventPostponed",
}

DIFFICULTY = {
    "SL": "very easy",
    "L": "easy",
    "M": "medium",
    "S": "difficult",
    "SS": "very difficult",
}

FREQUENCY_UNITS = {"Daily": "D", "Weekly": "W", "Monthly": "M", "Yearly": "Y"}

# TOURDATA bookkeeping flags that say nothing about the place itself.
INTERNAL_FEATURE = re.compile(r"^(Has|Media_|LANGUAGE|DQ)")

TEXT_PROPERTIES = {
    "openings": "openingNotes",
    "kitchenhours": "kitchenHours",
    "price": "priceNotes",
    "directions": "directions",
    "citytax": "cityTax",
    "cancellation": "cancellationPolicy",
}

RATING_PROPERTIES = {
    "Barrierefreiheit": "accessibilityScore",
    "TrustYou": "trustYouScore",
    "FalstaffGabel": "falstaffFork",
    "FallstaffTasse": "falstaffCup",
    "FallstaffGlas": "falstaffGlass",
    "GaultMillau": "gaultMillau",
    "AlacarteWein": "alaCarteWine",
    "Michelin": "michelin",
    "Kondition": "fitnessRequired",
    "Panorama": "panorama",
}

NUMBER_PROPERTIES = {
    "PREIS_AB": "priceFromEuro",
    "ROOMS_BETTEN_GESAMT": "beds",
    "ROOMS_ZIMMER_GESAMT": "rooms",
    "ROOM_SITZEINDOOR": "indoorSeats",
    "ROOM_SITZEGASTGARTEN": "gardenSeats",
}


def compact(props: dict[str, Any]) -> dict[str, Any]:
    """Drop properties that have no value."""
    return {k: v for k, v in props.items() if v not in ("", None, [], {})}


def plain(value: object) -> str:
    """Turn TOURDATA's HTML fragments into plain text."""
    if not isinstance(value, str):
        return ""
    text = re.sub(r"<br\s*/?>|</p>|</div>|</li>|</h\d>", "\n", value, flags=re.IGNORECASE)
    text = html.unescape(re.sub(r"<[^>]+>", "", text))
    text = re.sub(r"[­​]", "", text).replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\s*\n\s*", "\n", text).strip()


def text_of(item: dict[str, Any], *rels: str) -> str:
    """Return the first non-empty text for the given rels, in that order."""
    for rel in rels:
        for entry in item.get("texts") or []:
            if entry.get("rel") == rel and (value := plain(entry.get("value"))):
                return value
    return ""


def attribute(item: dict[str, Any], key: str) -> str | None:
    return next((a.get("value") for a in item.get("attributes") or [] if a["key"] == key), None)


def rating(item: dict[str, Any], kind: str) -> float | None:
    return next((r.get("value") for r in item.get("ratings") or [] if r["type"] == kind), None)


def number(item: dict[str, Any], kind: str) -> float | None:
    return next((n.get("value") for n in item.get("numbers") or [] if n["type"] == kind), None)


def properties(pairs: dict[str, object]) -> list[dict[str, Any]]:
    return [
        {"@type": "PropertyValue", "name": name, "value": value}
        for name, value in pairs.items()
        if value not in ("", None, [], False)
    ]


def image_of(item: dict[str, Any]) -> dict[str, Any]:
    media = next((m for m in item.get("media_objects") or [] if m.get("rel") == "default"), None)
    if not media:
        return {}
    return compact(
        {
            "@type": "ImageObject",
            "url": media.get("url"),
            "caption": media.get("alt") or media.get("description"),
            "creditText": media.get("source"),
        }
    )


def base_node(item: dict[str, Any], node_type: str | list[str], extra: dict[str, object]) -> dict[str, Any]:
    """Build the properties shared by every TOURDATA object."""
    geo = (item.get("geo") or {}).get("main") or {}
    categories = item.get("categories") or []
    features = sorted(f for f in item.get("features") or [] if not INTERNAL_FEATURE.match(f))
    notices = [s.get("title") for s in item.get("subitems") or [] if s.get("type") == "Akutmeldung"]

    return compact(
        {
            "@type": node_type,
            "identifier": {
                "@type": "PropertyValue",
                "propertyID": "TOURDATA-ID",
                "value": item["global_id"],
            },
            "name": item["title"],
            "additionalType": categories[0] if categories else None,
            "keywords": ", ".join(categories),
            "disambiguatingDescription": text_of(item, "teaser", "teaser_summer", "teaser_winter"),
            "description": text_of(item, "details", "details_summer", "details_export", "details_winter"),
            "address": compact(
                {
                    "@type": "PostalAddress",
                    "streetAddress": item.get("street"),
                    "postalCode": item.get("zip"),
                    "addressLocality": item.get("city"),
                    "addressRegion": attribute(item, "BUNDESLAND"),
                    "addressCountry": item.get("country"),
                }
            )
            if item.get("city")
            else None,
            "geo": compact(
                {
                    "@type": "GeoCoordinates",
                    "latitude": geo.get("latitude"),
                    "longitude": geo.get("longitude"),
                    "elevation": geo.get("altitude"),
                }
            )
            if geo.get("latitude")
            else None,
            "telephone": item.get("phone"),
            "email": item.get("email"),
            "url": item.get("web"),
            "image": image_of(item),
            "containedInPlace": [
                {"@type": "AdministrativeArea", "name": area} for area in item.get("areas") or []
            ],
            "amenityFeature": [
                {"@type": "LocationFeatureSpecification", "name": feature, "value": True}
                for feature in features
            ],
            "additionalProperty": properties(
                {
                    **{name: text_of(item, rel) for rel, name in TEXT_PROPERTIES.items()},
                    **{name: rating(item, kind) for kind, name in RATING_PROPERTIES.items()},
                    **{name: number(item, kind) for kind, name in NUMBER_PROPERTIES.items()},
                    "discounts": "; ".join(
                        plain(t.get("value"))
                        for t in item.get("texts") or []
                        if str(t.get("rel")).startswith("discount_")
                    ),
                    "suitableMonths": ", ".join(
                        str(s["month"]) for s in item.get("seasons") or [] if s.get("suitable") == "Suitable"
                    ),
                    "notice": "; ".join(n for n in notices if n),
                    **extra,
                }
            ),
        }
    )


def plausible_date(value: str | None) -> str | None:
    """TOURDATA uses 1900 and 2070 as 'no real date' placeholders."""
    return value[:10] if value and 2000 <= int(value[:4]) <= 2050 else None


def opening_hours(item: dict[str, Any]) -> list[dict[str, Any]]:
    specs: dict[str, dict[str, Any]] = {}
    for interval in item.get("timeIntervals") or []:
        if not interval.get("weekdays"):
            continue
        spec = compact(
            {
                "@type": "OpeningHoursSpecification",
                "dayOfWeek": [f"https://schema.org/{day}" for day in interval["weekdays"]],
                "opens": interval["start"][11:16],
                "closes": interval["end"][11:16],
                "validFrom": plausible_date(interval.get("start")),
                "validThrough": plausible_date(interval.get("repeatUntil")),
            }
        )
        specs[json.dumps(spec, sort_keys=True)] = spec
    return list(specs.values())


def gastronomy(item: dict[str, Any]) -> dict[str, Any]:
    categories = item.get("categories") or []
    types = sorted({GASTRONOMY_TYPES[c] for c in categories if c in GASTRONOMY_TYPES})
    node_type = types[0] if len(types) == 1 else types or "FoodEstablishment"
    cuisines = [c for c in item.get("cuisine_types") or [] if c != "nicht spezifiziert"]
    return compact(
        {
            **base_node(item, node_type, {"alwaysOpen": item.get("alwaysOpen")}),
            "servesCuisine": cuisines,
            "openingHoursSpecification": opening_hours(item),
        }
    )


def accommodation(item: dict[str, Any]) -> dict[str, Any]:
    categories = item.get("categories") or []
    types = sorted({ACCOMMODATION_TYPES[c] for c in categories if c in ACCOMMODATION_TYPES})
    if types:
        node_type = types[0] if len(types) == 1 else types
    elif "Unterkünfte" in categories:
        node_type = "LodgingBusiness"
    else:
        node_type = "EventVenue"  # the export also holds event centres without any lodging
    return compact({**base_node(item, node_type, {}), "numberOfRooms": number(item, "ROOMS_ZIMMER_GESAMT")})


def schedule(interval: dict[str, Any]) -> dict[str, Any]:
    start, end = interval["start"], interval["end"]
    last_day = end[:10]
    if end[11:16] == "00:00" and last_day > start[:10]:
        last_day = (date.fromisoformat(last_day) - timedelta(days=1)).isoformat()

    frequency = FREQUENCY_UNITS.get(interval.get("freq") or "")
    repeat_until = (interval.get("repeatUntil") or "")[:10]
    return compact(
        {
            "@type": "Schedule",
            "startDate": start[:10],
            "endDate": repeat_until if frequency and repeat_until else last_day,
            "startTime": start[11:16],
            "endTime": end[11:16],
            "scheduleTimezone": "Europe/Vienna",
            "repeatFrequency": f"P{interval.get('interval') or 1}{frequency}" if frequency else None,
            "byDay": [f"https://schema.org/{d}" for d in interval.get("weekdays") or []] if frequency else None,
        }
    )


def event(item: dict[str, Any]) -> dict[str, Any]:
    categories = item.get("categories") or []
    node_type = next((t for c, t in EVENT_TYPES.items() if c in categories), "Event")
    node = base_node(item, node_type, {})
    features = item.get("features") or []
    free = "PRICE_FREE" in features

    place = compact(
        {
            "@type": "Place",
            "name": text_of(item, "venues") or item.get("name") or item.get("city"),
            "address": node.pop("address", None),
            "geo": node.pop("geo", None),
            "amenityFeature": node.pop("amenityFeature", None),
            "containedInPlace": node.pop("containedInPlace", None),
        }
    )
    organizer = next(
        (s.get("title") for s in item.get("subitems") or [] if str(s.get("type")).startswith("Relation_Veranstalter")),
        None,
    )
    price_notes = text_of(item, "price")
    node.pop("additionalProperty", None)  # not defined for Event; prices move to offers below

    return compact(
        {
            **node,
            "startDate": attribute(item, "NextFixtureStart"),
            "endDate": attribute(item, "NextFixtureEnd"),
            "eventStatus": EVENT_STATUS.get(attribute(item, "Status") or ""),
            "eventSchedule": [schedule(i) for i in item.get("timeIntervals") or []],
            "location": place,
            "organizer": {"@type": "Organization", "name": organizer} if organizer else None,
            "isAccessibleForFree": free or None,
            "offers": compact(
                {
                    "@type": "Offer",
                    "description": price_notes,
                    "price": 0 if free else None,
                    "priceCurrency": "EUR" if free else None,
                }
            )
            if free or price_notes
            else None,
        }
    )


def tour(item: dict[str, Any]) -> dict[str, Any]:
    return base_node(
        item,
        ["TouristAttraction", "TouristTrip"],
        {
            "difficulty": DIFFICULTY.get(attribute(item, "INFO_SCHWIERIGKEIT") or ""),
            "distanceMetres": item.get("length"),
            "durationSeconds": item.get("duration"),
            "ascentMetres": item.get("totalAscent"),
            "descentMetres": item.get("totalDescent"),
            "elevationMinMetres": item.get("elevationMin"),
            "elevationMaxMetres": item.get("elevationMax"),
            "roundTrip": item.get("roundTrip"),
            "trailStatus": attribute(item, "Status"),
        },
    )


def area(item: dict[str, Any]) -> dict[str, Any]:
    return base_node(item, "TouristDestination", {})


CONVERTERS = {
    "gastronomy": gastronomy,
    "accommodation": accommodation,
    "events": event,
    "tours": tour,
    "areas": area,
}

NAMES = {
    "gastronomy": "Restaurants, cafés and bars of Upper Austria",
    "accommodation": "Accommodation and event venues of Upper Austria",
    "events": "Events in Upper Austria",
    "tours": "Hiking, cycling and winter tours of Upper Austria",
    "areas": "Tourism regions of Upper Austria",
}


def item_list(name: str, nodes: list[dict[str, Any]], modified: str | None, credit: str) -> dict[str, Any]:
    return compact(
        {
            "@context": "https://schema.org",
            "@type": ["ItemList", "Dataset"],
            "name": name,
            "license": LICENCE_URL,
            "creditText": credit,
            "dateModified": modified,
            "numberOfItems": len(nodes),
            "itemListElement": [
                {"@type": "ListItem", "position": position, "item": node}
                for position, node in enumerate(nodes, start=1)
            ],
        }
    )


def write(key: str, document: dict[str, Any]) -> None:
    path = SCHEMA_DIR / f"{key}.jsonld"
    path.write_text(json.dumps(document, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{key}: {document['numberOfItems']} items, {path.stat().st_size / 1e6:.1f} MB")


def monuments() -> dict[str, Any]:
    """Add the geocoded positions to the monuments, which have no coordinates of their own."""
    source = json.loads(MONUMENTS_JSONLD.read_text(encoding="utf-8"))
    points = {p["id"]: p for p in json.loads(MONUMENT_POINTS.read_text(encoding="utf-8"))}

    nodes = []
    for element in source["itemListElement"]:
        node = element["item"]
        point = points.get(f"heris-{node['identifier']['value']}")
        if point:
            node["geo"] = {
                "@type": "GeoCoordinates",
                "latitude": point["latitude"],
                "longitude": point["longitude"],
            }
            node["additionalProperty"] = properties(
                {"locationPrecision": "approximate" if point["approximate"] else "address"}
            )
        nodes.append(node)
    return item_list(source["name"], nodes, None, MONUMENTS_CREDIT)


def main() -> None:
    SCHEMA_DIR.mkdir(exist_ok=True)
    for key, filename in TOURDATA_FILES.items():
        items = json.loads((DATASET_DIR / filename).read_text(encoding="utf-8"))["items"]
        nodes = [CONVERTERS[key](item) for item in items]
        write(key, item_list(NAMES[key], nodes, max(item["changed"] for item in items), TOURDATA_CREDIT))
    write("monuments", monuments())


if __name__ == "__main__":
    main()
