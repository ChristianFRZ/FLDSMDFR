import { useEffect, useRef } from "react";

/** Cuánto dura cada animación del logo, en milisegundos. Repetidas en `app.css`. */
export const DURATIONS = { intro: 1200, enter: 900, drop: 900 } as const;

/** Si la persona pidió menos movimiento. Sin `matchMedia` (tests, navegadores viejos) se asume que no. */
export function prefersReducedMotion(): boolean {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/**
 * Llama `onDone` una sola vez cuando pasan `ms`, o en el siguiente tick si se pidió menos movimiento.
 * Desmontar antes cancela la llamada.
 */
export function useDone(ms: number, onDone: () => void): void {
  const latest = useRef(onDone);
  latest.current = onDone;
  const called = useRef(false);

  useEffect(() => {
    const timer = window.setTimeout(
      () => {
        if (called.current) return;
        called.current = true;
        latest.current();
      },
      prefersReducedMotion() ? 0 : ms,
    );
    return () => window.clearTimeout(timer);
  }, [ms]);
}
