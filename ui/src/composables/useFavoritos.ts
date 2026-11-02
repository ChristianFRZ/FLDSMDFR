import { ref } from 'vue'
import * as me from '../api/me'
import { useAvisos } from './useAvisos'

// Estado singleton: el corazón del reproductor, las filas y "Tus favoritas" comparten los ids.
const ids = ref<Set<string>>(new Set())
// Sube con cada cambio confirmado para que "Tus favoritas" sepa que debe recargar.
const version = ref(0)

const { mostrar } = useAvisos()

async function cargar(): Promise<void> {
  try {
    ids.value = new Set(await me.favoriteIds())
  } catch {
    // Sin ids los corazones salen vacíos; se recargan en el siguiente intento.
  }
}

function esFavorita(id: string): boolean {
  return ids.value.has(id)
}

function fijar(id: string, valor: boolean): void {
  const copia = new Set(ids.value)
  if (valor) copia.add(id)
  else copia.delete(id)
  ids.value = copia
}

/** Optimista: el corazón cambia al instante y se revierte si la API falla. */
async function alternar(songId: string): Promise<void> {
  const nuevo = !esFavorita(songId)
  fijar(songId, nuevo)
  try {
    if (nuevo) await me.like(songId)
    else await me.unlike(songId)
    version.value++
  } catch {
    fijar(songId, !nuevo)
    mostrar('No pudimos actualizar tus favoritas. Vuelve a intentarlo.', 'error')
  }
}

function reiniciar(): void {
  ids.value = new Set()
}

export function useFavoritos() {
  return { ids, version, cargar, esFavorita, alternar, reiniciar }
}
