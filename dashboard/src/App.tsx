import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { MapContainer, TileLayer, useMap, useMapEvents } from "react-leaflet";
import { fetchStates, type State } from "./api";
import AircraftMarkers from "./AircraftMarkers";
import Sidebar from "./Sidebar";
import TrailLayer from "./TrailLayer";
import SelectionDetail from "./SelectionDetail";

const DARK_TILES = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";
const DARK_ATTR = '&copy; <a href="https://carto.com/">CARTO</a>';

export default function App() {
  const [states, setStates] = useState<State[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const pollingRef = useRef(false);

  const poll = useCallback(async () => {
    if (pollingRef.current) return;
    pollingRef.current = true;
    try {
      const data = await fetchStates();
      setStates(data);
      setLastUpdated(new Date().toLocaleTimeString());
      setError(null);
    } catch {
      setError("Cannot reach backend. Make sure the server is running.");
    } finally {
      setLoading(false);
      pollingRef.current = false;
    }
  }, []);

  useEffect(() => {
    poll();
    const id = setInterval(poll, 2_000);
    return () => clearInterval(id);
  }, [poll]);

  const selectedState = useMemo(
    () => states.find((s) => s.icao24 === selected) ?? null,
    [states, selected],
  );

  const handleSelect = useCallback(
    (icao24: string | null) => {
      setSelected(icao24);
    },
    [],
  );

  return (
    <div style={{ display: "flex", height: "100%", width: "100%", background: "#0f172a" }}>
      <Sidebar
        states={states}
        selectedIcao24={selected}
        onSelect={handleSelect}
      />
      <div style={{ flex: 1, position: "relative" }}>
        <MapContainer
          center={[20, 0]}
          zoom={2}
          scrollWheelZoom={true}
          doubleClickZoom={false}
          style={{ height: "100%", width: "100%" }}
          zoomControl={false}
        >
          <TileLayer
            attribution={DARK_ATTR}
            url={DARK_TILES}
          />
          <MapClickHandler onSelect={handleSelect} />
          <AircraftMarkers states={states} selectedIcao24={selected} onSelect={handleSelect} />
          <TrailLayer icao24={selected} />
          {selectedState && <MapFlyTo state={selectedState} />}
        </MapContainer>

        <div style={styles.topRight}>
          <span style={styles.count}>{states.length} aircraft</span>
          {lastUpdated && <span style={styles.ts}>{lastUpdated}</span>}
        </div>

        {loading && (
          <div style={styles.spinnerOverlay}>
            <div style={styles.spinner} />
            <span style={{ marginTop: 8, color: "#94a3b8" }}>Loading flight data…</span>
          </div>
        )}

        {error && !loading && (
          <div style={styles.banner}>
            {error}
            <button style={styles.retryBtn} onClick={poll}>Retry</button>
          </div>
        )}

        <SelectionDetail state={selectedState} onClose={() => setSelected(null)} />
      </div>
    </div>
  );
}

function MapFlyTo({ state }: { state: State }) {
  const map = useMap();
  const lastIcao = useRef<string | null>(null);

  useEffect(() => {
    if (state.icao24 === lastIcao.current) return;
    lastIcao.current = state.icao24;
    map.flyTo([state.latitude, state.longitude], 8, { duration: 1 });
  }, [state.icao24, state.latitude, state.longitude, map]);

  return null;
}

function MapClickHandler({ onSelect }: { onSelect: (icao24: string | null) => void }) {
  useMapEvents({
    click() {
      onSelect(null);
    },
  });
  return null;
}

const styles: Record<string, React.CSSProperties> = {
  topRight: {
    position: "absolute",
    top: 12,
    right: 12,
    zIndex: 1000,
    display: "flex",
    gap: 10,
    alignItems: "center",
  },
  count: {
    background: "rgba(15,23,42,0.85)",
    color: "#94a3b8",
    padding: "5px 12px",
    borderRadius: 6,
    fontSize: 12,
    fontWeight: 600,
    backdropFilter: "blur(4px)",
    border: "1px solid #1e293b",
  },
  ts: {
    background: "rgba(15,23,42,0.85)",
    color: "#64748b",
    padding: "5px 12px",
    borderRadius: 6,
    fontSize: 11,
    fontFamily: "monospace",
    backdropFilter: "blur(4px)",
    border: "1px solid #1e293b",
  },
  spinnerOverlay: {
    position: "absolute",
    inset: 0,
    zIndex: 2000,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    background: "rgba(15,23,42,0.8)",
    fontSize: 14,
  },
  spinner: {
    width: 36,
    height: 36,
    border: "3px solid #1e293b",
    borderTop: "3px solid #3b82f6",
    borderRadius: "50%",
    animation: "spin 0.8s linear infinite",
  },
  banner: {
    position: "absolute",
    top: 60,
    right: 12,
    zIndex: 1000,
    background: "rgba(127,29,29,0.9)",
    color: "#fca5a5",
    padding: "8px 14px",
    borderRadius: 6,
    fontSize: 12,
    display: "flex",
    alignItems: "center",
    gap: 10,
    backdropFilter: "blur(4px)",
    border: "1px solid #7f1d1d",
  },
  retryBtn: {
    background: "#dc2626",
    color: "#fff",
    border: "none",
    borderRadius: 4,
    padding: "3px 10px",
    fontSize: 11,
    cursor: "pointer",
  },
};
