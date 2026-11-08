# WIP Hackathon Project - Der AI Concierge von Oberösterreich (Atriensis Danubii)

## Architecture

The current architecture utilises a [Vite](https://vite.dev/)+[React](https://react.dev/) frontend written in [Typescript](https://www.typescriptlang.org/) with a Python backend using [FastAPI](https://fastapi.tiangolo.com/).

For those who have never made a web-app before, this is how it works:

1. We start the frontend and backend app independently.
2. By interacting with the frontend, the frontend sends requests to the backend (using `fetch()`).
3. The backend then responds, so the frontend can update accordingly.
4. This communication often involves data (e.g. requests with parameters, responses with requested data), which
   is always handled using JSON. In Typescript this corresponds to an object, while in Python this corresponds to a dictionary.

See [backend/DATA_AND_API.md](backend/DATA_AND_API.md) for the data service, the AI concierge, and the data sources and licences.

## Data licence

Our datasets are licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Weather data is by [Open-Meteo](https://open-meteo.com/en/docs/geosphere-austria-api) (CC BY 4.0), and map data is © OpenStreetMap contributors (ODbL).
