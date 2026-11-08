// In dev, Vite proxies /api to the backend (see vite.config.ts), so no CORS preflight is needed.
const API_URL = import.meta.env.VITE_API_URL ?? "";

export type LocationData = Record<string, unknown>;

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
