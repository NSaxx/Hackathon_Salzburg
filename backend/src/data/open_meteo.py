import openmeteo_requests

import pandas as pd
import requests_cache
from retry_requests import retry

# Link to explore the data set:
# https://open-meteo.com/en/docs/geosphere-austria-api?hourly=temperature_2m,weather_code


def data(
    latitude: float, longitude: float, past_days: int, forecast_days: 5
) -> pd.DataFrame:
    # Setup the Open-Meteo API client with cache and retry on error
    cache_session = requests_cache.CachedSession(".cache", expire_after=3600)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)

    # Make sure all required weather variables are listed here
    # The order of variables in hourly or daily is important
    # to assign them correctly  below
    responses = openmeteo.weather_api(
        url="https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "hourly": [
                "temperature_2m",
                "weather_code",
                "rain",
                "snowfall",
                "snowfall_height",
                "precipitation_probability",
                "precipitation",
                "sunshine_duration",
                "temperature_2m_max",
                "temperature_2m_min",
                "wind_speed_10m",
                "wind_direction_10m",
                "is_day",
            ],
            "timezone": "auto",
            "past_days": past_days,
            "forecast_days": forecast_days,
            "models": "geosphere_seamless",
        },
    )

    # Process first location. Add a for-loop for multiple locations or weather models
    response = responses[0]

    # Process hourly data. The order of variables needs to be the same as requested.
    hourly = response.Hourly()
    hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
    hourly_weather_code = hourly.Variables(1).ValuesAsNumpy()
    hourly_rain = hourly.Variables(2).ValuesAsNumpy()
    hourly_snowfall = hourly.Variables(3).ValuesAsNumpy()
    hourly_snowfall_height = hourly.Variables(4).ValuesAsNumpy()
    hourly_precipitation_probability = hourly.Variables(5).ValuesAsNumpy()
    hourly_precipitation = hourly.Variables(6).ValuesAsNumpy()
    hourly_sunshine_duration = hourly.Variables(7).ValuesAsNumpy()
    hourly_temperature_2m_max = hourly.Variables(8).ValuesAsNumpy()
    hourly_temperature_2m_min = hourly.Variables(9).ValuesAsNumpy()
    hourly_wind_speed_10m = hourly.Variables(10).ValuesAsNumpy()
    hourly_wind_direction_10m = hourly.Variables(11).ValuesAsNumpy()
    hourly_is_day = hourly.Variables(12).ValuesAsNumpy()

    hourly_data = {
        "date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left",
        ).tz_convert(response.Timezone().decode()),
        "temperature": hourly_temperature_2m,
        "weather_code": hourly_weather_code,
        "rain": hourly_rain,
        "snowfall": hourly_snowfall,
        "snowfall_height": hourly_snowfall_height,
        "precipitation_probability": hourly_precipitation_probability,
        "precipitation": hourly_precipitation,
        "sunshine_duration": hourly_sunshine_duration,
        "temperature_max": hourly_temperature_2m_max,
        "temperature_min": hourly_temperature_2m_min,
        "wind_speed": hourly_wind_speed_10m,
        "wind_direction": hourly_wind_direction_10m,
        "is_day": hourly_is_day,
    }

    return pd.DataFrame(data=hourly_data)


def _number(value: float) -> float | None:
    return None if pd.isna(value) else round(float(value), 1)


def summary(hourly: pd.DataFrame) -> dict[str, object]:
    """Reduce the hourly data to the conditions right now and one entry per day."""
    now = pd.Timestamp.now(tz=hourly["date"].dt.tz)
    current = hourly[hourly["date"] <= now].iloc[-1]

    days = [
        {
            "date": date.isoformat(),
            "temperature_min": _number(day["temperature_min"].min()),
            "temperature_max": _number(day["temperature_max"].max()),
            # Like Open-Meteo's daily value: the most severe weather of the day.
            "weather_code": _number(day["weather_code"].max()),
            "precipitation_probability": _number(day["precipitation_probability"].max()),
        }
        for date, day in hourly.groupby(hourly["date"].dt.date)
    ]

    return {
        "current": {
            "time": current["date"].isoformat(),
            "temperature": _number(current["temperature"]),
            "weather_code": _number(current["weather_code"]),
            "is_day": bool(current["is_day"]),
            "wind_speed": _number(current["wind_speed"]),
            "precipitation_probability": _number(current["precipitation_probability"]),
        },
        "days": days,
    }
