import { memo, useEffect, useMemo, useState } from "react";
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
import {
  fetchMapPoints,
  type MapPoint,
  type MapPoints,
  type PointDataset,
} from "../../services/locationApi";

const NO_POINTS: MapPoint[] = [];

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

// The most points drawn at once; the backend spreads them evenly over the view.
const MAX_VISIBLE_POINTS = 150;
const RELOAD_DELAY_MS = 150;

const DATASETS: Record<PointDataset, { label: string; color: string }> = {
  gastronomy: { label: "Gastronomy", color: "#e11d48" },
  events: { label: "Events", color: "#9333ea" },
  tours: { label: "Tours", color: "#16a34a" },
  monuments: { label: "Monuments", color: "#b45309" },
};

const pointStyles = Object.fromEntries(
  Object.entries(DATASETS).map(([dataset, { color }]) => [
    dataset,
    { color: "#ffffff", weight: 1, fillColor: color, fillOpacity: 0.9 },
  ]),
) as Record<PointDataset, L.PathOptions>;

interface PointLoaderProps {
  onLoaded: (points: MapPoints) => void;
  onFailed: (failed: boolean) => void;
}

function PointLoader({ onLoaded, onFailed }: PointLoaderProps) {
  const map = useMap();

  useEffect(() => {
    let controller: AbortController | null = null;
    let timer: ReturnType<typeof setTimeout>;

    async function load() {
      controller?.abort();
      const current = new AbortController();
      controller = current;
      const bounds = map.getBounds();

      try {
        const points = await fetchMapPoints(
          {
            south: bounds.getSouth(),
            west: bounds.getWest(),
            north: bounds.getNorth(),
            east: bounds.getEast(),
          },
          MAX_VISIBLE_POINTS,
          current.signal,
        );
        onLoaded(points);
        onFailed(false);
      } catch (err) {
        if (current.signal.aborted) return;
        console.error(err);
        onFailed(true);
      }
    }

    function scheduleLoad() {
      clearTimeout(timer);
      timer = setTimeout(load, RELOAD_DELAY_MS);
    }

    scheduleLoad();
    map.on("moveend", scheduleLoad);

    return () => {
      map.off("moveend", scheduleLoad);
      clearTimeout(timer);
      controller?.abort();
    };
  }, [map, onLoaded, onFailed]);

  return null;
}

// All points are drawn on one shared canvas instead of one DOM node each.
const pointRenderer = L.canvas({ tolerance: 6 });

interface PointMarkersProps {
  points: MapPoint[];
  onLocationClick: (location: MapLocation) => void;
}

const PointMarkers = memo(function PointMarkers({
  points,
  onLocationClick,
}: PointMarkersProps) {
  return points.map((point) => (
    <CircleMarker
      key={point.id}
      center={[point.latitude, point.longitude]}
      radius={5}
      renderer={pointRenderer}
      pathOptions={pointStyles[point.dataset]}
      eventHandlers={{ click: () => onLocationClick(point) }}
    >
      <Tooltip direction="top">{point.name}</Tooltip>
    </CircleMarker>
  ));
});

function MapLegend({ result, failed }: { result: MapPoints | null; failed: boolean }) {
  let status = "";
  if (failed) {
    status = "Places could not be loaded.";
  } else if (result && result.shown < result.numberOfItems) {
    status = `Showing ${result.shown} of ${result.numberOfItems.toLocaleString("en")}. Zoom in for more.`;
  } else if (result) {
    status = `${result.numberOfItems.toLocaleString("en")} places in view`;
  }

  return (
    <div className="map-legend">
      <ul>
        {Object.values(DATASETS).map(({ label, color }) => (
          <li key={label}>
            <span className="legend-dot" style={{ background: color }} />
            {label}
          </li>
        ))}
      </ul>
      {status && <p role="status">{status}</p>}
    </div>
  );
}

interface Props {
  locations: MapLocation[];
  selectedLocation: MapLocation | null;
  onLocationClick: (location: MapLocation) => void;
}

export default function InteractiveMap({
  locations,
  selectedLocation,
  onLocationClick,
}: Props) {
  const [result, setResult] = useState<MapPoints | null>(null);
  const [failed, setFailed] = useState(false);

  const selectedPoint =
    selectedLocation && !locations.some(({ id }) => id === selectedLocation.id)
      ? selectedLocation
      : null;

  return (
    <>
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

        <Polygon
          positions={OUTSIDE_MASK}
          pathOptions={MASK_STYLE}
          interactive={false}
        />
        <Polygon
          positions={upperAustriaBoundary}
          pathOptions={BORDER_STYLE}
          interactive={false}
        />

        <PointLoader onLoaded={setResult} onFailed={setFailed} />
        <PointMarkers
          points={result?.points ?? NO_POINTS}
          onLocationClick={onLocationClick}
        />

        {locations.map((location) => (
          <LocationMarker
            key={location.id}
            location={location}
            selected={location.id === selectedLocation?.id}
            onLocationClick={onLocationClick}
          />
        ))}

        {selectedPoint && (
          <LocationMarker
            location={selectedPoint}
            selected
            onLocationClick={onLocationClick}
          />
        )}
      </MapContainer>
      <MapLegend result={result} failed={failed} />
    </>
  );
}
