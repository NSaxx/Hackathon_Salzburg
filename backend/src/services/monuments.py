"""Search the touristic monuments of Upper Austria and describe them as schema.org."""

import re
from functools import cache
from pathlib import Path
from typing import Any

import pandas as pd

from src.services.sources import envelope

CSV_PATH = (
    Path(__file__).resolve().parents[2]
    / "datasets"
    / "upperaustria_denkmal_touristic.csv"
)

# Whether a category is mostly visited indoors, outdoors, or both.
# Used to pick sights that suit the weather.
SETTING = {
    "museum_memorial": "indoor",
    "abbey": "indoor",
    "pilgrimage": "indoor",
    "culture_venue": "indoor",
    "castle": "mixed",
    "technical": "mixed",
    "archaeology": "outdoor",
    "fortification": "outdoor",
    "landmark": "outdoor",
}

MAX_LIMIT = 50


@cache
def _load() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH, sep=";", dtype={"HERIS-ID": str})
    return df.fillna("")


def _to_dict(row: pd.Series) -> dict[str, str]:
    return {
        "heris_id": row["HERIS-ID"],
        "name": row["Objekttitel"],
        "municipality": row["Gemeinde"],
        "category": row["category"],
        "setting": SETTING.get(row["category"], "unknown"),
        "address": re.sub(r"\s+,", ",", row["Adresse"]).strip(),
    }


def categories() -> list[str]:
    return list(SETTING)


def search(
    municipality: str | None = None,
    category: str | None = None,
    query: str | None = None,
    limit: int = 10,
) -> list[dict[str, str]]:
    df = _load()
    if municipality:
        df = df[df["Gemeinde"].str.lower() == municipality.strip().lower()]
    if category:
        df = df[df["category"] == category]
    if query:
        df = df[df["Objekttitel"].str.contains(query, case=False, regex=False)]
    limit = max(1, min(limit, MAX_LIMIT))
    return [_to_dict(row) for _, row in df.head(limit).iterrows()]


def get(heris_id: str) -> dict[str, str] | None:
    df = _load()
    match = df[df["HERIS-ID"] == str(heris_id)]
    return None if match.empty else _to_dict(match.iloc[0])


def to_json_ld(monument: dict[str, str], *, context: bool = True) -> dict[str, Any]:
    """schema.org JSON-LD, ready to embed in a web page or hand to an AI agent.

    Pass `context=False` when the monument is nested in a document that already
    declares the `@context`.
    """
    address: dict[str, str] = {
        "@type": "PostalAddress",
        "addressLocality": monument["municipality"],
        "addressRegion": "Oberösterreich",
        "addressCountry": "AT",
    }
    # Addresses look like "Grünburger Straße 117, 4541 Adlwang".
    if m := re.match(r"^(.*),\s*(\d{4})\s+.+$", monument["address"]):
        address["streetAddress"], address["postalCode"] = m.group(1), m.group(2)
    elif monument["address"]:
        address["streetAddress"] = monument["address"]
    json_ld = {
        "@type": ["LandmarksOrHistoricalBuildings", "TouristAttraction"],
        "identifier": {
            "@type": "PropertyValue",
            "propertyID": "HERIS-ID",
            "value": monument["heris_id"],
        },
        "name": monument["name"],
        "additionalType": monument["category"],
        "keywords": monument["category"],
        "address": address,
    }
    return {"@context": "https://schema.org"} | json_ld if context else json_ld


def export_json_ld() -> dict[str, Any]:
    """Every touristic monument as one schema.org `ItemList`."""
    monuments = [_to_dict(row) for _, row in _load().iterrows()]
    return {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "Touristic monuments of Upper Austria",
        "numberOfItems": len(monuments),
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": position,
                "item": to_json_ld(monument, context=False),
            }
            for position, monument in enumerate(monuments, start=1)
        ],
    }


def search_response(**kwargs: Any) -> dict[str, Any]:  # noqa: ANN401
    return envelope(search(**kwargs), "denkmalliste")


def get_response(heris_id: str) -> dict[str, Any]:
    monument = get(heris_id)
    if monument is None:
        return envelope(None, "denkmalliste") | {
            "error": f"No monument with HERIS-ID {heris_id}"
        }
    return envelope(monument | {"json_ld": to_json_ld(monument)}, "denkmalliste")
