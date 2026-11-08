import { memo, useEffect, useMemo } from "react";
import { MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";

import L from "leaflet";
import iconUrl from "leaflet/dist/images/marker-icon.png";
import iconRetinaUrl from "leaflet/dist/images/marker-icon-2x.png";
import shadowUrl from "leaflet/dist/images/marker-shadow.png";

import type { MapLocation } from "../../data/locations";

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

// Icons are bundled by Vite instead of fetched from unpkg on every page load.
const iconOptions: L.IconOptions = {
  iconUrl,
  iconRetinaUrl,
  shadowUrl,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
};

const defaultIcon = new L.Icon(iconOptions);
const selectedIcon = new L.Icon({ ...iconOptions, className: "marker-selected" });

const MAP_CENTER: L.LatLngExpression = [48.2, 13.9];
const MAX_BOUNDS: L.LatLngBoundsExpression = [
  [47.4, 12.6], // Southwest
  [48.9, 14.9], // Northeast
];

interface LocationMarkerProps {
  location: MapLocation;
  selected: boolean;
  onLocationClick: (location: MapLocation) => void;
}

// Memoised so a state change in App (loading, data, ...) doesn't re-render every marker.
const LocationMarker = memo(function LocationMarker({
  location,
  selected,
  onLocationClick,
}: LocationMarkerProps) {
  const eventHandlers = useMemo(
    () => ({ click: () => onLocationClick(location) }),
    [location, onLocationClick],
  );

  return (
    <Marker
      position={[location.latitude, location.longitude]}
      icon={selected ? selectedIcon : defaultIcon}
      eventHandlers={eventHandlers}
    >
      <Popup>{location.name}</Popup>
    </Marker>
  );
});

interface Props {
  locations: MapLocation[];
  selectedLocationId: string | null;
  onLocationClick: (location: MapLocation) => void;
}

export default function InteractiveMap({
  locations,
  selectedLocationId,
  onLocationClick,
}: Props) {
  return (
    <MapContainer
      center={MAP_CENTER}
      zoom={8}
      minZoom={8}
      maxZoom={14}
      maxBounds={MAX_BOUNDS}
      maxBoundsViscosity={1.0}
      style={{
        height: "100%",
        width: "100%",
      }}
    >
      <MapResizeHandler />
      <TileLayer
        attribution="&copy; OpenStreetMap contributors"
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        maxZoom={14}
        keepBuffer={4}
      />

      {locations.map((location) => (
        <LocationMarker
          key={location.id}
          location={location}
          selected={location.id === selectedLocationId}
          onLocationClick={onLocationClick}
        />
      ))}
    </MapContainer>
  );
}
