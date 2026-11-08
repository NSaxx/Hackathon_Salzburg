"""Convert gastro.csv into schema.org JSON-LD (FoodEstablishment and subtypes)."""

import ast
import json
from typing import Any

import pandas as pd

CSV_IN = "gastro.csv"
JSONLD_OUT = "gastro.jsonld"
COUNTRY = "AT"  # ISO 3166-1 alpha-2; change if your data is not Austrian

# category in your CSV -> schema.org type; anything else becomes FoodEstablishment
TYPE_MAP = {
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

DAYS = {
    "Mon": "Monday",
    "Tue": "Tuesday",
    "Wed": "Wednesday",
    "Thu": "Thursday",
    "Fri": "Friday",
    "Sat": "Saturday",
    "Sun": "Sunday",
}


def parse_list(value: object) -> list[Any]:
    """Parse a list that to_csv wrote as text, e.g. "['bar', 'pub']"."""
    if not isinstance(value, str) or not value.strip():
        return []
    return ast.literal_eval(value)


def compact(props: dict[str, Any]) -> dict[str, Any]:
    """Drop properties that have no value."""
    return {k: v for k, v in props.items() if v not in ("", None, [], {})}


def node(type_: str, **props: object) -> dict[str, Any]:
    """Build a nested schema.org node, or {} if it has no properties."""
    props = compact(props)
    return {"@type": type_, **props} if props else {}


def schema_type(categories: list[str]) -> str | list[str]:
    types = sorted({TYPE_MAP[c] for c in categories if c in TYPE_MAP})
    if not types:
        return "FoodEstablishment"
    return types[0] if len(types) == 1 else types


def parse_hours(text: str) -> list[dict[str, Any]]:
    """Parse 'Mon, Tue 08:00-20:30; Sat 09:00-12:00' into opening-hours specs."""
    specs = []
    for segment in dict.fromkeys(text.split("; ")):  # also drops exact repeats
        days_part, _, hours = segment.rpartition(" ")
        days = [DAYS[d] for d in days_part.split(", ") if d]
        if not days:  # segment without weekdays cannot be expressed, skip it
            continue
        opens, closes = hours.split("-")
        specs.append(
            node(
                "OpeningHoursSpecification",
                dayOfWeek=days,
                opens=f"{opens}:00",
                closes=f"{closes}:00",
            )
        )
    return specs


def absolute_url(url: str) -> str:
    if url and not url.startswith(("http://", "https://")):
        return f"https://{url}"
    return url


def to_schema(row: dict[str, Any]) -> dict[str, Any]:
    return compact(
        {
            "@type": schema_type(row["categories"]),
            "name": row["title"],
            "address": node(
                "PostalAddress",
                streetAddress=row["street"],
                postalCode=row["zip"],
                addressLocality=row["city"],
                addressCountry=COUNTRY,
            ),
            "geo": node(
                "GeoCoordinates",
                latitude=row["geo_main_latitude"],
                longitude=row["geo_main_longitude"],
            ),
            "telephone": row["phone"],
            "email": row["email"],
            "url": absolute_url(row["web"]),
            "keywords": ", ".join(row["categories"]),
            "openingHoursSpecification": row["openingHoursSpecification"],
        }
    )


def to_schema_org() -> None:
    df = pd.read_csv(CSV_IN, dtype={"zip": str, "phone": str}).fillna("")
    df["categories"] = df["categories"].apply(parse_list)

    skipped = sum(
        s.startswith(" ") for v in df["timeIntervals"] for s in set(v.split("; "))
    )
    df["openingHoursSpecification"] = df["timeIntervals"].apply(parse_hours)

    unmapped = {c for cats in df["categories"] for c in cats if c not in TYPE_MAP}
    if unmapped:
        print("Not in TYPE_MAP (kept in keywords only):", sorted(unmapped))
    if skipped:
        print(f"Skipped {skipped} interval(s) that have no weekdays")

    return {
        "@context": "https://schema.org",
        "@graph": [to_schema(row) for row in df.to_dict("records")],
    }


if __name__ == "__main__":
    with open(JSONLD_OUT, "w", encoding="utf-8") as f:
        json.dump(to_schema_org(), f, ensure_ascii=False, indent=2)
