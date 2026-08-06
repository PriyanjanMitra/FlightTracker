import type { ThemeName } from "./theme";

interface LogoProps {
  themeName: ThemeName;
  size?: number;
}

export default function Logo({ themeName, size = 26 }: LogoProps) {
  if (themeName === "souls") {
    return <BonfireLogo size={size} />;
  }
  return <PlaneLogo size={size} />;
}

function PlaneLogo({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M2 16l9-1V7.5L8 5v-1l4-.7L16 4v1l-3 2.5V15l9 1v1.6L12 18.8 3 18.6 2 16z"
        transform="translate(0 1) rotate(0 12 12)"
        fill="currentColor"
      />
    </svg>
  );
}

function BonfireLogo({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      {/* log pile */}
      <rect x="3.5" y="14.5" width="17" height="2.4" rx="1.2" opacity="0.85" />
      <rect x="7" y="16.6" width="12" height="2.2" rx="1.1" opacity="0.6" />
      {/* flame with cutout */}
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M12 2.5c2.6 3 4.2 5.4 4.2 8.1a4.2 4.2 0 1 1-8.4 0C7.8 7.9 9.4 5.5 12 2.5Zm0 4.7c1.3 1.6 2.1 2.9 2.1 4.3a2.1 2.1 0 1 1-4.2 0c0-1.4.8-2.7 2.1-4.3Z"
        opacity="0.95"
      />
    </svg>
  );
}