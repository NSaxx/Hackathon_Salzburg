import pandas as pd
from fastapi.testclient import TestClient

from src.data import open_meteo
from src.main import app

client = TestClient(app)


def fake_hourly(*_args: object, **_kwargs: object) -> pd.DataFrame:
    start = pd.Timestamp.now(tz="Europe/Vienna").normalize() - pd.Timedelta(days=1)
    return pd.DataFrame(
        {
            "date": pd.date_range(start, periods=72, freq="h"),
            "temperature": 5.0,
            "weather_code": [3.0] * 71 + [float("nan")],
            "wind_speed": 10.0,
            "precipitation_probability": 20.0,
            "temperature_max": range(72),
            "temperature_min": range(72),
            "is_day": 1.0,
        }
    )


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] in {"Hello World", "Greetings World"}


def test_location_returns_weather_summary(monkeypatch):
    monkeypatch.setattr(open_meteo, "data", fake_hourly)
    response = client.get("/api/location", params={"lat": 48.2, "lon": 14.4})

    assert response.status_code == 200
    weather = response.json()["weather"]
    assert weather["current"]["temperature"] == 5.0
    assert weather["current"]["is_day"] is True
    assert [day["temperature_max"] for day in weather["days"]] == [23, 47, 71]
    assert [day["temperature_min"] for day in weather["days"]] == [0, 24, 48]


def test_location_rejects_invalid_coordinates():
    assert client.get("/api/location", params={"lat": 123, "lon": 14.4}).status_code == 422


def test_location_reports_weather_failure(monkeypatch):
    def fail(*_args: object, **_kwargs: object) -> None:
        raise ConnectionError

    monkeypatch.setattr(open_meteo, "data", fail)
    response = client.get("/api/location", params={"lat": 48.2, "lon": 14.4})
    assert response.status_code == 502
