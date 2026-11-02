import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../../api/http'
import type { SongOut } from '../../api/types'

const { upload, uploadCover, mostrar } = vi.hoisted(() => ({
  upload: vi.fn(),
  uploadCover: vi.fn(),
  mostrar: vi.fn(),
}))

vi.mock('../../api/songs', () => ({ upload, uploadCover }))
vi.mock('../../composables/useAvisos', () => ({ useAvisos: () => ({ mostrar }) }))

import FormularioSubida from '../FormularioSubida.vue'

const MB = 1024 * 1024
const cancion: SongOut = {
  id: 's1',
  title: 'Granizo',
  artist: 'Los Meteoros',
  album: 'Pronóstico',
  duration_seconds: 12,
  is_active: true,
  has_cover: false,
}

function archivo(nombre: string, bytes = 10): File {
  return new File([new Uint8Array(bytes)], nombre)
}

async function llenar(wrapper: ReturnType<typeof mount>, file: File | null) {
  await wrapper.get('#subida-titulo').setValue('Granizo')
  await wrapper.get('#subida-artista').setValue('Los Meteoros')
  await wrapper.get('#subida-album').setValue('Pronóstico')
  if (file) {
    const input = wrapper.get('#subida-archivo')
    Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
    await input.trigger('change')
  }
}

describe('FormularioSubida', () => {
  beforeEach(() => {
    upload.mockReset()
    uploadCover.mockReset()
    mostrar.mockReset()
  })

  it('el selector acepta solo mp3, ogg y wav', () => {
    const wrapper = mount(FormularioSubida)
    expect(wrapper.get('#subida-archivo').attributes('accept')).toBe('.mp3,.ogg,.wav')
  })

  it('rechaza un .flac sin llamar al API', async () => {
    const wrapper = mount(FormularioSubida)
    await llenar(wrapper, archivo('tema.flac'))
    await wrapper.get('form').trigger('submit')

    expect(wrapper.text()).toContain('Formato no compatible. Usa MP3, OGG o WAV.')
    expect(upload).not.toHaveBeenCalled()
  })

  it('rechaza un archivo de 21 MB sin llamar al API', async () => {
    const wrapper = mount(FormularioSubida)
    await llenar(wrapper, archivo('tema.mp3', 21 * MB))
    await wrapper.get('form').trigger('submit')

    expect(wrapper.text()).toContain('El archivo pesa más de 20 MB.')
    expect(upload).not.toHaveBeenCalled()
  })

  it('pide los campos requeridos', async () => {
    const wrapper = mount(FormularioSubida)
    await wrapper.get('form').trigger('submit')

    expect(wrapper.text()).toContain('Escribe el título.')
    expect(wrapper.text()).toContain('Escribe el artista.')
    expect(wrapper.text()).toContain('Escribe el álbum.')
    expect(wrapper.text()).toContain('Elige un archivo MP3, OGG o WAV.')
    expect(upload).not.toHaveBeenCalled()
  })

  it('un envío válido manda FormData, avisa y emite subida', async () => {
    upload.mockResolvedValue(cancion)
    const wrapper = mount(FormularioSubida)
    const file = archivo('tema.wav')
    await llenar(wrapper, file)
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    const form = upload.mock.calls[0][0] as FormData
    expect(form.get('title')).toBe('Granizo')
    expect(form.get('artist')).toBe('Los Meteoros')
    expect(form.get('album')).toBe('Pronóstico')
    expect((form.get('file') as File).name).toBe('tema.wav')
    expect(mostrar).toHaveBeenCalledWith('Canción subida')
    expect(wrapper.emitted('subida')?.[0]).toEqual([cancion])
  })

  it('muestra el error invalid_audio del API', async () => {
    upload.mockRejectedValue(new ApiError(422, 'invalid_audio', 'texto del servidor'))
    const wrapper = mount(FormularioSubida)
    await llenar(wrapper, archivo('tema.mp3'))
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toContain('El archivo no es un audio válido.')
    expect(wrapper.emitted('subida')).toBeUndefined()
  })

  it('uploads cover after song', async () => {
    upload.mockResolvedValue(cancion)
    uploadCover.mockResolvedValue({ ...cancion, has_cover: true })
    const wrapper = mount(FormularioSubida)
    await llenar(wrapper, archivo('tema.mp3'))
    const portada = new File([new Uint8Array(10)], 'portada.png', { type: 'image/png' })
    const campo = wrapper.get('#subida-portada')
    Object.defineProperty(campo.element, 'files', { value: [portada], configurable: true })
    await campo.trigger('change')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(uploadCover).toHaveBeenCalledWith('s1', portada)
    expect(wrapper.emitted('subida')).toEqual([[{ ...cancion, has_cover: true }]])
  })

  it('cover failure keeps song and warns', async () => {
    upload.mockResolvedValue(cancion)
    uploadCover.mockRejectedValue(new ApiError(415, 'unsupported_image', 'x'))
    const wrapper = mount(FormularioSubida)
    await llenar(wrapper, archivo('tema.mp3'))
    const campo = wrapper.get('#subida-portada')
    Object.defineProperty(campo.element, 'files', {
      value: [new File([new Uint8Array(10)], 'p.png', { type: 'image/png' })],
      configurable: true,
    })
    await campo.trigger('change')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.emitted('subida')).toEqual([[cancion]])
    expect(mostrar).toHaveBeenCalledWith(
      'La canción se subió, pero la portada no. Inténtalo desde la tabla.',
      'error',
    )
  })

  it('rechaza una portada de más de 2 MB sin llamar al API', async () => {
    const wrapper = mount(FormularioSubida)
    await llenar(wrapper, archivo('tema.mp3'))
    const campo = wrapper.get('#subida-portada')
    Object.defineProperty(campo.element, 'files', {
      value: [new File([new Uint8Array(2 * MB + 1)], 'p.png', { type: 'image/png' })],
      configurable: true,
    })
    await campo.trigger('change')
    await wrapper.get('form').trigger('submit')

    expect(wrapper.text()).toContain('La portada debe pesar 2 MB o menos.')
    expect(upload).not.toHaveBeenCalled()
  })
})
