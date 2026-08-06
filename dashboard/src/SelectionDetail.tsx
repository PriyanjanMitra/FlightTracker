import { useEffect, useState } from "react";
import type { State, FlightInfo } from "./api";
import { fetchFlightInfo } from "./api";
import { useTheme } from "./theme";

function formatTime(ts: number): string {
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString();
}

interface Props {
  state: State | null;
  onClose: () => void;
}

export default function SelectionDetail({ state, onClose }: Props) {
  const { theme } = useTheme();
  const [flightInfo, setFlightInfo] = useState<FlightInfo | null>(null);

  useEffect(() => {
    setFlightInfo(null);
    if (!state?.callsign) return;
    let cancelled = false;
    fetchFlightInfo({
      icao24: state.icao24,
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
  }, [state?.icao24, state?.callsign]);

  if (!state) return null;

  const vr = theme.status(state.vertical_rate);
  const s = styles(theme);

  return (
    <div style={s.overlay} onClick={onClose}>
      <div style={s.panel} onClick={(e) => e.stopPropagation()}>
        <button style={s.close} onClick={onClose}>✕</button>

        <div style={s.kicker}>{theme.name === "souls" ? "ESTUS KIND LED" : "FLIGHT INFO"}</div>
        <div style={s.callsign}>{state.callsign || (theme.name === "souls" ? "Nameless Soul" : "—")}</div>

        {flightInfo?.aircraft && (
          <div style={s.aircraftLine}>
            <span style={s.aircraftType}>
              {flightInfo.aircraft.type || flightInfo.aircraft.icao_type || "Aircraft"}
            </span>
            {flightInfo.aircraft.manufacturer && (
              <span style={s.aircraftMfg}>{flightInfo.aircraft.manufacturer}</span>
            )}
            {flightInfo.aircraft.registration && (
              <span style={s.aircraftReg}>{flightInfo.aircraft.registration}</span>
            )}
          </div>
        )}

        {flightInfo?.airline?.name && (
          <div style={s.airline}>{flightInfo.airline.name}</div>
        )}

        {(flightInfo?.origin || flightInfo?.destination) && (
          <div style={s.route}>
            <div style={s.routeEnd}>
              <span style={s.airportCode}>{flightInfo?.origin?.iata ?? "—"}</span>
              <span style={s.airportName}>{flightInfo?.origin?.name ?? "Unknown"}</span>
            </div>
            <span style={s.routeArrow}>→</span>
            <div style={s.routeEnd}>
              <span style={s.airportCode}>{flightInfo?.destination?.iata ?? "—"}</span>
              <span style={s.airportName}>{flightInfo?.destination?.name ?? "Unknown"}</span>
            </div>
          </div>
        )}

        <div style={s.grid}>
          <div style={s.gridItem}>
            <span style={s.label}>Altitude</span>
            <span style={s.value}>{state.baro_altitude != null ? `${Math.round(state.baro_altitude)} ft` : "—"}</span>
          </div>
          <div style={s.gridItem}>
            <span style={s.label}>Speed</span>
            <span style={s.value}>{state.velocity != null ? `${Math.round(state.velocity * 1.944)} kn` : "—"}</span>
          </div>
          <div style={s.gridItem}>
            <span style={s.label}>Heading</span>
            <span style={s.value}>{state.heading != null ? `${Math.round(state.heading)}°` : "—"}</span>
          </div>
          <div style={s.gridItem}>
            <span style={s.label}>Vertical</span>
            <span style={{ ...s.value, color: vr.color }}>{vr.text}</span>
          </div>
        </div>

        <div style={s.meta}>
          <span style={s.metaItem}><span style={s.metaLabel}>Country</span> {state.origin_country}</span>
          <span style={s.metaItem}><span style={s.metaLabel}>ICAO</span> {state.icao24}</span>
          <span style={s.metaItem}><span style={s.metaLabel}>Category</span> {state.category_label || "—"}</span>
          <span style={s.metaItem}><span style={s.metaLabel}>Last contact</span> {formatTime(state.last_contact)}</span>
        </div>
      </div>
    </div>
  );
}

function styles(theme: ReturnType<typeof useTheme>["theme"]): Record<string, React.CSSProperties> {
  return {
    overlay: {
      position: "absolute",
      inset: 0,
      zIndex: 1200,
      display: "flex",
      alignItems: "flex-end",
      justifyContent: "center",
      background: "rgba(0,0,0,0.5)",
    },
    panel: {
      width: "100%",
      maxWidth: 480,
      background: theme.panelGrad,
      border: `1px solid ${theme.borderLight}`,
      borderBottom: "none",
      borderTopLeftRadius: 8,
      borderTopRightRadius: 8,
      padding: "22px 24px 28px",
      color: theme.text,
      fontFamily: theme.font,
      position: "relative",
      boxShadow: `0 -6px 30px rgba(0,0,0,0.8), 0 0 0 1px rgba(255,255,255,0.05)`,
    },
    close: {
      position: "absolute",
      top: 14,
      right: 16,
      background: "none",
      border: "none",
      color: theme.muted,
      fontSize: 18,
      cursor: "pointer",
      padding: 4,
      lineHeight: 1,
    },
    kicker: {
      fontSize: 10,
      color: theme.muted,
      letterSpacing: "0.25em",
      textTransform: "uppercase" as const,
      marginBottom: 6,
    },
    callsign: {
      fontSize: 24,
      fontWeight: 700,
      letterSpacing: "0.06em",
      color: theme.name === "souls" ? theme.accentText : theme.text,
      marginBottom: 4,
      textShadow: theme.name === "souls" ? "0 0 14px rgba(212,175,55,0.35)" : "none",
    },
    route: {
      display: "flex",
      alignItems: "center",
      gap: 12,
      marginBottom: 18,
      fontSize: 14,
    },
    routeEnd: {
      display: "flex",
      flexDirection: "column",
      gap: 2,
    },
    airportCode: {
      fontWeight: 700,
      color: theme.accent,
      fontSize: 18,
      letterSpacing: "0.1em",
    },
    airportName: {
      fontSize: 11,
      color: theme.muted,
      maxWidth: 170,
      whiteSpace: "nowrap" as const,
      overflow: "hidden",
      textOverflow: "ellipsis",
    },
    routeArrow: {
      color: theme.muted,
      fontSize: 14,
    },
    aircraftLine: {
      display: "flex",
      alignItems: "baseline",
      gap: 8,
      marginBottom: 2,
    },
    aircraftType: {
      fontWeight: 700,
      color: theme.text,
      fontSize: 14,
    },
    aircraftMfg: {
      fontSize: 11,
      color: theme.muted,
    },
    aircraftReg: {
      fontSize: 11,
      color: theme.accent,
    },
    airline: {
      fontSize: 12,
      color: theme.muted,
      marginBottom: 12,
    },
    grid: {
      display: "grid",
      gridTemplateColumns: "1fr 1fr",
      gap: "1px",
      background: theme.borderLight,
      borderRadius: 4,
      overflow: "hidden",
      marginBottom: 16,
    },
    gridItem: {
      background: theme.panel,
      padding: "12px 14px",
    },
    label: {
      display: "block",
      fontSize: 10,
      color: theme.muted,
      textTransform: "uppercase" as const,
      letterSpacing: "0.12em",
      marginBottom: 3,
    },
    value: {
      fontSize: 16,
      fontWeight: 600,
      color: theme.text,
      fontFamily: "monospace",
    },
    meta: {
      display: "flex",
      flexWrap: "wrap",
      gap: "6px 18px",
      fontSize: 11,
      color: theme.muted,
    },
    metaItem: {
      whiteSpace: "nowrap" as const,
    },
    metaLabel: {
      color: theme.muted,
      opacity: 0.7,
    },
  };
}
