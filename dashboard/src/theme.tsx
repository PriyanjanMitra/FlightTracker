import { createContext, useCallback, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";

export type ThemeName = "radar" | "souls";

export interface StatusBadge {
  text: string;
  color: string;
}

export interface Theme {
  name: ThemeName;
  label: string;
  icon: string;
  font: string;
  bg: string;
  panel: string;
  panelGrad: string;
  border: string;
  borderLight: string;
  text: string;
  textBright: string;
  muted: string;
  accent: string;
  accentText: string;
  selectionBg: string;
  inputBg: string;
  altColor: (alt: number | null) => string;
  status: (vr: number | null) => StatusBadge;
  markerFill: string;
  selectedMarker: { fill: string; glow: string };
  trailColor: string;
  clusterBg: string;
  clusterText: string;
  chipBg: string;
  spinner: { border: string; top: string; glow: string };
  banner: { bg: string; border: string; text: string; btnBg: string };
}

export const themes: Record<ThemeName, Theme> = {
  radar: {
    name: "radar",
    label: "Radar",
    icon: "🛰",
    font: "system-ui, -apple-system, sans-serif",
    bg: "#0f172a",
    panel: "#0f172a",
    panelGrad: "linear-gradient(180deg, #0f172a 0%, #0b1120 100%)",
    border: "#1e293b",
    borderLight: "#334155",
    text: "#e2e8f0",
    textBright: "#f8fafc",
    muted: "#94a3b8",
    accent: "#3b82f6",
    accentText: "#60a5fa",
    selectionBg: "rgba(59,130,246,0.15)",
    inputBg: "#1e293b",
    altColor: (alt) => {
      if (alt == null) return "#6b7280";
      if (alt < 1500) return "#22c55e";
      if (alt < 4500) return "#84cc16";
      if (alt < 7500) return "#eab308";
      if (alt < 10500) return "#f97316";
      return "#ef4444";
    },
    status: (vr) => {
      if (vr == null) return { text: "—", color: "#6b7280" };
      if (vr > 5) return { text: "Climb", color: "#22c55e" };
      if (vr < -5) return { text: "Descend", color: "#ef4444" };
      return { text: "Level", color: "#3b82f6" };
    },
    markerFill: "#2563eb",
    selectedMarker: { fill: "#ef4444", glow: "rgba(239,68,68,0.9)" },
    trailColor: "#2563eb",
    clusterBg: "#2563eb",
    clusterText: "#f8fafc",
    chipBg: "rgba(15,23,42,0.85)",
    spinner: { border: "#1e293b", top: "#3b82f6", glow: "none" },
    banner: {
      bg: "rgba(127,29,29,0.9)",
      border: "#7f1d1d",
      text: "#fca5a5",
      btnBg: "#dc2626",
    },
  },

  souls: {
    name: "souls",
    label: "Bonfire",
    icon: "🔥",
    font: "'Cinzel', system-ui, serif",
    bg: "#0a0a0a",
    panel: "#141414",
    panelGrad: "linear-gradient(180deg, #141414 0%, #0c0c0c 100%)",
    border: "#2c2c2c",
    borderLight: "#3a3a3a",
    text: "#b8b0a8",
    textBright: "#e8c97a",
    muted: "#6f6a63",
    accent: "#d4af37",
    accentText: "#e8c97a",
    selectionBg: "rgba(212,175,55,0.10)",
    inputBg: "#0a0a0a",
    altColor: (alt) => {
      if (alt == null) return "#6f6a63";
      if (alt < 1500) return "#d4af37";
      if (alt < 4500) return "#e0812b";
      if (alt < 7500) return "#b5651d";
      if (alt < 10500) return "#9a1f1f";
      return "#5c1212";
    },
    status: (vr) => {
      if (vr == null) return { text: "Hollow", color: "#6f6a63" };
      if (vr > 5) return { text: "Ascend", color: "#d4af37" };
      if (vr < -5) return { text: "Descend", color: "#8b1e1e" };
      return { text: "Wander", color: "#e0812b" };
    },
    markerFill: "#d4af37",
    selectedMarker: { fill: "#d4af37", glow: "rgba(212,175,55,0.9)" },
    trailColor: "#d4af37",
    clusterBg: "#d4af37",
    clusterText: "#0a0a0a",
    chipBg: "rgba(12,12,12,0.9)",
    spinner: { border: "#2c2c2c", top: "#d4af37", glow: "0 0 16px rgba(212,175,55,0.3)" },
    banner: {
      bg: "rgba(44,12,12,0.95)",
      border: "#5c1212",
      text: "#e0b0a0",
      btnBg: "#5c1212",
    },
  },
};

interface ThemeContextValue {
  theme: Theme;
  themeName: ThemeName;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextValue>({
  theme: themes.radar,
  themeName: "radar",
  toggleTheme: () => {},
});

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [themeName, setThemeName] = useState<ThemeName>(
    () => (localStorage.getItem("theme") as ThemeName) || "radar",
  );

  const toggleTheme = useCallback(() => {
    setThemeName((prev) => {
      const next = prev === "radar" ? "souls" : "radar";
      localStorage.setItem("theme", next);
      return next;
    });
  }, []);

  const value = useMemo(
    () => ({ theme: themes[themeName], themeName, toggleTheme }),
    [themeName, toggleTheme],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  return useContext(ThemeContext);
}
