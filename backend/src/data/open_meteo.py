import openmeteo_requests

import pandas as pd
import requests_cache
from retry_requests import retry

# Link to explore the data set:
# https://open-meteo.com/en/docs/geosphere-austria-api?hourly=temperature_2m,weather_code


def data(latitude: float, longitude: float) -> pd.DataFrame:
    # Setup the Open-Meteo API client with cache and retry on error
    cache_session = requests_cache.CachedSession(".cache", expire_after=3600)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)

    # Make sure all required weather variables are listed here
    # The order of variables in hourly or daily is important to assign them correctly
    # below
    responses = openmeteo.weather_api(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "temperature_2m",
            "forecast_days": 3,
            "models": "geosphere_seamless",
        },
    )

    # Process first location. Add a for-loop for multiple locations or weather models
    response = responses[0]
    lat = abs(response.Latitude())
    long = abs(response.Longitude())
    south_or_north = "S" if response.Latitude() < 0 else "N"
    west_or_east = "W" if response.Longitude() < 0 else "E"
    print(f"Coordinates: {lat}°{south_or_north} {long}°{west_or_east}")
    print(f"Elevation: {response.Elevation()} m asl")
    print(f"Timezone difference to GMT+0: {response.UtcOffsetSeconds()}s")

    # Process hourly data. The order of variables needs to be the same as requested.
    hourly = response.Hourly()
    hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()

    hourly_data = {
        "date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left",
        )
    }

    hourly_data["temperature_2m"] = hourly_temperature_2m

    hourly_dataframe = pd.DataFrame(data=hourly_data)
    print("\nHourly data\n", hourly_dataframe)

    return hourly_dataframe
