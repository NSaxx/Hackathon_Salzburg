import sys

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


def gastronomy() -> pd.DataFrame:
    return read_json_to_dataframe("data/Gastronomy (Gastro.json).json")


def events() -> pd.DataFrame:
    return read_json_to_dataframe("data/Events (Veranstaltung.json).json")


def tours() -> pd.DataFrame:
    return read_json_to_dataframe("data/Tours (Tour.json, gzip)")


def packages_and_offers() -> pd.DataFrame:
    return read_json_to_dataframe(
        "data/Packages and offers (GlobalePauschale.json).json"
    )


def places() -> pd.DataFrame:
    return read_json_to_dataframe("data/Places (OrteInformation.json).json")


def tourism_areas() -> pd.DataFrame:
    return read_json_to_dataframe("data/Tourism areas (Gebiet.json).json")
