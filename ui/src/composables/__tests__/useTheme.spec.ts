import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const STORAGE_KEY = 'fldsmdfr-lado'

function mockColorScheme(dark: boolean) {
  vi.stubGlobal(
    'matchMedia',
    vi.fn((query: string) => ({
      matches: dark && query === '(prefers-color-scheme: dark)',
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })),
  )
}

// El estado es un singleton de módulo: cada prueba importa una copia nueva.
async function freshUseTheme() {
  vi.resetModules()
  const mod = await import('../useTheme')
  return mod.useTheme
}

describe('useTheme', () => {
  beforeEach(() => {
    localStorage.clear()
    delete document.documentElement.dataset.lado
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('sin preferencia guardada y sistema oscuro empieza en Lado B', async () => {
    mockColorScheme(true)
    const useTheme = await freshUseTheme()
    const { side } = useTheme()
    expect(side.value).toBe('B')
    expect(document.documentElement.dataset.lado).toBe('B')
  })

  it('sin preferencia guardada y sistema claro empieza en Lado A', async () => {
    mockColorScheme(false)
    const useTheme = await freshUseTheme()
    expect(useTheme().side.value).toBe('A')
    expect(document.documentElement.dataset.lado).toBe('A')
  })

  it('la elección guardada gana a la preferencia del sistema', async () => {
    localStorage.setItem(STORAGE_KEY, 'A')
    mockColorScheme(true)
    const useTheme = await freshUseTheme()
    expect(useTheme().side.value).toBe('A')
    expect(document.documentElement.dataset.lado).toBe('A')
  })

  it('ignora un valor guardado que no es A ni B', async () => {
    localStorage.setItem(STORAGE_KEY, 'C')
    mockColorScheme(true)
    const useTheme = await freshUseTheme()
    expect(useTheme().side.value).toBe('B')
  })

  it('toggle cambia de lado, actualiza el documento y lo recuerda', async () => {
    mockColorScheme(false)
    const useTheme = await freshUseTheme()
    const { side, toggle } = useTheme()
    toggle()
    expect(side.value).toBe('B')
    expect(document.documentElement.dataset.lado).toBe('B')
    expect(localStorage.getItem(STORAGE_KEY)).toBe('B')
    toggle()
    expect(side.value).toBe('A')
    expect(localStorage.getItem(STORAGE_KEY)).toBe('A')
  })

  it('set fija un lado concreto y comparte el estado entre llamadas', async () => {
    mockColorScheme(false)
    const useTheme = await freshUseTheme()
    useTheme().set('B')
    expect(useTheme().side.value).toBe('B')
    expect(localStorage.getItem(STORAGE_KEY)).toBe('B')
  })

  it('si localStorage lanza errores no rompe y usa la preferencia del sistema', async () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new DOMException('bloqueado', 'SecurityError')
    })
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new DOMException('bloqueado', 'SecurityError')
    })
    mockColorScheme(true)
    const useTheme = await freshUseTheme()
    const { side, toggle } = useTheme()
    expect(side.value).toBe('B')
    expect(() => toggle()).not.toThrow()
    expect(side.value).toBe('A')
    expect(document.documentElement.dataset.lado).toBe('A')
  })
})
