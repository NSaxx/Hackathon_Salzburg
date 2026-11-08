import json
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from src import chat, places, schema_org_tourdata as schema
from src.main import app

client = TestClient(app)

GASTRO_ITEM = {
    "global_id": "tourdata_gastro_1",
    "title": "Mostschänke Test",
    "categories": ["Mostschänke"],
    "city": "Steyr",
    "zip": "4400",
    "street": "Testgasse 1",
    "country": "AT",
    "geo": {"main": {"latitude": 48.05, "longitude": 14.42}},
    "web": "https://example.at/most",
    "texts": [
        {"rel": "teaser", "type": "text/html", "value": "<strong>Guter&nbsp;Most</strong><br>aus Steyr"},
        {"rel": "openings", "type": "text/html", "value": "Mo-Fr"},
    ],
    "features": ["HasRequiredTranslations", "AI_INTEREST_RAIN"],
    "timeIntervals": [
        {"weekdays": ["Monday"], "start": "2021-02-23T10:00:00+01:00", "end": "2021-02-24T00:00:00+01:00"},
        {"weekdays": ["Monday"], "start": "2021-02-23T10:00:00+01:00", "end": "2021-02-24T00:00:00+01:00"},
    ],
}

EVENT_ITEM = {
    "global_id": "tourdata_event_1",
    "title": "Adventmarkt Test",
    "categories": ["Markt, Messe"],
    "city": "Steyr",
    "country": "AT",
    "geo": {"main": {"latitude": 48.04, "longitude": 14.42}},
    "features": ["PRICE_FREE"],
    "attributes": [{"key": "Status", "value": "cancelled"}],
    "texts": [{"rel": "venues", "type": "text/plain", "value": "Stadtplatz"}],
    "timeIntervals": [
        {
            "weekdays": ["Saturday"],
            "start": "2026-11-28T10:00:00+01:00",
            "end": "2026-11-28T18:00:00+01:00",
            "repeatUntil": "2026-12-19T00:00:00+01:00",
            "freq": "Weekly",
            "interval": 1,
        }
    ],
}


@pytest.fixture
def data(monkeypatch):
    entries = [
        places.make_entry("gastronomy", schema.gastronomy(GASTRO_ITEM)),
        places.make_entry("events", schema.event(EVENT_ITEM)),
    ]
    monkeypatch.setattr(places, "store", lambda: places.Store({e.id: e for e in entries}, {}))


def test_gastronomy_maps_to_schema_org():
    node = schema.gastronomy(GASTRO_ITEM)

    assert node["@type"] == "BarOrPub"
    assert node["identifier"]["value"] == "tourdata_gastro_1"
    assert node["disambiguatingDescription"] == "Guter Most\naus Steyr"
    assert node["geo"]["latitude"] == 48.05
    assert [f["name"] for f in node["amenityFeature"]] == ["AI_INTEREST_RAIN"]
    assert len(node["openingHoursSpecification"]) == 1
    assert node["openingHoursSpecification"][0]["opens"] == "10:00"


def test_event_keeps_place_and_schedule_nested():
    node = schema.event(EVENT_ITEM)

    assert node["@type"] == "SaleEvent"
    assert node["location"]["name"] == "Stadtplatz"
    assert node["location"]["geo"]["longitude"] == 14.42
    assert "geo" not in node
    assert node["eventStatus"].endswith("EventCancelled")
    assert node["offers"]["price"] == 0
    assert node["eventSchedule"][0]["repeatFrequency"] == "P1W"
    assert node["eventSchedule"][0]["endDate"] == "2026-12-19"


def test_placeholder_dates_are_dropped():
    assert schema.plausible_date("1900-12-31T00:00:00+01:00") is None
    assert schema.plausible_date("2070-01-01T00:00:00+01:00") is None
    assert schema.plausible_date("2026-11-08T00:00:00+01:00") == "2026-11-08"


