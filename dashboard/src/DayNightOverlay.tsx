import { useEffect, useRef } from "react";
import { useMap } from "react-leaflet";
import terminator from "@joergdietrich/leaflet.terminator";

const UPDATE_MS = 60_000;

interface DayNightOverlayProps {
  color: string;
  fillColor: string;
  fillOpacity: number;
}

export default function DayNightOverlay({ color, fillColor, fillOpacity }: DayNightOverlayProps) {
  const map = useMap();
  const layerRef = useRef<ReturnType<typeof terminator> | null>(null);

  useEffect(() => {
    const layer = terminator({ color, fillColor, fillOpacity });
    layerRef.current = layer;
    layer.addTo(map);
    return () => {
      layer.remove();
      layerRef.current = null;
    };
  }, [map, color, fillColor, fillOpacity]);

  useEffect(() => {
    const id = setInterval(() => {
      layerRef.current?.setTime(new Date());
    }, UPDATE_MS);
    return () => clearInterval(id);
  }, []);

  return null;
}
