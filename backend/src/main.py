from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from random import random

from src.data import open_meteo

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Hello World" if random() <= 0.5 else "Greetings World"}


# Deliberately not async: the Open-Meteo client blocks, so FastAPI runs this in a thread.
@app.get("/api/location")
def location(
    lat: float = Query(ge=-90, le=90), lon: float = Query(ge=-180, le=180)
) -> dict[str, object]:
    try:
        hourly = open_meteo.data(lat, lon, past_days=0, forecast_days=5)
    except Exception as error:
        raise HTTPException(status_code=502, detail="Weather service unavailable") from error

    return {"weather": open_meteo.summary(hourly)}
