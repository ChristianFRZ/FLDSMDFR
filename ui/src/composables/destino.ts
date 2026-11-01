/**
 * Destino tras entrar: solo rutas internas de la app (empiezan por "/" y no por "//" ni "/\").
 * Evita redirecciones abiertas con `?siguiente=//otro-sitio`.
 */
export function destinoSeguro(siguiente: unknown): string {
  if (typeof siguiente !== 'string') return '/'
  if (!siguiente.startsWith('/') || siguiente.startsWith('//') || siguiente.startsWith('/\\')) {
    return '/'
  }
  if (siguiente === '/acceso' || siguiente.startsWith('/acceso?')) return '/'
  return siguiente
}
