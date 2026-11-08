export interface MapLocation {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  category?: string;
  address?: string;
  // True when the position is only known to village or municipality level.
  approximate?: boolean;
}

export const locations: MapLocation[] = [
  {
    id: "location-1",
    name: "Linz",
    latitude: 48.3069,
    longitude: 14.2858,
  },
  {
    id: "location-2",
    name: "Wels",
    latitude: 48.1575,
    longitude: 14.028,
  },
  {
    id: "location-3",
    name: "Steyr",
    latitude: 48.0427,
    longitude: 14.4213,
  },
  {
    id: "location-4",
    name: "Gmunden",
    latitude: 47.9184,
    longitude: 13.7993,
  },
];
