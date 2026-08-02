import { useMemo } from "react";
import { divIcon } from "leaflet";
import { Marker } from "react-leaflet";
import type { State } from "./api";
import { useTheme } from "./theme";

const PLANE_SVG = (color: string) =>
  `<svg viewBox="0 0 24 24" width="20" height="20" fill="${color}" xmlns="http://www.w3.org/2000/svg"><path d="M21 16v-2l-8-5V3.5A1.5 1.5 0 0 0 11.5 2 1.5 1.5 0 0 0 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z"/></svg>`;

function createPlaneIcon(heading: number | null, color: string) {
  const deg = heading != null ? heading : 0;
  return divIcon({
    className: "",
    iconSize: [20, 20],
    iconAnchor: [10, 10],
    html: `<div style="transform:rotate(${deg}deg);width:20px;height:20px;display:flex;align-items:center;justify-content:center">${PLANE_SVG(color)}</div>`,
  });
}

function createSelectedIcon(heading: number | null, fill: string, glow: string, size: number) {
  const deg = heading != null ? heading : 0;
  const svg = PLANE_SVG(fill);
  return divIcon({
    className: "",
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    html: `<div style="
      transform:rotate(${deg}deg);
      width:${size}px;height:${size}px;
      display:flex;
      align-items:center;
      justify-content:center;
      filter:drop-shadow(0 0 8px ${glow});
      background:radial-gradient(circle, rgba(255,255,255,0.08) 0%, rgba(0,0,0,0) 70%);
      border-radius:50%;
      transition:transform 0.3s;
    ">${svg}</div>`,
  });
}

function quantizeHeading(heading: number | null): number {
  return heading == null ? 0 : Math.round(heading / 5) * 5;
}

interface Props {
  states: State[];
  selectedIcao24: string | null;
  onSelect: (icao24: string | null) => void;
}

export default function AircraftMarkers({ states, selectedIcao24, onSelect }: Props) {
  const { theme } = useTheme();

  const iconCache = useMemo(() => {
    const cache = new Map<string, ReturnType<typeof divIcon>>();
    return (heading: number | null, color: string) => {
      const key = `${quantizeHeading(heading)}_${color}`;
      if (!cache.has(key)) {
        cache.set(key, createPlaneIcon(heading, color));
      }
      return cache.get(key)!;
    };
  }, []);

  const selectedIconCache = useMemo(() => {
    const cache = new Map<number, ReturnType<typeof divIcon>>();
    return (heading: number | null) => {
      const key = quantizeHeading(heading);
      if (!cache.has(key)) {
        cache.set(
          key,
          createSelectedIcon(heading, theme.selectedMarker.fill, theme.selectedMarker.glow, 36),
        );
      }
      return cache.get(key)!;
    };
  }, [theme.selectedMarker.fill, theme.selectedMarker.glow]);

  const list = selectedIcao24
    ? states.filter((s) => s.icao24 === selectedIcao24)
    : states;

  return (
    <>
      {list.map((s) => (
        <Marker
          key={s.icao24}
          position={[s.latitude, s.longitude]}
          icon={s.icao24 === selectedIcao24 ? selectedIconCache(s.heading) : iconCache(s.heading, theme.altColor(s.baro_altitude))}
          eventHandlers={{
            click: () => onSelect(s.icao24),
          }}
        />
      ))}
    </>
  );
}
