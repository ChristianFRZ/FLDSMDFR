import { useSyncExternalStore } from "react";
import type { LibrarySort } from "./libraryOrder";

const KEY = "meloxo.library";

type Prefs = { sort: LibrarySort; pinned: string[] };

const SORTS: readonly LibrarySort[] = ["default", "name"];

/** Lo guardado puede estar corrupto o venir de otra versión: lo que no sirve se trata como ausente. */
function read(): Prefs {
  try {
    const stored: unknown = JSON.parse(localStorage.getItem(KEY) ?? "null");
    if (typeof stored !== "object" || stored === null) return { sort: "default", pinned: [] };
    const { sort, pinned } = stored as { sort?: unknown; pinned?: unknown };
    return {
      sort: SORTS.includes(sort as LibrarySort) ? (sort as LibrarySort) : "default",
      pinned: Array.isArray(pinned) ? pinned.filter((id): id is string => typeof id === "string") : [],
    };
  } catch {
    return { sort: "default", pinned: [] };
  }
}

let prefs = read();
const listeners = new Set<() => void>();

function write(next: Prefs) {
  prefs = next;
  try {
    localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    // Sin almacenamiento, el cambio vale solo en esta sesión.
  }
  listeners.forEach((listener) => listener());
}

const subscribe = (listener: () => void) => {
  listeners.add(listener);
  return () => listeners.delete(listener);
};

const setSort = (sort: LibrarySort) => write({ ...prefs, sort });

const togglePin = (id: string) =>
  write({ ...prefs, pinned: prefs.pinned.includes(id) ? prefs.pinned.filter((pinned) => pinned !== id) : [...prefs.pinned, id] });

/** Una sola copia para toda la pantalla: la barra lateral y la biblioteca ven siempre lo mismo. */
export function useLibraryPrefs() {
  const current = useSyncExternalStore(subscribe, () => prefs);
  return { sort: current.sort, pinned: current.pinned, setSort, togglePin };
}

/** Para las pruebas: vuelve a leer lo guardado, o lo borra. */
export function resetLibraryPrefs(options: { keepStorage?: boolean } = {}) {
  if (!options.keepStorage) {
    try {
      localStorage.removeItem(KEY);
    } catch {
      // Nada que borrar.
    }
  }
  prefs = read();
  listeners.forEach((listener) => listener());
}
