import { useSyncExternalStore } from "react";

export type ThemePref = "system" | "dark" | "light";
export type Theme = "dark" | "light";

const KEY = "meloxo.theme";
const PREFS: readonly ThemePref[] = ["system", "dark", "light"];
const QUERY = "(prefers-color-scheme: light)";
/** Lo que el navegador pinta alrededor de la página (barra del móvil, controles nativos). */
const BROWSER_COLOR: Record<Theme, string> = { dark: "#141317", light: "#ebe5d8" };

type State = { pref: ThemePref; resolved: Theme };

export const resolveTheme = (pref: ThemePref, prefersLight: boolean): Theme =>
  pref === "system" ? (prefersLight ? "light" : "dark") : pref;

/** Lo guardado puede estar corrupto: lo que no sirve se trata como ausente, y lo de siempre es oscuro. */
function readPref(): ThemePref {
  try {
    const stored = localStorage.getItem(KEY);
    return PREFS.includes(stored as ThemePref) ? (stored as ThemePref) : "dark";
  } catch {
    return "dark";
  }
}

const systemMedia = () => (typeof window.matchMedia === "function" ? window.matchMedia(QUERY) : undefined);

const compute = (pref: ThemePref): State => ({ pref, resolved: resolveTheme(pref, !!systemMedia()?.matches) });

function setMeta(name: string, content: string) {
  document.querySelector(`meta[name="${name}"]`)?.setAttribute("content", content);
}

function apply({ resolved }: State) {
  document.documentElement.setAttribute("data-theme", resolved);
  setMeta("theme-color", BROWSER_COLOR[resolved]);
  setMeta("color-scheme", resolved);
}

let state: State = compute("dark");
let watched: MediaQueryList | undefined;
const listeners = new Set<() => void>();

function commit(next: State) {
  state = next;
  apply(next);
  listeners.forEach((listener) => listener());
}

function followSystem() {
  if (state.pref === "system") commit(compute("system"));
}

function watchSystem() {
  watched?.removeEventListener("change", followSystem);
  watched = systemMedia();
  watched?.addEventListener("change", followSystem);
}

/** Vuelve a leer lo guardado y a mirar el equipo. Se llama al cargar la app, y en las pruebas. */
export function resetTheme() {
  watchSystem();
  commit(compute(readPref()));
}

function setPref(pref: ThemePref) {
  try {
    localStorage.setItem(KEY, pref);
  } catch {
    // Sin almacenamiento, la elección vale solo en esta sesión.
  }
  commit(compute(pref));
}

const subscribe = (listener: () => void) => {
  listeners.add(listener);
  return () => listeners.delete(listener);
};

export function useTheme() {
  const current = useSyncExternalStore(subscribe, () => state);
  return { pref: current.pref, resolved: current.resolved, setPref };
}

resetTheme();
