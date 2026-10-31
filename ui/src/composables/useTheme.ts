import { readonly, ref, type Ref } from 'vue'

/** Lado del casete = tema visual. A: Mostaza y oliva (claro). B: Ámbar nocturno (oscuro). */
export type Side = 'A' | 'B'

const STORAGE_KEY = 'fldsmdfr-lado'

function isSide(value: unknown): value is Side {
  return value === 'A' || value === 'B'
}

function readStoredSide(): Side | null {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    return isSide(stored) ? stored : null
  } catch {
    // localStorage bloqueado (navegación privada, políticas del navegador): se ignora.
    return null
  }
}

function storeSide(value: Side): void {
  try {
    localStorage.setItem(STORAGE_KEY, value)
  } catch {
    // Sin almacenamiento la elección dura solo esta sesión.
  }
}

function systemSide(): Side {
  const prefersDark =
    typeof matchMedia === 'function' && matchMedia('(prefers-color-scheme: dark)').matches
  return prefersDark ? 'B' : 'A'
}

function apply(value: Side): void {
  document.documentElement.dataset.lado = value
}

// Estado singleton a nivel de módulo: todos los componentes comparten el mismo lado.
const side = ref<Side>(readStoredSide() ?? systemSide())
apply(side.value)

function set(value: Side): void {
  side.value = value
  apply(value)
  storeSide(value)
}

function toggle(): void {
  set(side.value === 'A' ? 'B' : 'A')
}

export function useTheme(): {
  side: Readonly<Ref<Side>>
  toggle: () => void
  set: (value: Side) => void
} {
  return { side: readonly(side), toggle, set }
}
