import { useMemo, useState } from "react";
import type { State } from "./api";

type SortKey = "callsign" | "baro_altitude" | "velocity" | "heading" | "origin_country";
type SortDir = "asc" | "desc";

interface Props {
  states: State[];
  selectedIcao24: string | null;
  onSelect: (icao24: string | null) => void;
}

function statusLabel(vr: number | null): { text: string; color: string } {
  if (vr == null) return { text: "—", color: "#6b7280" };
  if (vr > 5) return { text: "Climb", color: "#22c55e" };
  if (vr < -5) return { text: "Descend", color: "#ef4444" };
  return { text: "Level", color: "#3b82f6" };
}

function altColor(alt: number | null): string {
  if (alt == null) return "#6b7280";
  if (alt < 1500) return "#22c55e";
  if (alt < 4500) return "#84cc16";
  if (alt < 7500) return "#eab308";
  if (alt < 10500) return "#f97316";
  return "#ef4444";
}

export default function Sidebar({ states, selectedIcao24, onSelect }: Props) {
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

  const climbing = states.filter((s) => s.vertical_rate != null && s.vertical_rate > 5).length;
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

  return (
    <div style={styles.panel}>
      <div style={styles.header}>Radar</div>

      <div style={styles.stats}>
        <span style={styles.stat}>{states.length} aircraft</span>
        <span style={{ ...styles.stat, color: "#22c55e" }}>↑{climbing}</span>
        <span style={{ ...styles.stat, color: "#ef4444" }}>↓{descending}</span>
      </div>

      <div style={styles.searchWrap}>
        <svg style={styles.searchIcon} viewBox="0 0 24 24" width="14" height="14" fill="#9ca3af"><path d="M15.5 14h-.79l-.28-.27A6.47 6.47 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>
        <input
          style={styles.searchInput}
          placeholder="Filter callsign / country…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <div style={styles.list}>
        <div style={styles.rowHeader}>
          <span style={styles.colCall} onClick={() => toggleSort("callsign")}>Call</span>
          <span style={styles.colAlt} onClick={() => toggleSort("baro_altitude")}>Alt</span>
          <span style={styles.colSpd} onClick={() => toggleSort("velocity")}>Spd</span>
          <span style={styles.colStat}>Status</span>
        </div>
        <div style={styles.rows}>
          {filtered.map((s) => {
            const selected = s.icao24 === selectedIcao24;
            const vr = statusLabel(s.vertical_rate);
            return (
              <div
                key={s.icao24}
                style={{
                  ...styles.row,
                  background: selected ? "rgba(59,130,246,0.15)" : undefined,
                  borderLeft: selected ? "3px solid #3b82f6" : "3px solid transparent",
                }}
                onClick={() => onSelect(s.icao24 === selectedIcao24 ? null : s.icao24)}
              >
                <span style={{ ...styles.colCall, color: selected ? "#60a5fa" : "#e5e7eb" }}>
                  {s.callsign || "—"}
                </span>
                <span style={{ ...styles.colAlt, color: altColor(s.baro_altitude) }}>
                  {s.baro_altitude != null ? `${Math.round(s.baro_altitude / 100) * 100}` : "—"}
                </span>
                <span style={styles.colSpd}>
                  {s.velocity != null ? `${Math.round(s.velocity * 1.944)}` : "—"}
                </span>
                <span style={{ ...styles.colStat, color: vr.color }}>{vr.text}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  panel: {
    width: 320,
    height: "100%",
    display: "flex",
    flexDirection: "column",
    background: "#0f172a",
    color: "#e2e8f0",
    fontFamily: "system-ui, -apple-system, sans-serif",
    fontSize: 12,
    borderRight: "1px solid #1e293b",
    overflow: "hidden",
  },
  header: {
    padding: "14px 16px 8px",
    fontWeight: 700,
    fontSize: 16,
    letterSpacing: "0.05em",
    textTransform: "uppercase",
    color: "#94a3b8",
  },
  stats: {
    display: "flex",
    gap: 12,
    padding: "0 16px 10px",
    fontSize: 11,
    fontWeight: 600,
    borderBottom: "1px solid #1e293b",
  },
  stat: {
    color: "#94a3b8",
  },
  searchWrap: {
    position: "relative",
    margin: "8px 12px",
  },
  searchIcon: {
    position: "absolute",
    left: 10,
    top: "50%",
    transform: "translateY(-50%)",
    pointerEvents: "none",
  },
  searchInput: {
    width: "100%",
    padding: "7px 10px 7px 30px",
    borderRadius: 6,
    border: "1px solid #334155",
    background: "#1e293b",
    color: "#e2e8f0",
    fontSize: 12,
    outline: "none",
    boxSizing: "border-box",
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
    color: "#64748b",
    fontSize: 10,
    textTransform: "uppercase",
    letterSpacing: "0.05em",
    borderBottom: "1px solid #1e293b",
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
    borderBottom: "1px solid #1e293b",
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
    color: "#94a3b8",
  },
  colStat: {
    flex: 1,
    textAlign: "right" as const,
    fontWeight: 600,
    fontSize: 10,
    textTransform: "uppercase" as const,
    letterSpacing: "0.04em",
  },
};