@pytest.mark.parametrize(
    ("schedule", "expected"),
    [
        ({"startDate": "2026-11-10"}, [date(2026, 11, 10)]),
        (
            {"startDate": "2026-11-09", "endDate": "2026-11-30", "repeatFrequency": "P1W", "byDay": ["https://schema.org/Saturday"]},
            [date(2026, 11, 14), date(2026, 11, 21), date(2026, 11, 28)],
        ),
        (
            {"startDate": "2026-11-09", "endDate": "2026-12-31", "repeatFrequency": "P2W", "byDay": ["https://schema.org/Monday"]},
            [date(2026, 11, 9), date(2026, 11, 23)],
        ),
        ({"startDate": "2026-11-29", "endDate": "2027-01-05", "repeatFrequency": "P1D"}, [date(2026, 11, 29), date(2026, 11, 30)]),
        ({"startDate": "2025-11-15", "endDate": "2027-01-05", "repeatFrequency": "P1Y"}, [date(2026, 11, 15)]),
        ({"startDate": "2026-12-01", "endDate": "2026-12-05"}, []),
    ],
)
def test_schedule_dates(schedule, expected):
    assert sorted(places.schedule_dates(schedule, date(2026, 11, 1), date(2026, 11, 30))) == expected


def test_umlauts_and_spellings_match():
    assert places.fold("Mühle") == places.fold("Muehle")
    assert places.fold("Schloß") == places.fold("Schloss")


def test_places_search_by_text_position_and_interest(data):
    found = client.get("/api/places", params={"q": "most", "lat": 48.05, "lon": 14.42, "interest": "rainy_day"}).json()
    assert found["@type"] == "ItemList"
    assert found["itemListElement"][0]["item"]["identifier"] == "tourdata_gastro_1"
    assert found["itemListElement"][0]["item"]["distanceKm"] == 0

    assert client.get("/api/places", params={"q": "most", "interest": "kids"}).json()["numberOfItems"] == 0
    assert client.get("/api/places", params={"lat": 47.0, "lon": 12.0, "radius_km": 5}).json()["numberOfItems"] == 0


def test_place_details(data):
    assert client.get("/api/places/tourdata_gastro_1").json()["@context"] == "https://schema.org"
    assert client.get("/api/places/unknown").status_code == 404


def test_events_are_filtered_by_date(data):
    inside = {"date_from": "2026-12-01", "date_to": "2026-12-07"}
    outside = {"date_from": "2027-02-01", "date_to": "2027-02-07"}

    result = client.get("/api/events", params=inside).json()
    assert result["itemListElement"][0]["item"]["matchingDates"] == ["2026-12-05"]
    assert client.get("/api/events", params=outside).json()["numberOfItems"] == 0


