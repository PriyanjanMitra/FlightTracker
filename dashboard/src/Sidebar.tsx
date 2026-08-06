import { useMemo, useState } from "react";
import type { State } from "./api";
import Logo from "./Logo";
import { useTheme } from "./theme";

type SortKey = "callsign" | "baro_altitude" | "velocity" | "heading" | "origin_country";
type SortDir = "asc" | "desc";

interface Props {
  states: State[];
  selectedIcao24: string | null;
  onSelect: (icao24: string | null) => void;
}

export default function Sidebar({ states, selectedIcao24, onSelect }: Props) {
  const { theme, themeName } = useTheme();
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("callsign");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  const ascending = states.filter((s) => s.vertical_rate != null && s.vertical_rate > 5).length;
  const descending = states.filter((s) => s.vertical_rate != null && s.vertical_rate < -5).length;

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    let list = states;
    if (q) {
      list = states.filter(
        (s) =>
          s.callsign.toLowerCase().includes(q) ||
          s.origin_country.toLowerCase().includes(q),
      );
    }
    return [...list].sort((a, b) => {
      let va: string | number = a[sortKey] ?? "";
      let vb: string | number = b[sortKey] ?? "";
      if (typeof va === "string") {
        va = va.toLowerCase();
        vb = (vb as string).toLowerCase();
      }
      if (va < vb) return sortDir === "asc" ? -1 : 1;
      if (va > vb) return sortDir === "asc" ? 1 : -1;
      return 0;
    });
  }, [states, search, sortKey, sortDir]);

  const s = styles(theme);

  return (
    <div style={s.panel}>
      <div style={s.header}>
        <span style={{ ...s.logo, color: theme.accentText }}>
          <Logo themeName={themeName} />
        </span>
        <div>
          <div style={s.title}>FlightTracker</div>
          <div style={s.subtitle}>{theme.name === "souls" ? "The Skies Endure" : "Live Flight Tracking"}</div>
        </div>
      </div>

      <div style={s.stats}>
        <span style={s.stat}>{states.length} aircraft</span>
        <span style={{ ...s.stat, color: theme.altColor(20000) }}>▲ {ascending}</span>
        <span style={{ ...s.stat, color: theme.altColor(-1) }}>▼ {descending}</span>
      </div>

      <div style={s.searchWrap}>
        <input
          style={s.searchInput}
          placeholder="Filter by callsign / country…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <div style={s.list}>
        <div style={s.rowHeader}>
          <span style={s.colCall} onClick={() => toggleSort("callsign")}>Call</span>
          <span style={s.colAlt} onClick={() => toggleSort("baro_altitude")}>Alt</span>
          <span style={s.colSpd} onClick={() => toggleSort("velocity")}>Spd</span>
          <span style={s.colStat}>Status</span>
        </div>
        <div style={s.rows}>
          {filtered.map((row) => {
            const selected = row.icao24 === selectedIcao24;
            const vr = theme.status(row.vertical_rate);
            return (
              <div
                key={row.icao24}
                style={{
                  ...s.row,
                  background: selected ? theme.selectionBg : undefined,
                  borderLeft: selected ? `3px solid ${theme.accent}` : "3px solid transparent",
                }}
                onClick={() => onSelect(row.icao24 === selectedIcao24 ? null : row.icao24)}
              >
                <span style={{ ...s.colCall, color: selected ? theme.accentText : theme.text }}>
                  {row.callsign || "—"}
                </span>
                <span style={{ ...s.colAlt, color: theme.altColor(row.baro_altitude) }}>
                  {row.baro_altitude != null ? `${Math.round(row.baro_altitude / 100) * 100}` : "—"}
                </span>
                <span style={s.colSpd}>
                  {row.velocity != null ? `${Math.round(row.velocity * 1.944)}` : "—"}
                </span>
                <span style={{ ...s.colStat, color: vr.color }}>{vr.text}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function styles(theme: ReturnType<typeof useTheme>["theme"]): Record<string, React.CSSProperties> {
  return {
    panel: {
      width: 320,
      height: "100%",
      display: "flex",
      flexDirection: "column",
      background: theme.panelGrad,
      color: theme.text,
      fontFamily: theme.font,
      fontSize: 12,
      borderRight: `1px solid ${theme.border}`,
      overflow: "hidden",
    },
    header: {
      display: "flex",
      alignItems: "center",
      gap: 12,
      padding: "18px 16px 10px",
      borderBottom: `1px solid ${theme.border}`,
    },
    logo: {
      fontSize: 22,
      filter: "drop-shadow(0 0 8px rgba(224,129,43,0.8))",
      animation: "ember 2.4s ease-in-out infinite",
    },
    title: {
      fontWeight: 700,
      fontSize: 18,
      letterSpacing: "0.12em",
      textTransform: "uppercase" as const,
      color: theme.accentText,
      textShadow: theme.name === "souls" ? "0 0 12px rgba(212,175,55,0.4)" : "none",
    },
    subtitle: {
      fontSize: 10,
      color: theme.muted,
      letterSpacing: "0.2em",
      textTransform: "uppercase" as const,
      marginTop: 2,
    },
    stats: {
      display: "flex",
      gap: 12,
      padding: "10px 16px",
      fontSize: 11,
      fontWeight: 600,
      borderBottom: `1px solid ${theme.border}`,
    },
    stat: {
      color: theme.muted,
    },
    searchWrap: {
      margin: "10px 12px",
    },
    searchInput: {
      width: "100%",
      padding: "8px 12px",
      borderRadius: 6,
      border: `1px solid ${theme.borderLight}`,
      background: theme.inputBg,
      color: theme.text,
      fontSize: 12,
      outline: "none",
      boxSizing: "border-box",
      fontFamily: theme.font,
    },
    list: {
      flex: 1,
      display: "flex",
      flexDirection: "column",
      overflow: "hidden",
    },
    rowHeader: {
      display: "flex",
      padding: "4px 12px 4px 15px",
      fontWeight: 600,
      color: theme.muted,
      fontSize: 10,
      textTransform: "uppercase" as const,
      letterSpacing: "0.08em",
      borderBottom: `1px solid ${theme.border}`,
      cursor: "pointer",
      userSelect: "none",
    },
    rows: {
      flex: 1,
      overflowY: "auto",
    },
    row: {
      display: "flex",
      padding: "5px 12px 5px 12px",
      borderBottom: `1px solid ${theme.border}`,
      cursor: "pointer",
      transition: "background 0.15s",
      alignItems: "center",
    },
    colCall: {
      width: 80,
      flexShrink: 0,
      overflow: "hidden",
      textOverflow: "ellipsis",
      fontWeight: 600,
      fontSize: 12,
    },
    colAlt: {
      width: 55,
      flexShrink: 0,
      textAlign: "right" as const,
      fontWeight: 600,
      fontFamily: "monospace",
    },
    colSpd: {
      width: 40,
      flexShrink: 0,
      textAlign: "right" as const,
      fontFamily: "monospace",
      color: theme.muted,
    },
    colStat: {
      flex: 1,
      textAlign: "right" as const,
      fontWeight: 600,
      fontSize: 10,
      textTransform: "uppercase" as const,
      letterSpacing: "0.06em",
    },
  };
}
