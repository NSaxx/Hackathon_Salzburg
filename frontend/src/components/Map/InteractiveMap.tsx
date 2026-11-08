import { memo, useEffect, useMemo } from "react";
import {
  CircleMarker,
  MapContainer,
  Marker,
  Polygon,
  TileLayer,
  Tooltip,
  useMap,
  ZoomControl,
} from "react-leaflet";

import L from "leaflet";

import type { MapLocation } from "../../data/locations";
import { upperAustriaBoundary } from "../../data/upperAustria";

const UPPER_AUSTRIA_BOUNDS = L.latLngBounds(upperAustriaBoundary);
const MAX_BOUNDS = UPPER_AUSTRIA_BOUNDS.pad(0.02);

// Everything outside Upper Austria is covered by a rectangle with the state cut out as a hole.
const OUTSIDE_MASK: L.LatLngExpression[][] = [
  [
    [40, 5],
    [40, 22],
    [56, 22],
    [56, 5],
  ],
  upperAustriaBoundary,
];

// The fill colour comes from the theme, see .map-mask in App.css.
const MASK_STYLE: L.PathOptions = {
  className: "map-mask",
  stroke: false,
  fillOpacity: 1,
};
const BORDER_STYLE: L.PathOptions = {
  color: "#2563eb",
  weight: 2,
  fill: false,
};

const SELECTED_MIN_ZOOM = 10;

function MapResizeHandler() {
  const map = useMap();

  useEffect(() => {
    const observer = new ResizeObserver(() => {
      map.invalidateSize({
        pan: false,
        animate: false,
      });
      // Don't allow zooming out further than needed to show the whole state.
      map.setMinZoom(map.getBoundsZoom(MAX_BOUNDS));
    });

    observer.observe(map.getContainer());

    return () => observer.disconnect();
  }, [map]);

  return null;
}

function FlyToSelected({ location }: { location: MapLocation | null }) {
  const map = useMap();

  useEffect(() => {
    if (!location) return;

    const target: L.LatLngTuple = [location.latitude, location.longitude];
    const zoom = Math.max(map.getZoom(), SELECTED_MIN_ZOOM);

    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      map.setView(target, zoom, { animate: false });
    } else {
      map.flyTo(target, zoom, { duration: 0.8 });
    }
  }, [map, location]);

  return null;
}

const pinOptions: L.DivIconOptions = {
  html: "<span></span>",
  iconSize: [28, 28],
  iconAnchor: [14, 14],
  tooltipAnchor: [0, -14],
};

const defaultIcon = L.divIcon({ ...pinOptions, className: "map-pin" });
const selectedIcon = L.divIcon({
  ...pinOptions,
  className: "map-pin map-pin--selected",
});

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
      alt={location.name}
      eventHandlers={eventHandlers}
    >
      <Tooltip direction="top">{location.name}</Tooltip>
    </Marker>
  );
});

// Hundreds of monuments are drawn on one shared canvas instead of one DOM node each.
const monumentRenderer = L.canvas({ tolerance: 6 });
const MONUMENT_STYLE: L.PathOptions = {
  color: "#ffffff",
  weight: 1,
  fillColor: "#0d9488",
  fillOpacity: 0.9,
};

interface MonumentPointsProps {
  monuments: MapLocation[];
  onLocationClick: (location: MapLocation) => void;
}

const MonumentPoints = memo(function MonumentPoints({
  monuments,
  onLocationClick,
}: MonumentPointsProps) {
  return monuments.map((monument) => (
    <CircleMarker
      key={monument.id}
      center={[monument.latitude, monument.longitude]}
      radius={5}
      renderer={monumentRenderer}
      pathOptions={MONUMENT_STYLE}
      eventHandlers={{ click: () => onLocationClick(monument) }}
    >
      <Tooltip direction="top">{monument.name}</Tooltip>
    </CircleMarker>
  ));
});

interface Props {
  locations: MapLocation[];
  monuments: MapLocation[];
  selectedLocation: MapLocation | null;
  onLocationClick: (location: MapLocation) => void;
}

export default function InteractiveMap({
  locations,
  monuments,
  selectedLocation,
  onLocationClick,
}: Props) {
  const selectedMonument =
    selectedLocation && !locations.some(({ id }) => id === selectedLocation.id)
      ? selectedLocation
      : null;

  return (
    <MapContainer
      bounds={UPPER_AUSTRIA_BOUNDS}
      maxZoom={14}
      zoomSnap={0.25}
      maxBounds={MAX_BOUNDS}
      maxBoundsViscosity={1.0}
      zoomControl={false}
      style={{
        height: "100%",
        width: "100%",
      }}
    >
      <MapResizeHandler />
      <FlyToSelected location={selectedLocation} />
      <ZoomControl position="bottomleft" />
      <TileLayer
        attribution="&copy; OpenStreetMap contributors"
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        maxZoom={14}
        keepBuffer={4}
      />

      <Polygon positions={OUTSIDE_MASK} pathOptions={MASK_STYLE} interactive={false} />
      <Polygon
        positions={upperAustriaBoundary}
        pathOptions={BORDER_STYLE}
        interactive={false}
      />

      <MonumentPoints monuments={monuments} onLocationClick={onLocationClick} />

      {locations.map((location) => (
        <LocationMarker
          key={location.id}
          location={location}
          selected={location.id === selectedLocation?.id}
          onLocationClick={onLocationClick}
        />
      ))}

      {selectedMonument && (
        <LocationMarker
          location={selectedMonument}
          selected
          onLocationClick={onLocationClick}
        />
      )}
    </MapContainer>
  );
}
