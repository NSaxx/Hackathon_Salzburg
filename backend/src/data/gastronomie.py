import tourdata
from typing import Any

import pandas as pd

def fmt_interval(i: dict[str, Any]) -> str:
    days = ", ".join(d[:3] for d in i["weekdays"])
    start = i["start"][11:16]
    end = i["end"][11:16]
    return f"{days} {start}-{end}"


def fmt_time_intervals(intervals: object) -> str:
    if not isinstance(intervals, list):
        return ""
    return "; ".join(fmt_interval(i) for i in intervals)

def get_juicy_gastro_data() -> pd.DataFrame:
    gastro_raw: pd.DataFrame = tourdata.read_json_to_dataframe('Gastro.json')
    gastro_raw["timeIntervals"] = gastro_raw["timeIntervals"].apply(fmt_time_intervals)
    gastro_raw_filter: pd.DataFrame = gastro_raw[
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
    return gastro_raw_filter


get_juicy_gastro_data().to_csv("gastro.csv", index=False)
