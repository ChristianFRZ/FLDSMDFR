import { useSyncExternalStore } from "react";

/** El mismo corte de los estilos. En JS porque el reproductor cambia de forma, no solo de tamaño. */
const QUERY = "(max-width: 900px)";

function subscribe(listener: () => void) {
  const media = window.matchMedia?.(QUERY);
  media?.addEventListener("change", listener);
  return () => media?.removeEventListener("change", listener);
}

export function useCompact(): boolean {
  return useSyncExternalStore(subscribe, () => window.matchMedia?.(QUERY).matches ?? false);
}
