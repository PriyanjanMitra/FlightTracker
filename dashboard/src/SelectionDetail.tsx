import { useEffect, useState } from "react";
import type { State, FlightInfo } from "./api";
import { fetchFlightInfo } from "./api";

function statusLabel(vr: number | null): { text: string; color: string } {
  if (vr == null) return { text: "—", color: "#6b7280" };
  if (vr > 5) return { text: "Climbing", color: "#22c55e" };
  if (vr < -5) return { text: "Descending", color: "#ef4444" };
  return { text: "Level", color: "#3b82f6" };
}

function formatTime(ts: number): string {
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString();
}

interface Props {
  state: State | null;
  onClose: () => void;
}

export default function SelectionDetail({ state, onClose }: Props) {
  const [flightInfo, setFlightInfo] = useState<FlightInfo | null>(null);

  useEffect(() => {
    setFlightInfo(null);
    if (!state?.callsign) return;
    let cancelled = false;
    fetchFlightInfo({
      callsign: state.callsign,
      latitude: state.latitude,
      longitude: state.longitude,
      heading: state.heading ?? undefined,
      vertical_rate: state.vertical_rate ?? undefined,
    })
      .then((info) => {
        if (!cancelled) setFlightInfo(info);
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [state?.callsign, state?.latitude, state?.longitude, state?.heading, state?.vertical_rate]);

  if (!state) return null;

  const vr = statusLabel(state.vertical_rate);

  return (
    <div style={styles.overlay} onClick={onClose}>
      <div style={styles.panel} onClick={(e) => e.stopPropagation()}>
        <button style={styles.close} onClick={onClose}>✕</button>

        <div style={styles.callsign}>{state.callsign || "—"}</div>

        {flightInfo?.origin && flightInfo?.destination && (
          <div style={styles.route}>
            <span style={styles.airportCode}>{flightInfo.origin.iata}</span>
            <span style={styles.routeArrow}>→</span>
            <span style={styles.airportCode}>{flightInfo.destination.iata}</span>
          </div>
        )}

        <div style={styles.grid}>
          <div style={styles.gridItem}>
            <span style={styles.label}>Altitude</span>
            <span style={styles.value}>{state.baro_altitude != null ? `${Math.round(state.baro_altitude)} m` : "—"}</span>
          </div>
          <div style={styles.gridItem}>
            <span style={styles.label}>Speed</span>
            <span style={styles.value}>{state.velocity != null ? `${Math.round(state.velocity * 1.944)} kn` : "—"}</span>
          </div>
          <div style={styles.gridItem}>
            <span style={styles.label}>Heading</span>
            <span style={styles.value}>{state.heading != null ? `${Math.round(state.heading)}°` : "—"}</span>
          </div>
          <div style={styles.gridItem}>
            <span style={styles.label}>V/S</span>
            <span style={{ ...styles.value, color: vr.color }}>{vr.text}</span>
          </div>
        </div>

        <div style={styles.meta}>
          <span style={styles.metaItem}><span style={styles.metaLabel}>Country</span> {state.origin_country}</span>
          <span style={styles.metaItem}><span style={styles.metaLabel}>ICAO</span> {state.icao24}</span>
          <span style={styles.metaItem}><span style={styles.metaLabel}>Category</span> {state.category_label || "—"}</span>
          <span style={styles.metaItem}><span style={styles.metaLabel}>Last contact</span> {formatTime(state.last_contact)}</span>
        </div>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  overlay: {
    position: "absolute",
    inset: 0,
    zIndex: 1200,
    display: "flex",
    alignItems: "flex-end",
    justifyContent: "center",
    background: "rgba(0,0,0,0.3)",
  },
  panel: {
    width: "100%",
    maxWidth: 480,
    background: "#0f172a",
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    padding: "20px 24px 28px",
    color: "#e2e8f0",
    fontFamily: "system-ui, -apple-system, sans-serif",
    position: "relative",
    boxShadow: "0 -4px 24px rgba(0,0,0,0.5)",
  },
  close: {
    position: "absolute",
    top: 14,
    right: 16,
    background: "none",
    border: "none",
    color: "#64748b",
    fontSize: 18,
    cursor: "pointer",
    padding: 4,
    lineHeight: 1,
  },
  callsign: {
    fontSize: 22,
    fontWeight: 700,
    letterSpacing: "0.02em",
    marginBottom: 4,
  },
  route: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    marginBottom: 16,
    fontSize: 14,
  },
  airportCode: {
    fontWeight: 700,
    color: "#60a5fa",
    fontSize: 16,
  },
  routeArrow: {
    color: "#64748b",
    fontSize: 14,
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "1px",
    background: "#1e293b",
    borderRadius: 8,
    overflow: "hidden",
    marginBottom: 14,
  },
  gridItem: {
    background: "#0f172a",
    padding: "10px 14px",
  },
  label: {
    display: "block",
    fontSize: 10,
    color: "#64748b",
    textTransform: "uppercase" as const,
    letterSpacing: "0.05em",
    marginBottom: 2,
  },
  value: {
    fontSize: 16,
    fontWeight: 600,
    color: "#e2e8f0",
    fontFamily: "monospace",
  },
  meta: {
    display: "flex",
    flexWrap: "wrap",
    gap: "6px 16px",
    fontSize: 11,
    color: "#94a3b8",
  },
  metaItem: {
    whiteSpace: "nowrap" as const,
  },
  metaLabel: {
    color: "#64748b",
  },
};
