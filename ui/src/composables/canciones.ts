import type { FavoriteSongOut, PlaylistSongOut, SongOut } from '../api/types'

/** Aviso de lista degradada (DESIGN.md §6.9): el catálogo no respondió y se ven las copias. */
export const AVISO_DEGRADADO = 'El catálogo no responde; mostramos los últimos datos guardados.'

/** Fila de casete → canción reproducible (sin portada: el detalle de casete no la trae).
 * Una fila degradada (copia, catálogo caído) no se reproduce: el audio también es del catálogo. */
export function desdeCasete(fila: PlaylistSongOut): SongOut {
  return {
    id: fila.song_id,
    title: fila.title,
    artist: fila.artist,
    album: fila.album,
    duration_seconds: fila.duration_seconds,
    is_active: fila.status === 'ok',
    has_cover: false,
  }
}

export function desdeFavorita(fila: FavoriteSongOut): SongOut {
  return {
    id: fila.song_id,
    title: fila.title,
    artist: fila.artist,
    album: fila.album,
    duration_seconds: fila.duration_seconds,
    is_active: fila.status === 'ok',
    has_cover: fila.has_cover,
  }
}

/** "12 canciones · 48 min" */
export function resumenDuracion(canciones: number, segundos: number): string {
  const n = `${canciones} ${canciones === 1 ? 'canción' : 'canciones'}`
  if (segundos <= 0) return n
  const minutos = Math.round(segundos / 60)
  if (minutos < 60) return `${n} · ${Math.max(minutos, 1)} min`
  return `${n} · ${Math.floor(minutos / 60)} h ${minutos % 60} min`
}
