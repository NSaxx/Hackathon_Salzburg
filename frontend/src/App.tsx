import { useCallback, useEffect, useRef, useState } from "react";
import "./App.css";

import InteractiveMap from "./components/Map/InteractiveMap";
import { locations, type MapLocation } from "./data/locations";
import { fetchLocationData, type LocationData } from "./services/locationApi";

function App() {
  const [selectedLocation, setSelectedLocation] = useState<MapLocation | null>(null);
  const [data, setData] = useState<LocationData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Only the most recent click may update state; earlier in-flight requests are aborted.
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => () => abortRef.current?.abort(), []);

  const handleLocationClick = useCallback(async (location: MapLocation) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setSelectedLocation(location);
    setLoading(true);
    setError(null);
    setData(null);

    try {
      const result = await fetchLocationData(
        location.latitude,
        location.longitude,
        controller.signal,
      );
      setData(result);
    } catch (err) {
      if (controller.signal.aborted) return;
      console.error(err);
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, []);

  return (
    <div className="app">
      <main className="map-container">
        <InteractiveMap
          locations={locations}
          selectedLocationId={selectedLocation?.id ?? null}
          onLocationClick={handleLocationClick}
        />
      </main>

      <aside className="info-panel" aria-live="polite">
        <h2>{selectedLocation?.name ?? "Location information"}</h2>

        {!selectedLocation && (
          <p className="muted">Select a marker on the map to see details.</p>
        )}
        {loading && <p className="muted">Loading…</p>}
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        {data && (
          <dl className="data-list">
            {Object.entries(data).map(([key, value]) => (
              <div key={key}>
                <dt>{key}</dt>
                <dd>
                  {typeof value === "string" ? value : JSON.stringify(value, null, 2)}
                </dd>
              </div>
            ))}
          </dl>
        )}
      </aside>
    </div>
  );
}

export default App;
