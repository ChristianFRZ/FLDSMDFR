/** Iniciales para avatares: "Alex López" → "AL", "Marta" → "MA". */
export function iniciales(nombre: string): string {
  const partes = nombre.trim().split(/\s+/).filter(Boolean)
  if (partes.length === 0) return '?'
  if (partes.length === 1) return partes[0].slice(0, 2).toUpperCase()
  return (partes[0][0] + partes[partes.length - 1][0]).toUpperCase()
}

/** Primera palabra del nombre, para el saludo. */
export function primerNombre(nombre: string): string {
  return nombre.trim().split(/\s+/)[0] ?? ''
}

const UNIDADES: Array<[Intl.RelativeTimeFormatUnit, number]> = [
  ['year', 365 * 86_400],
  ['month', 30 * 86_400],
  ['week', 7 * 86_400],
  ['day', 86_400],
  ['hour', 3_600],
  ['minute', 60],
]
const relativo = new Intl.RelativeTimeFormat('es', { numeric: 'auto' })

/** "hace 2 horas", "ayer", "ahora": tiempo relativo en español. */
export function tiempoRelativo(iso: string, ahora: number = Date.now()): string {
  const segundos = Math.round((new Date(iso).getTime() - ahora) / 1000)
  for (const [unidad, tamano] of UNIDADES) {
    if (Math.abs(segundos) >= tamano) return relativo.format(Math.trunc(segundos / tamano), unidad)
  }
  return 'ahora'
}
