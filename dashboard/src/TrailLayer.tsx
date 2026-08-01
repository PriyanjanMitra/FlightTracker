import { useEffect, useState } from "react";
import { Polyline } from "react-leaflet";
import { fetchTrails, type TrailPoint } from "./api";

interface Props {
  icao24: string | null;
}

export default function TrailLayer({ icao24 }: Props) {
  const [points, setPoints] = useState<TrailPoint[]>([]);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!icao24) {
      setPoints([]);
      setError(false);
      return;
    }
    let cancelled = false;
    setError(false);
    fetchTrails(15)
      .then((data) => {
        if (!cancelled) {
          setPoints(data[icao24] ?? []);
        }
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });
    return () => {
      cancelled = true;
    };
  }, [icao24]);

  if (error) return null;
  if (points.length < 2) return null;

  const positions: [number, number][] = points.map((p) => [p.lat, p.lon]);
  return <Polyline positions={positions} color="#2563eb" weight={2} opacity={0.7} />;
}
