/** Bitrate medio estimado en kbps (tamaño × 8 / duración); null si falta algún dato. */
export function bitrateKbps(sizeBytes: number, seconds: number): number | null {
  if (!(sizeBytes > 0) || !(seconds > 0)) return null
  return Math.round((sizeBytes * 8) / seconds / 1000)
}

/** Porcentaje de la canción ya descargado (suma de los rangos de audio.buffered). */
export function porcentajeDescargado(buffered: ReadonlyArray<[number, number]>, duration: number): number {
  if (!(duration > 0)) return 0
  const segundos = buffered.reduce((total, [inicio, fin]) => total + Math.max(fin - inicio, 0), 0)
  return Math.min(Math.round((segundos / duration) * 100), 100)
}

/** "3.8 MB" */
export function tamanoLegible(bytes: number): string {
  if (!(bytes > 0)) return '—'
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const FORMATOS: Record<string, string> = {
  'audio/mpeg': 'MP3',
  'audio/mp3': 'MP3',
  'audio/ogg': 'Ogg',
  'audio/flac': 'FLAC',
  'audio/x-flac': 'FLAC',
  'audio/wav': 'WAV',
  'audio/x-wav': 'WAV',
  'audio/mp4': 'AAC (MP4)',
  'audio/aac': 'AAC',
}

export function formatoLegible(mime: string | undefined): string {
  if (!mime) return '—'
  return FORMATOS[mime] ?? mime
}
