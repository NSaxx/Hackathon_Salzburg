import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";

import L from "leaflet";

import type { MapLocation } from "../../data/locations";
import { useEffect } from "react";
import { useMap } from "react-leaflet";

function MapResizeHandler() {
  const map = useMap();

  useEffect(() => {
    const observer = new ResizeObserver(() => {
      map.invalidateSize({
        pan: false,
        animate: false,
      });
    });

    observer.observe(map.getContainer());

    return () => observer.disconnect();
  }, [map]);

  return null;
}

interface Props {
  locations: MapLocation[];
  selectedLocation: string | null;
  onLocationClick: (location: MapLocation) => void;
}

const defaultIcon = new L.Icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

export default function InteractiveMap({ locations, onLocationClick }: Props) {
  return (
    <MapContainer
      center={[48.2, 13.9]}
      zoom={8}
      minZoom={8}
      maxZoom={14}
      maxBounds={[
        [47.4, 12.6], // Southwest
        [48.9, 14.9], // Northeast
      ]}
      maxBoundsViscosity={1.0}
      style={{
        height: "100%",
        width: "100%",
      }}
    >
      <MapResizeHandler />
      <TileLayer
        attribution="&copy; OpenStreetMap contributors"
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {locations.map((location) => (
        <Marker
          key={location.id}
          position={[location.latitude, location.longitude]}
          icon={defaultIcon}
          eventHandlers={{
            click: () => onLocationClick(location),
          }}
        >
          <Popup>{location.name}</Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}
