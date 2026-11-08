"""Data source register and the response envelope every service returns.

Each answer says where its data came from, under which licence, and when it
was fetched, so a client (or an AI agent) can show or check its sources.
"""

from datetime import UTC, datetime
from typing import Any

SOURCES: dict[str, dict[str, str]] = {
    "denkmalliste": {
        "name": "Denkmalliste Oberösterreich (Bundesdenkmalamt), filtered to "
        "sights a visitor would go and see",
        "url": "https://www.bda.gv.at/service/unterschutzstellung/denkmalverzeichnis/denkmalliste-gemaess-3-dmsg.html",
        "licence": "CC BY 4.0 (Bundesdenkmalamt), to verify",
        "update_frequency": "yearly (local snapshot)",
    },
    "open_meteo": {
        "name": "Open-Meteo weather forecast and geocoding",
        "url": "https://open-meteo.com",
        "licence": "CC BY 4.0 (data), free API for non-commercial use",
        "update_frequency": "hourly",
    },
}


def envelope(data: Any, *source_keys: str) -> dict[str, Any]:  # noqa: ANN401
    return {
        "data": data,
        "sources": [SOURCES[key] for key in source_keys],
        "retrieved_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
