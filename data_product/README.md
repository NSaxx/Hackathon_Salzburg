# Upper Austria Heritage Experience Graph

**Version 1.0, data as of 4 November 2026.** One joined, documented dataset that connects Upper Austria's protected monuments to the tours, restaurants, stays and events around them.

## Why it exists

The federal monument register knows what is historically important but says nothing about how to visit it. TOURDATA knows every trail, restaurant, bed and event but barely knows about heritage. This product connects the two.

- **1,436 of the 2,049 tours that pass a touristic monument are not flagged as cultural in the source.** That is cultural content which search, apps and AI assistants cannot currently find.
- 797 monuments now have at least one tour, 729 have a restaurant within 1 km, and 764 have a stay within 2 km.
- Every monument has a self-contained record that an AI assistant can use directly.

## What is included

| File | Grain | Use it for |
|---|---|---|
| `places.csv` | 18,145 places, one row each | A single catalogue of 918 monuments, 4,542 tours, 4,081 restaurants, 4,060 stays and 4,544 events |
| `links.csv` | 29,503 typed relations | Joining places: which monuments a tour passes, where to eat nearby, what is held where |
| `municipalities.csv` | 430 Upper Austrian municipalities | Heritage, offer and capacity comparison, plus event activity for 12 months |
| `alerts.csv` | 603 trail and site notices | Closures and warnings with validity dates |
| `monument_cards.jsonl` | 918 JSON records | Retrieval by AI agents and apps, no joins needed |
| `heritage_graph.jsonld` | schema.org graph | Monuments and 2,049 tours as `TouristTrip` itineraries in route order |
| `data_dictionary.csv` | Every column | Meaning, type and unit |
| `dcat.jsonld` | Catalogue record | Machine-readable metadata |

## How to join it to your data

- **`gemeinde_code`** is the official five-digit Austrian municipality code. Use it to join statistics, overnight stays, mobility or any other municipal data.
- **`place_id`** is the TOURDATA `global_id` (for example `tourdata_tour_100003`) or `heris-<HERIS-ID>` for monuments. Use it to fetch full descriptions and media from TOURDATA.
- **`wikidata_id`** links 650 monuments to the open knowledge graph.

## Example: what can a family do?

Short, open, family-friendly hikes that pass a castle, with a restaurant near that castle:

```python
import pandas as pd

places = pd.read_csv("places.csv", low_memory=False)
links = pd.read_csv("links.csv")

routes = (
    links[links.relation == "passes_monument"]
    .merge(places.add_prefix("tour_"), left_on="from_id", right_on="tour_place_id")
    .merge(places.add_prefix("monument_"), left_on="to_id", right_on="monument_place_id")
)
food = links.loc[links.relation == "near_gastro", ["from_id", "to_id", "distance_m"]].merge(
    places[["place_id", "name", "opening_hours"]], left_on="to_id", right_on="place_id"
)
matches = routes[
    (routes.tour_category == "Wanderweg")
    & (routes.tour_status == "open")
    & routes.tour_family_friendly
    & (routes.tour_length_km <= 8)
    & (routes.monument_category == "castle")
    & (routes.distance_m <= 100)
].merge(food, left_on="monument_place_id", right_on="from_id", suffixes=("", "_restaurant"))
```

This returns 56 distinct hikes. One is the Burg Werfenstein Wanderweg in St. Nikola, which reaches the castle ruin 5 km into a 5.7 km route.

## How the data was linked

| Relation | Direction | Rule | Confidence |
|---|---|---|---|
| `passes_monument` | tour to monument | Route geometry within 200 m, with position along the route | high up to 100 m, otherwise medium |
| `near_gastro` | monument to restaurant | Three nearest within 1 km, straight line | medium |
| `near_stay` | monument to stay | Three nearest within 2 km, straight line | medium |
| `held_at_monument` | event to monument | Monument name appears in the event title or venue, within 500 m | high |
| `near_monument` | event to monument | Within 150 m, name not confirmed | low |
| `recommends`, `has_venue`, `same_operator`, `route_variant` | as named | Maintained by TOURDATA editors | high |

Only monuments with address-level or Wikidata coordinates receive spatial links (846 of 918). Cancelled events and places with suspect coordinates are excluded from spatial links.

**Monument coordinates.** Addresses were geocoded, with 751 monuments placed at house level. Another 95 use Wikidata coordinates, and 72 remain at locality level (`coord_precision = locality`).

**Wikidata matching.** The HERIS-ID in the register is not the same identifier as Wikidata's P2951, so joining on those numbers links the wrong buildings. Matching uses name and distance instead, one to one, and `wikidata_match` records the method. Where both sources have a location, the median difference is 19 m.

## Quality checks

Each build stops with an error if `place_id` is not unique, a link points to an unknown place, a relation is duplicated, a coordinate is out of range, or an email address or phone number appears in an output file.

The first version was also audited against the raw files:

- 400 randomly sampled route links were recalculated with a separate method. None differed by more than 40 m.
- Route geometry length matches the published tour length (median ratio 0.999).
- Monthly event activity is expanded from the source recurrence rules. It matches the source's own count exactly for 90% of events. Most other differences are events with several time slots per day, because `fixture_days_12m` counts days.

## Known limitations

- This is a snapshot and is not updated live. Check `alerts.csv` and tour `status` against the source for anything safety-related.
- 395 alerts have no end date in the source. They are marked `open_ended` and counted as active, and some may be out of date.
- Distances to restaurants and stays are straight lines, not walking routes.
- A link means proximity, not that the monument can be entered. The register does not record opening hours or public access.
- The 918 monuments come from a keyword filter over the 5,982 register entries, so some visitable sites are missing. `monuments_protected` in `municipalities.csv` counts all entries.
- 551 places lie outside Upper Austria, mostly in Salzburg. They remain in `places.csv` with their `state` but are excluded from `municipalities.csv`.
- 12 places have coordinates far from their municipality. They are flagged in `geo_suspect` and kept for correction at the source.
- Bed numbers exist for 68% of stays, so `beds` and `monuments_per_1000_beds` are lower bounds and upper bounds respectively. Treat small municipalities with caution.
- Stay coordinates are rounded to about 100 m, so `near_stay` distances carry that error.
- `category` and `categories` for TOURDATA places are in German, as supplied.
- `weather_independent`, `family_friendly` and similar flags are the source's own values and were not checked on site.

## Privacy and rights

No email addresses, telephone numbers, contact persons or free-text descriptions are included. Stays have no street address and rounded coordinates, because many are private homes. Listing names are unchanged as published by TOURDATA, and some contain the host's surname.

| Source | Used for | Terms |
|---|---|---|
| TOURDATA, Upper Austria Tourism, via the TTF Data Space | Tours, restaurants, stays, events, areas | As set by the TTF Data Space |
| Bundesdenkmalamt, Denkmalverzeichnis | Monuments and protection status | Published by the BDA |
| Wikidata | Identifiers, coordinates, labels | CC0 |
| Wikimedia Commons | Monument image links | Per file, see each file page |
| geocode.at | House-level coordinates | As set by the service |
| OpenStreetMap via Nominatim | Locality coordinates | © OpenStreetMap contributors, ODbL |

TOURDATA images are linked only when their own licence is CC0, CC-BY or CC-BY-SA, with the credit in `image_credit`.

## Rebuild

From `backend/`, with the source files in `backend/dataset/`:

```bash
python -m src.data.build_data_product
```

## Contact

Team Kirschwarriors, Salzburg Tourism Hackathon 2026. Feedback and corrections are welcome through the TTF Data Space.
