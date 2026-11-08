import type { MapLocation } from "../data/locations";

// In dev, Vite proxies /api to the backend (see vite.config.ts), so no CORS preflight is needed.
export const API_URL = import.meta.env.VITE_API_URL ?? "";

export interface WeatherSummary {
  current: {
    time: string;
    temperature: number | null;
    weather_code: number | null;
    is_day: boolean;
    wind_speed: number | null;
    precipitation_probability: number | null;
  };
  days: {
    date: string;
    temperature_min: number | null;
    temperature_max: number | null;
    weather_code: number | null;
    precipitation_probability: number | null;
  }[];
  source: {
    name: string;
    url: string;
    licence: string;
    licenceUrl: string;
  };
}

export interface LocationData {
  weather: WeatherSummary;
}

export type PointDataset = "gastronomy" | "events" | "tours" | "monuments";

export interface MapPoint extends MapLocation {
  dataset: PointDataset;
}

export interface MapPoints {
  numberOfItems: number;
  shown: number;
  points: MapPoint[];
}

export async function fetchMapPoints(
  bounds: { south: number; west: number; north: number; east: number },
  limit: number,
  signal?: AbortSignal,
): Promise<MapPoints> {
  const params = new URLSearchParams({
    south: String(bounds.south),
    west: String(bounds.west),
    north: String(bounds.north),
    east: String(bounds.east),
    limit: String(limit),
  });

  const response = await fetch(`${API_URL}/api/map-points?${params}`, { signal });

  if (!response.ok) {
    throw new Error(`Could not load map points (${response.status})`);
  }

  return response.json();
}

export async function fetchLocationData(
  latitude: number,
  longitude: number,
  signal?: AbortSignal,
): Promise<LocationData> {
  const params = new URLSearchParams({
    lat: String(latitude),
    lon: String(longitude),
  });

  const response = await fetch(`${API_URL}/api/location?${params}`, { signal });

  if (!response.ok) {
    throw new Error(`Could not retrieve location data (${response.status})`);
  }

  return response.json();
}
