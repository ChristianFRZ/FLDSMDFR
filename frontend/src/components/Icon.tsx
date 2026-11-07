import type { ReactNode } from "react";

const paths: Record<string, ReactNode> = {
  home: <><path d="M3 11 12 4l9 7" /><path d="M5 10v10h14V10" /></>,
  search: <><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></>,
  library: <><rect x="3" y="6" width="18" height="13" rx="2" /><circle cx="9" cy="12" r="1.6" /><circle cx="15" cy="12" r="1.6" /></>,
  stats: <path d="M5 20V11M12 20V5M19 20v-6" />,
  plus: <path d="M12 5v14M5 12h14" />,
  bell: <><path d="M6 16V11a6 6 0 1 1 12 0v5l2 2H4z" /><path d="M10 21h4" /></>,
  left: <path d="m15 5-7 7 7 7" />,
  right: <path d="m9 5 7 7-7 7" />,
  shuffle: <><path d="M3 7h3c5 0 7 10 12 10h3" /><path d="M3 17h3c1.8 0 3-1 4.2-2.4M14 9.4C15 8 16.2 7 18 7h3" /><path d="m18 4 3 3-3 3M18 14l3 3-3 3" /></>,
  prev: <><path d="M19 5 9 12l10 7z" /><path d="M5 5v14" /></>,
  next: <><path d="m5 5 10 7-10 7z" /><path d="M19 5v14" /></>,
  play: <path d="m7 4 13 8-13 8z" />,
  pause: <path d="M8 5v14M16 5v14" />,
  repeat: <><path d="M4 11V9a3 3 0 0 1 3-3h13" /><path d="m17 3 3 3-3 3" /><path d="M20 13v2a3 3 0 0 1-3 3H4" /><path d="m7 21-3-3 3-3" /></>,
  heart: <path d="M12 20S4 15 4 9.5A4.5 4.5 0 0 1 12 7a4.5 4.5 0 0 1 8 2.5C20 15 12 20 12 20z" />,
  queue: <><path d="M4 6h12M4 12h12M4 18h7" /><path d="m15 15 5 3-5 3z" /></>,
  note: <><path d="M4 5h16v11l-3 3H4z" /><path d="M8 10h8M8 14h5" /></>,
  volume: <><path d="M4 9v6h4l5 4V5L8 9z" /><path d="M16.5 9a4 4 0 0 1 0 6" /></>,
  mute: <><path d="M4 9v6h4l5 4V5L8 9z" /><path d="m16 10 4 4M20 10l-4 4" /></>,
  expand: <path d="M4 9V4h5M20 15v5h-5M4 4l6 6M20 20l-6-6" />,
  close: <path d="M6 6l12 12M18 6 6 18" />,
  trash: <><path d="M4 7h16M9 7V4h6v3" /><path d="M6 7l1 13h10l1-13" /></>,
  link: <><path d="M10 14a4 4 0 0 0 6 0l3-3a4 4 0 0 0-6-6l-1 1" /><path d="M14 10a4 4 0 0 0-6 0l-3 3a4 4 0 0 0 6 6l1-1" /></>,
  drag: <path d="M9 6h.01M15 6h.01M9 12h.01M15 12h.01M9 18h.01M15 18h.01" />,
  up: <path d="m5 15 7-7 7 7" />,
  down: <path d="m5 9 7 7 7-7" />,
  upload: <><path d="M12 16V5" /><path d="m7 10 5-5 5 5" /><path d="M4 19h16" /></>,
  user: <><circle cx="12" cy="8" r="4" /><path d="M4 21c1-5 4-7 8-7s7 2 8 7" /></>,
  logout: <><path d="M14 4H5v16h9" /><path d="M10 12h10" /><path d="m16 8 4 4-4 4" /></>,
  check: <path d="m5 13 4 4L19 7" />,
  shield: <path d="M12 3 5 6v6c0 5 3 8 7 9 4-1 7-4 7-9V6z" />,
  mic: <><rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5 11a7 7 0 0 0 14 0" /><path d="M12 18v3" /></>,
};

export type IconName = keyof typeof paths;

/** Decorativo por defecto: quien lo usa pone el nombre accesible en el botón. */
export function Icon({ name, filled }: { name: IconName; filled?: boolean }) {
  return (
    <svg className={filled ? "icon icon-filled" : "icon"} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      {paths[name]}
    </svg>
  );
}