def map_item(index, kind="gastro", **extra):
    return {
        **GASTRO_ITEM,
        "global_id": f"tourdata_{kind}_{index}",
        "title": f"{kind} {index}",
        "geo": {"main": {"latitude": 48.0 + index % 40 * 0.01, "longitude": 14.0 + index // 40 * 0.01}},
        "attributes": [{"key": "BUNDESLAND", "value": "Oberösterreich"}],
        **extra,
    }


def use_map_entries(monkeypatch, entries):
    monkeypatch.setattr(places, "store", lambda: places.Store({e.id: e for e in entries}, {}))
    places.map_index.cache_clear()


VIEW = {"south": 47.0, "west": 13.0, "north": 49.0, "east": 15.0}


def test_map_points_are_capped_and_report_the_total(monkeypatch):
    use_map_entries(monkeypatch, [places.make_entry("gastronomy", schema.gastronomy(map_item(i))) for i in range(400)])

    result = client.get("/api/map-points", params={**VIEW, "limit": 25}).json()

    assert result["numberOfItems"] == 400
    assert result["shown"] == 25
    assert len(result["points"]) == 25
    assert client.get("/api/map-points", params={**VIEW, "limit": 25}).json() == result


def test_map_points_show_everything_in_a_small_view(monkeypatch):
    use_map_entries(monkeypatch, [places.make_entry("gastronomy", schema.gastronomy(map_item(i))) for i in range(5)])

    result = client.get("/api/map-points", params={**VIEW, "limit": 25}).json()

    assert (result["numberOfItems"], result["shown"]) == (5, 5)


def test_map_points_balance_datasets(monkeypatch):
    tour_items = [map_item(i, "tour", title=f"Tour {i}") for i in range(10)]
    use_map_entries(
        monkeypatch,
        [
            *[places.make_entry("gastronomy", schema.gastronomy(map_item(i))) for i in range(300)],
            *[places.make_entry("tours", schema.tour(item)) for item in tour_items],
        ],
    )

    points = client.get("/api/map-points", params={**VIEW, "limit": 20}).json()["points"]

    assert any(p["dataset"] == "tours" for p in points)
    assert any(p["dataset"] == "gastronomy" for p in points)


def test_map_points_leave_out_other_regions_and_past_or_cancelled_events(monkeypatch):
    other_region = map_item(1, attributes=[{"key": "BUNDESLAND", "value": "Salzburg"}])
    upcoming = places.today() + timedelta(days=3)
    interval = {"start": f"{upcoming}T10:00:00+01:00", "end": f"{upcoming}T12:00:00+01:00"}
    base = {"timeIntervals": [interval], "attributes": [{"key": "BUNDESLAND", "value": "Oberösterreich"}]}
    past = {**base, "timeIntervals": [{"start": "2020-01-01T10:00:00+01:00", "end": "2020-01-01T12:00:00+01:00"}]}
    cancelled = {**base, "attributes": [*base["attributes"], {"key": "Status", "value": "cancelled"}]}

    entries = [
        places.make_entry("gastronomy", schema.gastronomy(other_region)),
        places.make_entry("events", schema.event(map_item(2, "event", **base))),
        places.make_entry("events", schema.event(map_item(3, "event", **past))),
        places.make_entry("events", schema.event(map_item(4, "event", **cancelled))),
    ]
    use_map_entries(monkeypatch, entries)

    points = client.get("/api/map-points", params=VIEW).json()["points"]

    assert [p["id"] for p in points] == ["tourdata_event_2"]


def test_chat_validates_the_conversation(data):
    assert client.post("/api/chat", json={"messages": []}).status_code == 422
    last_from_assistant = {"messages": [{"role": "assistant", "content": "Hi"}]}
    assert client.post("/api/chat", json=last_from_assistant).status_code == 422


def api_message(content=None, tool_calls=None, finish_reason="stop"):
    message = {"role": "assistant", "content": content}
    if tool_calls:
        message["tool_calls"] = tool_calls
    return {"choices": [{"index": 0, "finish_reason": finish_reason, "message": message}]}


def tool_call(name, arguments):
    return {"id": "t1", "type": "function", "function": {"name": name, "arguments": json.dumps(arguments)}}


class FakeResponse:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self.body = body
        self.text = json.dumps(body)

    def json(self):
        return self.body


def fake_gateway(monkeypatch, responses, status_code=200):
    """Replace the gateway with canned responses and record the requests, so tests spend no quota."""
    seen = []

    def post(url, **kwargs):
        assert url.endswith("/chat/completions")
        seen.append(kwargs["json"])
        return FakeResponse(status_code, responses[len(seen) - 1])

    monkeypatch.setenv("ONE_INTELLIGENCE_API_KEY", "test")
    monkeypatch.setattr(chat.requests, "post", post)
    return seen


def test_chat_answers_from_the_tools_and_cites_sources(data, monkeypatch):
    requests = fake_gateway(
        monkeypatch,
        [
            api_message(tool_calls=[tool_call("search_places", {"query": "Most"})], finish_reason="tool_calls"),
            api_message("Try Mostschänke Test in Steyr."),
        ],
    )
    location = {"id": "location-3", "name": "Steyr", "latitude": 48.04, "longitude": 14.42}

    response = client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "Where can I buy cider?"}], "location": location},
    )

    assert response.status_code == 200
    assert response.json()["reply"] == "Try Mostschänke Test in Steyr."
    assert [s["id"] for s in response.json()["sources"]] == ["tourdata_gastro_1"]

    first, second = requests
    assert first["messages"][0]["role"] == "system"
    assert {t["function"]["name"] for t in first["tools"]} == {"search_places", "get_place_details", "find_events", "get_weather"}
    assert "Selected on the map: name: Steyr" in first["messages"][1]["content"]
    assert second["messages"][-2]["tool_calls"][0]["id"] == "t1"
    assert second["messages"][-1]["role"] == "tool"
    assert second["messages"][-1]["tool_call_id"] == "t1"
    assert "tourdata_gastro_1" in second["messages"][-1]["content"]


