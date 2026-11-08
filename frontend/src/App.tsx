import { useCallback, useEffect, useRef, useState } from "react";
import "./App.css";

import ChatBox from "./components/Chat/ChatBox";
import InteractiveMap from "./components/Map/InteractiveMap";
import WeatherCard from "./components/Weather/WeatherCard";
import { locations, type MapLocation } from "./data/locations";
import {
  fetchLocationData,
  fetchMonuments,
  type LocationData,
} from "./services/locationApi";

function App() {
  const [selectedLocation, setSelectedLocation] = useState<MapLocation | null>(null);
  const [data, setData] = useState<LocationData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [monuments, setMonuments] = useState<MapLocation[]>([]);
  const [monumentsError, setMonumentsError] = useState(false);

  // Only the most recent click may update state; earlier in-flight requests are aborted.
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => () => abortRef.current?.abort(), []);

  useEffect(() => {
    const controller = new AbortController();

    fetchMonuments(controller.signal)
      .then(setMonuments)
      .catch((err) => {
        if (controller.signal.aborted) return;
        console.error(err);
        setMonumentsError(true);
      });

    return () => controller.abort();
  }, []);

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
          monuments={monuments}
          selectedLocation={selectedLocation}
          onLocationClick={handleLocationClick}
        />
      </main>

      <aside className="info-panel">
        <header className="brand">
          <span className="brand-mark" aria-hidden="true" />
          <div>
            <h1>Atriensis Danubii</h1>
            <p>AI concierge for Upper Austria</p>
          </div>
        </header>

        <p className="eyebrow">Destinations</p>
        <ul className="chips">
          {locations.map((location) => (
            <li key={location.id}>
              <button
                type="button"
                className="chip"
                aria-pressed={location.id === selectedLocation?.id}
                onClick={() => handleLocationClick(location)}
              >
                {location.name}
              </button>
            </li>
          ))}
        </ul>

        {(monuments.length > 0 || monumentsError) && (
          <p className="monument-count">
            {monumentsError
              ? "Monuments could not be loaded."
              : `${monuments.length} monuments on the map`}
          </p>
        )}

        <section className="details" aria-live="polite">
          {selectedLocation ? (
            <>
              <h2>{selectedLocation.name}</h2>
              {selectedLocation.category && (
                <p className="meta">
                  <span className="tag">
                    {selectedLocation.category.replace(/_/g, " ")}
                  </span>
                  {selectedLocation.address}
                  {selectedLocation.approximate && " (approximate position)"}
                </p>
              )}
            </>
          ) : (
            <p className="empty">Pick a destination to see what's there.</p>
          )}

          {loading && (
            <div className="skeleton" aria-label="Loading">
              <span />
              <span />
              <span />
            </div>
          )}

          {error && selectedLocation && (
            <div className="error-card" role="alert">
              <p>{error}</p>
              <button
                type="button"
                className="retry"
                onClick={() => handleLocationClick(selectedLocation)}
              >
                Try again
              </button>
            </div>
          )}

          {data && <WeatherCard weather={data.weather} />}
        </section>

        <ChatBox location={selectedLocation} />
      </aside>
    </div>
  );
}

export default App;
