from typing import Any

import pandas as pd
import re
import numpy as np


import data.tourdata as tourdata


def is_valid(value):
    if value is None:
        return False

    if isinstance(value, (list, tuple, np.ndarray)):
        return len(value) > 0

    return not pd.isna(value)


DAY_MAPPING = {
    "Mon": "Monday",
    "Tue": "Tuesday",
    "Wed": "Wednesday",
    "Thu": "Thursday",
    "Fri": "Friday",
    "Sat": "Saturday",
    "Sun": "Sunday",
}


def parse_opening_hours(value: str):
    if not isinstance(value, str) or not value.strip():
        return []

    pattern = r"(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(\d{2}:\d{2})-(\d{2}:\d{2})"

    results = []

    for day, start, end in re.findall(pattern, value):
        results.append(
            {
                "@type": "OpeningHoursSpecification",
                "dayOfWeek": f"https://schema.org/{DAY_MAPPING[day]}",
                "opens": start,
                "closes": end,
            }
        )

    return results


def event_to_jsonld(row: pd.Series) -> dict[str, Any]:
    event = {
        "@type": "Event",
        "name": row["name"],
        "description": row["title"],
    }

    # Categories
    if is_valid(row["categories"]):
        event["keywords"] = row["categories"]

    # Location
    if is_valid(row["city"]):
        location = {
            "@type": "Place",
            "name": row["city"],
            "address": {
                "@type": "PostalAddress",
                "streetAddress": row["street"],
                "addressLocality": row["city"],
                "postalCode": row["zip"],
                "addressCountry": "AT",
            },
        }

        if is_valid(row["geo_main_latitude"]) and is_valid(row["geo_main_longitude"]):
            location["geo"] = {
                "@type": "GeoCoordinates",
                "latitude": row["geo_main_latitude"],
                "longitude": row["geo_main_longitude"],
            }

        event["location"] = location

    # Contact details
    if is_valid(row["email"]):
        event["email"] = row["email"]

    if is_valid(row["phone"]):
        event["telephone"] = row["phone"]

    if is_valid(row["web"]):
        event["url"] = row["web"]

    # Opening hours
    if is_valid(row["timeIntervals"]):
        hours = parse_opening_hours(str(row["timeIntervals"]))

        if hours:
            event["openingHoursSpecification"] = hours

    return {"@context": "https://schema.org", **event}


def to_schema_org() -> list[dict]:
    df = tourdata.events()
    return [event_to_jsonld(row) for _, row in df.iterrows()]


print(to_schema_org())
