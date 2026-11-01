import { describe, expect, it } from 'vitest'
import { saludo } from '../saludo'

const a = (h: number, m: number) => new Date(2026, 9, 31, h, m)

describe('saludo', () => {
  it.each([
    [a(4, 59), 'Buenas noches, Alex.'],
    [a(5, 0), 'Buenos días, Alex.'],
    [a(11, 59), 'Buenos días, Alex.'],
    [a(12, 0), 'Buenas tardes, Alex.'],
    [a(19, 59), 'Buenas tardes, Alex.'],
    [a(20, 0), 'Buenas noches, Alex.'],
  ])('%s → %s', (fecha, esperado) => {
    expect(saludo(fecha, 'Alex López')).toBe(esperado)
  })

  it('sin nombre no deja coma suelta', () => {
    expect(saludo(a(9, 0), '  ')).toBe('Buenos días.')
  })
})
