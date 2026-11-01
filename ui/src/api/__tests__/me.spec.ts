import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import * as me from '../me'
import * as playlists from '../playlists'
import * as songs from '../songs'

describe('clientes de API nuevos', () => {
  const fetchMock = vi.fn()

  beforeEach(() => {
    fetchMock.mockReset()
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('follow codifica el artista en la ruta', async () => {
    await me.follow('Calle 13/Residente')
    expect(fetchMock.mock.calls[0][0]).toBe('/api/me/follows/Calle%2013%2FResidente')
    expect(fetchMock.mock.calls[0][1].method).toBe('PUT')
  })

  it('uploadCover envía FormData con el campo file por PUT', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ id: 's1' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    const file = new File(['x'], 'c.png', { type: 'image/png' })
    await songs.uploadCover('s1', file)
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/songs/s1/cover')
    expect(init.method).toBe('PUT')
    expect(init.body).toBeInstanceOf(FormData)
    expect((init.body as FormData).get('file')).toBeInstanceOf(File)
    expect(new Headers(init.headers).has('Content-Type')).toBe(false)
  })

  it('history arma limit y offset', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ items: [], total: 0 }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    await me.history(6, 12)
    expect(fetchMock.mock.calls[0][0]).toBe('/api/me/history?limit=6&offset=12')
  })

  it('las urls de portada apuntan a la API', () => {
    expect(songs.coverUrl('a')).toBe('/api/songs/a/cover')
    expect(playlists.coverUrl('b')).toBe('/api/playlists/b/cover')
  })
})
