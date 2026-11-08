import { useState } from "react";
import "./App.css";

import InteractiveMap from "./components/Map/InteractiveMap";
import { locations, type MapLocation } from "./data/locations";
import { fetchLocationData } from "./services/locationApi";

function App() {
  const [selectedLocation, setSelectedLocation] = useState<string | null>(null);

  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  async function handleLocationClick(location: any) {
    setSelectedLocation(location.id);
    setLoading(true);
    setData(null);

    try {
      const result = await fetchLocationData(location.latitude, location.longitude);

      setData(result);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <main className="map-container">
        <InteractiveMap
          locations={locations}
          selectedLocation={selectedLocation}
          onLocationClick={handleLocationClick}
        />
      </main>

      <aside className="info-panel">
        <h2>Location information</h2>

        {/* Location information */}
      </aside>
    </div>
  );
}

export default App;
