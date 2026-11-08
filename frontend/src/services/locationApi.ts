export async function fetchLocationData(latitude: number, longitude: number) {
  const params = new URLSearchParams({
    lat: String(latitude),
    lon: String(longitude),
  });

  const response = await fetch(`http://localhost:8000/api/location?${params}`);

  if (!response.ok) {
    throw new Error("Could not retrieve location data");
  }

  return response.json();
}
