import sys

from typing import Any

import pandas as pd
import json

# data from TOURDATA, found in nexyo


def read_json_to_dataframe(filepath: str) -> pd.DataFrame:
    try:
        with open(filepath) as f:
            data = json.load(f)
            return pd.json_normalize(data, sep="_", record_path="items")
    except FileNotFoundError:
        print(f"You need to download the dataset and name it '{filepath}'")
        sys.exit(1)


def fmt_interval(i: dict[str, Any]) -> str:
    days = ", ".join(d[:3] for d in i["weekdays"])
    start = i["start"][11:16]
    end = i["end"][11:16]
    return f"{days} {start}-{end}"


def fmt_time_intervals(intervals: object) -> str:
    if not isinstance(intervals, list):
        return ""
    return "; ".join(fmt_interval(i) for i in intervals)


def gastronomy() -> pd.DataFrame:
    gastro_raw: pd.DataFrame = read_json_to_dataframe(
        "data/Gastronomy (Gastro.json).json"
    )
    gastro_raw["timeIntervals"] = gastro_raw["timeIntervals"].apply(fmt_time_intervals)
    gastro_clean: pd.DataFrame = gastro_raw[
        [
            "title",
            "categories",
            "street",
            "city",
            "zip",
            "geo_main_latitude",
            "geo_main_longitude",
            "email",
            "phone",
            "web",
            "timeIntervals",
        ]
    ]
    return gastro_clean


def events() -> pd.DataFrame:
    events_raw: pd.DataFrame = read_json_to_dataframe(
        "data/Events (Veranstaltung.json).json"
    )
    events_raw["timeIntervals"] = events_raw["timeIntervals"].apply(fmt_time_intervals)
    events_clean: pd.DataFrame = events_raw[
        [
            "name",
            "title",
            "categories",
            "street",
            "city",
            "zip",
            "geo_main_latitude",
            "geo_main_longitude",
            "email",
            "phone",
            "web",
            "timeIntervals",
        ]
    ]

    return events_clean
