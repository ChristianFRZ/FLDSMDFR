import { ref } from 'vue'
import * as me from '../api/me'
import type { FollowOut } from '../api/types'
import { useAvisos } from './useAvisos'

// Estado singleton: el catálogo y la pestaña "Artistas" comparten los artistas seguidos.
const artistas = ref<FollowOut[]>([])
const { mostrar } = useAvisos()

const clave = (artista: string) => artista.trim().toLowerCase()

async function cargar(): Promise<void> {
  try {
    artistas.value = await me.follows()
  } catch {
    // La pestaña queda vacía; se reintenta en la próxima carga.
  }
}

function sigue(artista: string): boolean {
  const k = clave(artista)
  return artistas.value.some((a) => clave(a.artist) === k)
}

/** Seguir o dejar de seguir; tras el cambio se recarga para traer conteo y portada reales. */
async function alternar(artista: string): Promise<void> {
  const seguia = sigue(artista)
  try {
    if (seguia) await me.unfollow(artista)
    else await me.follow(artista)
  } catch {
    mostrar(`No pudimos ${seguia ? 'dejar de seguir' : 'seguir'} a ${artista}. Vuelve a intentarlo.`, 'error')
    return
  }
  await cargar()
}

function reiniciar(): void {
  artistas.value = []
}

export function useSeguidos() {
  return { artistas, cargar, sigue, alternar, reiniciar }
}
