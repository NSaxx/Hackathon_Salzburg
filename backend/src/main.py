from datetime import date
from random import random
from typing import Annotated, Any, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src import chat, places
from src.data import open_meteo

app = FastAPI(
    title="Upper Austria tourism data service",
    description="TOURDATA and open data for Upper Austria as schema.org JSON-LD.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Latitude = Annotated[float | None, Query(ge=-90, le=90)]
Longitude = Annotated[float | None, Query(ge=-180, le=180)]
Radius = Annotated[float | None, Query(gt=0, le=200, description="Defaults to 25 km")]
Limit = Annotated[int, Query(ge=1, le=places.MAX_LIMIT)]
Datasets = Annotated[list[places.Dataset] | None, Query()]
Interests = Annotated[list[places.Interest] | None, Query()]


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Hello World" if random() <= 0.5 else "Greetings World"}


# The endpoints below are deliberately not async: the data and weather calls block,
# so FastAPI runs them in a worker thread.
@app.get("/api/location")
def location(
    lat: float = Query(ge=-90, le=90), lon: float = Query(ge=-180, le=180)
) -> dict[str, object]:
    try:
        hourly = open_meteo.data(lat, lon, past_days=0, forecast_days=5)
    except Exception as error:
        raise HTTPException(status_code=502, detail="Weather service unavailable") from error

    return {"weather": open_meteo.summary(hourly)}


def require_data() -> None:
    try:
        places.store()
    except places.DataNotBuiltError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.get("/api/places", summary="Search places by text, position, dataset and interest")
def list_places(
    q: str | None = None,
    lat: Latitude = None,
    lon: Longitude = None,
    radius_km: Radius = None,
    dataset: Datasets = None,
    interest: Interests = None,
    limit: Limit = 10,
) -> dict[str, Any]:
    require_data()
    return places.search_places(q, lat, lon, radius_km, dataset, interest, limit)


@app.get("/api/map-points", summary="Get a capped, evenly spread set of the points in a map view")
def list_map_points(
    south: float = Query(ge=-90, le=90),
    west: float = Query(ge=-180, le=180),
    north: float = Query(ge=-90, le=90),
    east: float = Query(ge=-180, le=180),
    dataset: Annotated[list[places.MapDataset] | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=places.MAX_MAP_POINTS)] = places.DEFAULT_MAP_POINTS,
) -> dict[str, Any]:
    require_data()
    return places.map_points(south, west, north, east, dataset, limit)


@app.get("/api/places/{place_id}", summary="Get the full schema.org record of a place or event")
def place_details(place_id: str) -> dict[str, Any]:
    require_data()
    node = places.get_place(place_id)
    if node is None:
        raise HTTPException(status_code=404, detail="No record with that id")
    return node


@app.get("/api/events", summary="Find events taking place within a date range")
def list_events(
    lat: Latitude = None,
    lon: Longitude = None,
    radius_km: Radius = None,
    date_from: date | None = None,
    date_to: date | None = None,
    q: str | None = None,
    interest: Interests = None,
    limit: Limit = 10,
) -> dict[str, Any]:
    require_data()
    return places.find_events(lat, lon, radius_km, date_from, date_to, q, interest, limit)


@app.get("/api/sources", summary="Data sources, licences and update frequency")
def list_sources() -> list[dict[str, Any]]:
    require_data()
    return places.sources()


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatLocation(BaseModel):
    id: str = Field(max_length=100)
    name: str = Field(max_length=300)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    category: str | None = Field(default=None, max_length=100)
    address: str | None = Field(default=None, max_length=300)
    approximate: bool | None = None


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=40)
    location: ChatLocation | None = None


@app.post("/api/chat", summary="Ask the concierge about Upper Austria or the selected place")
def chat_with_concierge(request: ChatRequest) -> dict[str, Any]:
    if request.messages[-1].role != "user":
        raise HTTPException(status_code=422, detail="The last message must come from the user")
    require_data()

    try:
        return chat.answer(
            [message.model_dump() for message in request.messages],
            request.location.model_dump() if request.location else None,
        )
    except chat.ChatNotConfiguredError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except chat.ChatBusyError as error:
        raise HTTPException(status_code=429, detail="The concierge is busy, please try again shortly") from error
    except chat.ChatUnavailableError as error:
        raise HTTPException(status_code=502, detail="The concierge is unavailable right now") from error
