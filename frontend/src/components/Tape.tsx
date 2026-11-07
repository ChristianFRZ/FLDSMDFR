import type { CSSProperties } from "react";
import { tapeHex } from "./tapeColors";

export type TapeColor = string;

type Props = { title: string; color?: TapeColor; tilt?: number; className?: string };

export function Tape({ title, color = "pink", tilt, className = "" }: Props) {
  const style = {
    "--shell": tapeHex(color),
    ...(tilt === undefined ? {} : { transform: `rotate(${tilt}deg)` }),
  } as CSSProperties;
  return (
    <div className={`tape ${className}`.trim()} style={style}>
      <svg viewBox="0 0 320 204" aria-hidden="true">
        <rect x="2" y="2" width="316" height="200" rx="12" fill="var(--shell)" stroke="#000" strokeOpacity=".35" strokeWidth="2" />
        <rect x="22" y="18" width="276" height="122" rx="6" fill="#FFFDF7" />
        <rect x="72" y="76" width="176" height="52" rx="26" fill="#15131F" />
        <circle cx="100" cy="102" r="18" fill="#FFFDF7" />
        <circle cx="100" cy="102" r="7" fill="#15131F" />
        <circle cx="220" cy="102" r="18" fill="#FFFDF7" />
        <circle cx="220" cy="102" r="7" fill="#15131F" />
        <path d="M70 202 L84 160 H236 L250 202 Z" fill="#000" opacity=".22" />
      </svg>
      <span>{title}</span>
    </div>
  );
}
