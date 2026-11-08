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


def points_of_interest() -> pd.DataFrame:
    return read_json_to_dataframe("data/Points of interest (Poi.json, gzip)")


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
    gastro_raw: pd.DataFrame = read_json_to_dataframe("data/Gastronomy (Gastro.json)")
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

def landesmuseen() -> pd.DataFrame:
    return pd.read_csv(
        "https://e-gov.ooe.gv.at/at.gv.ooe.ogd2-citi/api/file/eb1MKuyzLjiztYufybYPnQ/Standorte_der_Oberoesterreichischen_Landesmuseen.csv",
        encoding="latin-1",
        sep=";",
    ).drop(columns=["Staats-ID"])


def accomodation() -> pd.DataFrame:
    return read_json_to_dataframe("data/Accommodation (Vermieter.json)")


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


def tours() -> pd.DataFrame:
    return read_json_to_dataframe("data/Tours (Tour.json, gzip)")


def packages_and_offers() -> pd.DataFrame:
    return read_json_to_dataframe("data/Packages and offers (GlobalePauschale.json)")


def places() -> pd.DataFrame:
    return read_json_to_dataframe("data/Places (OrteInformation.json)")


def tourism_areas() -> pd.DataFrame:
    return read_json_to_dataframe("data/Tourism areas (Gebiet.json)")
