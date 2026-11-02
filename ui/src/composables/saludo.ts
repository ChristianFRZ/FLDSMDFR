import { primerNombre } from './texto'

/** "Buenos días, Alex." según la hora local: 5:00–11:59 días, 12:00–19:59 tardes, resto noches. */
export function saludo(fecha: Date, nombre: string): string {
  const hora = fecha.getHours()
  const base = hora >= 5 && hora < 12 ? 'Buenos días' : hora >= 12 && hora < 20 ? 'Buenas tardes' : 'Buenas noches'
  const quien = primerNombre(nombre)
  return quien ? `${base}, ${quien}.` : `${base}.`
}
