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