HELLO = {"messages": [{"role": "user", "content": "Hi"}]}


def test_sources_match_despite_different_punctuation():
    log = chat.SourceLog()
    log.add({"identifier": "a", "name": "Mitterhumer´s Hofstadl-Heuriger", "dataset": "gastronomy"})
    log.add({"identifier": "b", "name": "Not Mentioned", "dataset": "gastronomy"})

    assert [s["id"] for s in log.cited_in("Try Mitterhumer's Hofstadl Heuriger.")] == ["a"]


def test_sources_carry_provider_licence_and_a_link():
    log = chat.SourceLog()
    log.add({"identifier": "heris-1", "name": "Burg Test", "url": None, "dataset": "monuments"})
    log.used_weather = True

    monument, weather = log.cited_in("Visit Burg Test, it stays dry.")

    assert monument["provider"] == "Bundesdenkmalamt"
    assert monument["url"].startswith("https://www.bda.gv.at")
    assert monument["licence"] == "CC BY 4.0"
    assert weather["url"].startswith("https://open-meteo.com")


def test_answers_naming_no_record_still_credit_the_provider():
    log = chat.SourceLog()
    for identifier in ("a", "b"):
        log.add({"identifier": identifier, "name": f"Place {identifier}", "dataset": "tours"})
    log.add({"identifier": "c", "name": "Other", "dataset": "gastronomy"})

    assert [s["provider"] for s in log.cited_in("There are several options.")] == ["TOURDATA, Upper Austria Tourism"]


def test_api_responses_state_the_licence(data):
    licence = "https://creativecommons.org/licenses/by/4.0/"

    assert client.get("/api/places", params={"q": "most"}).json()["license"] == licence
    assert client.get("/api/places/tourdata_gastro_1").json()["license"] == licence
    assert schema.item_list("x", [], None, "y")["license"] == licence


def test_chat_hands_tool_errors_back_to_the_model(data, monkeypatch):
    requests = fake_gateway(
        monkeypatch,
        [
            api_message(tool_calls=[tool_call("find_events", {"date_from": "soon"})], finish_reason="tool_calls"),
            api_message("I could not check the date."),
        ],
    )

    assert client.post("/api/chat", json=HELLO).status_code == 200
    assert "find_events failed" in requests[1]["messages"][-1]["content"]


def test_chat_stops_calling_tools_after_the_round_limit(data, monkeypatch):
    looping = api_message(tool_calls=[tool_call("search_places", {"query": "Most"})], finish_reason="tool_calls")
    requests = fake_gateway(monkeypatch, [*[looping] * chat.MAX_TOOL_ROUNDS, api_message("Here is what I found.")])

    assert client.post("/api/chat", json=HELLO).json()["reply"] == "Here is what I found."
    assert len(requests) == chat.MAX_TOOL_ROUNDS + 1
    assert requests[-1]["tool_choice"] == "none"


def test_chat_handles_a_content_filter(data, monkeypatch):
    fake_gateway(monkeypatch, [api_message("", finish_reason="content_filter")])

    assert client.post("/api/chat", json=HELLO).json() == {"reply": chat.NO_ANSWER, "sources": []}


@pytest.mark.parametrize(("gateway_status", "expected"), [(401, 503), (429, 429), (500, 502)])
def test_chat_maps_gateway_errors_without_retrying(data, monkeypatch, gateway_status, expected):
    requests = fake_gateway(monkeypatch, [{"detail": "nope"}], status_code=gateway_status)

    assert client.post("/api/chat", json=HELLO).status_code == expected
    assert len(requests) == 1


def test_chat_reports_missing_credentials(data, monkeypatch):
    monkeypatch.delenv("ONE_INTELLIGENCE_API_KEY", raising=False)

    response = client.post("/api/chat", json=HELLO)

    assert response.status_code == 503
    assert "ONE_INTELLIGENCE_API_KEY" in response.json()["detail"]
