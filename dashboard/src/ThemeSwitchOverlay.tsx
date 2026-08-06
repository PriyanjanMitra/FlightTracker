import { useEffect, useState } from "react";

interface Props {
  show: boolean;
  onDone: () => void;
}

const DURATION_MS = 8100;

export default function ThemeSwitchOverlay({ show, onDone }: Props) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!show) {
      setVisible(false);
      return;
    }
    requestAnimationFrame(() => setVisible(true));
    const timer = setTimeout(onDone, DURATION_MS);
    return () => clearTimeout(timer);
  }, [show, onDone]);

  if (!show) return null;

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        width: "100vw",
        height: "100vh",
        backgroundColor: "rgba(20, 20, 20, 0.75)",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        zIndex: 999999,
        opacity: visible ? 1 : 0,
        pointerEvents: "none",
        transition: "opacity 1.5s ease-in-out",
        overflow: "hidden",
      }}
    >
      {/* rising embers */}
      {[...Array(20)].map((_, i) => (
        <span
          key={i}
          className="souls-ember"
          style={{
            left: `${(i * 53 + 7) % 100}%`,
            bottom: "4%",
            width: i % 3 === 0 ? 5 : 3,
            height: i % 3 === 0 ? 5 : 3,
            background: i % 3 === 0 ? "#e8c97a" : "#8b5a2b",
            boxShadow: "0 0 8px rgba(212,175,55,0.9)",
            animationDelay: `${(i % 8) * 0.55}s`,
            animationDuration: `${3.5 + (i % 4)}s`,
          }}
        />
      ))}

      <div
        style={{
          position: "relative",
          fontFamily: "'Cinzel', system-ui, serif",
          fontSize: "clamp(2.5rem, 8vw, 6rem)",
          fontWeight: 700,
          letterSpacing: "0.22em",
          color: "#e8c97a",
          textShadow:
            "0 0 18px rgba(212,175,55,0.8), 0 0 60px rgba(212,175,55,0.4), 0 6px 0 rgba(0,0,0,0.7)",
          opacity: visible ? 1 : 0,
          transform: visible ? "scale(1)" : "scale(0.8)",
          transition: "all 1.5s ease-in-out",
          textAlign: "center",
          userSelect: "none",
        }}
      >
        THEME&nbsp;SWITCHED
      </div>
    </div>
  );
}