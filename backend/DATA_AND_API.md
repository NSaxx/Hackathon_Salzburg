# Data service and AI concierge

Connects TOURDATA with open data for Upper Austria, publishes it as schema.org JSON-LD through a
small REST API, and answers guests through an AI concierge built on that API (hackathon challenge 05).

## Setup

1. Put the TOURDATA exports and monument files in `backend/dataset/`. The folder is git-ignored.
2. Build the schema.org datasets from the `backend` directory:

   ```bash
   python -m src.schema_org_tourdata
   ```

   This writes `dataset/schema_org/*.jsonld`. Re-run it whenever the exports change, then restart the server.

3. To use the chatbot, create a git-ignored `backend/.env` with the key for one.intelligence, the
   hackathon's OpenAI-compatible gateway, and restart the server. The data endpoints work without it.

   ```bash
   ONE_INTELLIGENCE_API_KEY=<your key>
   # Optional, this is the default model:
   ONE_INTELLIGENCE_MODEL=claude-sonnet-5-5
   ```

   All teams share the gateway's call quota. One guest question takes one call plus one per tool round
   (at most five in total), and failed calls are not retried.

## API

Interactive documentation is at `http://localhost:8000/docs` while the server runs.

| Endpoint | Purpose |
| --- | --- |
| `GET /api/places` | Search by text (`q`), position (`lat`, `lon`, `radius_km`), `dataset` and `interest` |
| `GET /api/places/{id}` | Full schema.org record of a place or event |
| `GET /api/events` | Events taking place between `date_from` and `date_to`, near a position or matching `q` |
| `GET /api/map-points` | At most `limit` evenly spread points inside `south`, `west`, `north`, `east`, plus the total in view. Covers Upper Austria's gastronomy, tours, monuments and events of the next 92 days |
| `GET /api/location` | Current weather and five-day forecast for `lat` and `lon` |
| `GET /api/sources` | Dataset origin, licence, update frequency, size and last change |
| `POST /api/chat` | The concierge. Takes `{ messages, location }`, returns `{ reply, sources }` |

`interest` is one of `kids`, `rainy_day`, `accessible`, `culinary`, `culture`, `nature`, `relaxation`,
`adventure`, `budget` or `pets`. List endpoints return a schema.org `ItemList` of shortened records; the
non-standard fields `distanceKm`, `matchingDates` and `dataset` are additions to help API clients.

The concierge's tools call the same functions as these endpoints (`src/places.py`), so it can only
report what the data service returns. Each reply lists the records it named as `sources`.

## Data sources

Live values for size and last change come from `GET /api/sources`.

| Dataset | Records | Source | Licence | Updates |
| --- | --- | --- | --- | --- |
| Gastronomy | 4,081 | TOURDATA, Upper Austria Tourism (via nexyo) | CC BY 4.0 | Maintained at source; re-export to refresh |
| Accommodation and venues | 4,060 | TOURDATA | CC BY 4.0 | As above |
| Events | 4,544 | TOURDATA | CC BY 4.0 | As above |
| Tours | 4,542 | TOURDATA | CC BY 4.0 | As above |
| Tourism regions | 7 | TOURDATA | CC BY 4.0 | As above |
| Monuments | 918 | [Bundesdenkmalamt list](https://www.bda.gv.at/service/unterschutzstellung/denkmalverzeichnis/denkmalliste-gemaess-3-dmsg.html), filtered to touristic sites | CC BY 4.0 | Published periodically; refreshed manually |
| Monument positions | 918 | geocode.at (751 at address level), OpenStreetMap Nominatim (167 approximate) | geocode.at to be confirmed; OSM is ODbL | Re-run `python -m src.data.monument_geocode` |
| Weather | Live | [Open-Meteo](https://open-meteo.com/en/docs/geosphere-austria-api), GeoSphere model | CC BY 4.0; free API is non-commercial | Live, cached for one hour |

Image credits from TOURDATA are kept in each record's `image.creditText`.

## Licence

The datasets are licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). When reusing them, credit the provider named above and link the licence. Our changes to the originals: converted to schema.org JSON-LD, HTML removed from texts, personal contact names and internal fields left out, and monuments given geocoded positions.

Each generated file and API response states this in a `license` field. The app shows it below the chat, every weather display links Open-Meteo, and every chatbot reply ends with its sources and their licence. Map tiles and OpenStreetMap-derived positions are © OpenStreetMap contributors under ODbL.

## schema.org mapping

Every file uses the same `ItemList` shape as the monuments dataset, also typed as `Dataset` so that it can carry `dateModified`.

| TOURDATA | schema.org |
| --- | --- |
| Gastro | `Restaurant`, `CafeOrCoffeeShop`, `BarOrPub`, `Bakery`, `Winery` and similar, by category |
| Vermieter | `Hotel`, `BedAndBreakfast`, `VacationRental`, `Campground`, `Hostel`, `LodgingBusiness`, `EventVenue` |
| Veranstaltung | `Event` subtypes with `eventSchedule`, `eventStatus`, `location` and `offers` |
| Tour | `TouristAttraction` and `TouristTrip` |
| Gebiet | `TouristDestination` |
| `features` | `amenityFeature` (on `location` for events) |
| `texts`, ratings and numbers without a schema.org property | `additionalProperty` |

Left out on purpose: names of contact persons and legal contacts, internal TOURDATA bookkeeping fields, and tour track geometry.

## Known gaps

- Water temperature, bathing water quality and public transport are not connected, so the concierge says it doesn't know.
- The Landesmuseen open dataset (`src/data/open_data_ooe.py`) returned HTTP 500 when this was built and is not included.
- Text search matches words and word parts. German terms work best, and the concierge translates for guests.
