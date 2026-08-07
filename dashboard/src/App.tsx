import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { MapContainer, TileLayer, useMap, useMapEvents } from "react-leaflet";
import { fetchStates, type State } from "./api";
import { useTheme } from "./theme";
import AircraftMarkers from "./AircraftMarkers";
import DayNightOverlay from "./DayNightOverlay";
import Logo from "./Logo";
import Sidebar from "./Sidebar";
import { playThemeSwitchSound } from "./sound";
import ThemeSwitchOverlay from "./ThemeSwitchOverlay";
import TrailLayer from "./TrailLayer";
import SelectionDetail from "./SelectionDetail";

const DARK_TILES = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const DARK_ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

export default function App() {
  const { theme, themeName, toggleTheme } = useTheme();
  const [states, setStates] = useState<State[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [soulsOverlay, setSoulsOverlay] = useState(false);
  const pollingRef = useRef(false);
  const prevTheme = useRef(themeName);

  useEffect(() => {
    const enteringSouls = prevTheme.current === "radar" && themeName === "souls";
    prevTheme.current = themeName;
    if (enteringSouls) {
      setSoulsOverlay(true);
      playThemeSwitchSound();
    }
  }, [themeName]);

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
    const id = setInterval(poll, 60_000);
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

  const s = styles(theme);

  return (
    <div style={{ position: "relative", height: "100%", width: "100%", background: theme.bg }}>
      <div
        style={{
          display: "flex",
          height: "100%",
          width: "100%",
          filter: soulsOverlay ? "grayscale(1)" : "none",
          transition: "filter 1.5s ease-in-out",
        }}
      >
        <Sidebar
          states={states}
          selectedIcao24={selected}
          onSelect={handleSelect}
        />
        <div
          style={{
            flex: 1,
            position: "relative",
          }}
        >
        <MapContainer
          center={[20, 0]}
          zoom={3}
          maxBounds={[[-85, -180], [85, 180]]}
          maxBoundsViscosity={1.0}
          scrollWheelZoom={true}
          doubleClickZoom={false}
          style={{ height: "100%", width: "100%" }}
          zoomControl={false}
        >
          <FitWorldMinZoom />
          <TileLayer
            attribution={DARK_ATTR}
            url={DARK_TILES}
            className="dark-tiles"
          />
          <DayNightOverlay
            color={theme.name === "souls" ? "#000" : "transparent"}
            fillColor={theme.name === "souls" ? "#000" : "#050a18"}
            fillOpacity={0.25}
          />
          <MapClickHandler onSelect={handleSelect} />
          <AircraftMarkers states={states} selectedIcao24={selected} onSelect={handleSelect} />
          <TrailLayer icao24={selected} />
          {selectedState && <MapFlyTo state={selectedState} />}
        </MapContainer>

        <div style={s.topRight}>
          <span style={s.count}>{states.length} aircraft</span>
          {lastUpdated && <span style={s.ts}>{lastUpdated}</span>}
          <button
            style={{ ...s.themeBtn, color: theme.textBright }}
            onClick={toggleTheme}
            title={`Switch to ${theme.name === "radar" ? "Bonfire" : "Radar"} theme`}
          >
            <Logo themeName={theme.name === "radar" ? "souls" : "radar"} size={18} />
          </button>
        </div>

        {loading && (
          <div style={s.spinnerOverlay}>
            <div style={s.spinner} />
            <span style={{ marginTop: 10, color: theme.accent, letterSpacing: "0.15em", fontFamily: theme.font }}>
              {theme.name === "souls" ? "Kindling the bonfire…" : "Loading flight data…"}
            </span>
          </div>
        )}

        {error && !loading && (
          <div style={s.banner}>
            {error}
            <button style={s.retryBtn} onClick={poll}>Retry</button>
          </div>
        )}

        <SelectionDetail state={selectedState} onClose={() => setSelected(null)} />
        </div>
      </div>
      <ThemeSwitchOverlay show={soulsOverlay} onDone={() => setSoulsOverlay(false)} />
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

function FitWorldMinZoom() {
  const map = useMap();
  const prev = useRef(-1);

  useEffect(() => {
    const apply = () => {
      const size = map.getSize();
      const worldPx = Math.max(size.x, size.y);
      const minZoom = Math.max(0, Math.ceil(Math.log2(worldPx / 256)));
      if (minZoom === prev.current) return;
      prev.current = minZoom;
      map.setMinZoom(minZoom);
      if (map.getZoom() < minZoom) map.setZoom(minZoom);
    };
    apply();
    map.on("resize", apply);
    return () => {
      map.off("resize", apply);
    };
  }, [map]);

  return null;
}

function styles(theme: ReturnType<typeof useTheme>["theme"]): Record<string, React.CSSProperties> {
  return {
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
      background: theme.chipBg,
      color: theme.text,
      padding: "5px 14px",
      borderRadius: 6,
      fontSize: 12,
      fontWeight: 600,
      fontFamily: theme.font,
      letterSpacing: "0.08em",
      backdropFilter: "blur(4px)",
      border: `1px solid ${theme.borderLight}`,
    },
    ts: {
      background: theme.chipBg,
      color: theme.muted,
      padding: "5px 14px",
      borderRadius: 6,
      fontSize: 11,
      fontFamily: "monospace",
      backdropFilter: "blur(4px)",
      border: `1px solid ${theme.borderLight}`,
    },
    themeBtn: {
      background: theme.chipBg,
      color: theme.accent,
      padding: "5px 10px",
      borderRadius: 6,
      fontSize: 16,
      cursor: "pointer",
      backdropFilter: "blur(4px)",
      border: `1px solid ${theme.borderLight}`,
      lineHeight: 1,
    },
    spinnerOverlay: {
      position: "absolute",
      inset: 0,
      zIndex: 2000,
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      background: "rgba(10,10,10,0.9)",
      fontSize: 14,
      fontFamily: theme.font,
    },
    spinner: {
      width: 40,
      height: 40,
      border: `3px solid ${theme.spinner.border}`,
      borderTop: `3px solid ${theme.spinner.top}`,
      borderRadius: "50%",
      animation: "spin 0.8s linear infinite",
      boxShadow: theme.spinner.glow,
    },
    banner: {
      position: "absolute",
      top: 60,
      right: 12,
      zIndex: 1000,
      background: theme.banner.bg,
      color: theme.banner.text,
      padding: "8px 14px",
      borderRadius: 6,
      fontSize: 12,
      display: "flex",
      alignItems: "center",
      gap: 10,
      backdropFilter: "blur(4px)",
      border: `1px solid ${theme.banner.border}`,
      fontFamily: theme.font,
    },
    retryBtn: {
      background: theme.banner.btnBg,
      color: theme.banner.text,
      border: `1px solid ${theme.banner.border}`,
      borderRadius: 4,
      padding: "3px 10px",
      fontSize: 11,
      cursor: "pointer",
      fontFamily: theme.font,
    },
  };
}
