import { useCallback, useEffect, useRef } from "react";
import { useTheme } from "../theme";
import { DURATIONS, useDone } from "./motion";

/** Paths del logo, copiados de `assets/meloxo-stacked-color-*.svg` (`#symbol` y `#wordmark`). */
const SYMBOL =
  "M34 44H236L220 71.7L242 93.7L214 121.7L240 147.7L216 189.3L238.7 212H34A18 18 0 0 1 16 194V62A18 18 0 0 1 34 44ZM50 126a32 32 0 1 0 64 0a32 32 0 1 0 -64 0ZM130 126a32 32 0 1 0 64 0a32 32 0 1 0 -64 0Z";
const WORDMARK =
  "M0.0 120.0L0.0 0.0L31.4 0.0L66.0 60.0L100.6 0.0L132.0 0.0L132.0 120.0L100.0 120.0L100.0 60.0L72.3 108.0L59.7 108.0L32.0 60.0L32.0 120.0Z M146.0 0.0L238.0 0.0L238.0 28.0L178.0 28.0L178.0 46.0L228.0 46.0L228.0 74.0L178.0 74.0L178.0 92.0L238.0 92.0L238.0 120.0L146.0 120.0Z M252.0 0.0L284.0 0.0L284.0 92.0L336.0 92.0L336.0 120.0L252.0 120.0Z M346 60a62 62 0 1 0 124 0a62 62 0 1 0 -124 0ZM380 60a28 28 0 1 0 56 0a28 28 0 1 0 -56 0Z M477.7 23.5L498.2 18.0L528.5 35.5L546.0 5.2L566.5 -0.3L572.0 20.2L554.5 50.5L584.8 68.0L590.3 88.5L569.8 94.0L539.5 76.5L522.0 106.8L501.5 112.3L496.0 91.8L513.5 61.5L483.2 44.0Z M598 60a62 62 0 1 0 124 0a62 62 0 1 0 -124 0ZM632 60a28 28 0 1 0 56 0a28 28 0 1 0 -56 0Z";

const PINK = "#FF3D8B";
/** El wordmark del logo para fondo claro es tinta; el del logo para fondo oscuro, papel. */
const WORDMARK_FILL = { light: "#141317", dark: "#F4F1EA" } as const;

const LABELS = { intro: "Cargando MELOXO", enter: "Entrando" } as const;

/** Los carretes van en los huecos del símbolo (centros 82,126 y 162,126; radio 32). */
function Reel({ cx }: { cx: number }) {
  return (
    <g className="logo-anim-reel">
      <circle cx={cx} cy={126} r={22} fill="none" stroke={PINK} strokeWidth={6} />
      <path d={`M${cx} 104V148M${cx - 22} 126H${cx + 22}`} stroke={PINK} strokeWidth={6} />
      <circle cx={cx} cy={126} r={6} fill={PINK} />
    </g>
  );
}

function Symbol() {
  return (
    <g className="logo-anim-symbol">
      <path fill={PINK} fillRule="evenodd" d={SYMBOL} />
      <Reel cx={82} />
      <Reel cx={162} />
    </g>
  );
}

/**
 * Animación del logo a pantalla completa. `intro`: el casete aparece, los carretes giran y se dibuja el
 * wordmark. `enter`: el casete cruza hacia abajo a la derecha, hacia el reproductor.
 * Un clic o cualquier tecla la salta; `onDone` se llama una sola vez.
 */
export function LogoAnimation({ variant, onDone }: { variant: "intro" | "enter"; onDone: () => void }) {
  const { resolved } = useTheme();
  const done = useRef(false);
  const latest = useRef(onDone);
  latest.current = onDone;

  const finish = useCallback(() => {
    if (done.current) return;
    done.current = true;
    latest.current();
  }, []);

  useDone(DURATIONS[variant], finish);

  useEffect(() => {
    window.addEventListener("keydown", finish);
    return () => window.removeEventListener("keydown", finish);
  }, [finish]);

  return (
    <div role="status" aria-label={LABELS[variant]} className={`logo-anim logo-anim-${variant}`} onClick={finish}>
      {variant === "intro" ? (
        <svg className="logo-anim-art" viewBox="0 0 686 392" aria-hidden="true">
          <g transform="translate(175.3 -45.2) scale(1.3)">
            <Symbol />
          </g>
          <path
            className="logo-anim-wordmark"
            transform="translate(12 262) scale(0.92)"
            fill={WORDMARK_FILL[resolved]}
            stroke={WORDMARK_FILL[resolved]}
            fillRule="evenodd"
            pathLength={1}
            d={WORDMARK}
          />
        </svg>
      ) : (
        <svg className="logo-anim-art" viewBox="16 44 226 168" aria-hidden="true">
          <Symbol />
        </svg>
      )}
    </div>
  );
}
