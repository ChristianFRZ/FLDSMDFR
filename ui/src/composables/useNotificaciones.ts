import { computed, ref } from 'vue'
import * as invites from '../api/invites'
import * as me from '../api/me'
import type { NotificationOut } from '../api/types'
import { useAvisos } from './useAvisos'
import { useCasetes } from './useCasetes'

/** Cada cuánto se consultan los avisos mientras la pestaña está visible (spec: ~30 s). */
export const INTERVALO_AVISOS_MS = 30_000

// Estado singleton: la campana y el panel comparten la misma lista.
const items = ref<NotificationOut[]>([])
const noLeidos = computed(() => items.value.filter((aviso) => !aviso.read).length)

let temporizador: ReturnType<typeof setInterval> | null = null
let consultando = false

const visible = () => document.visibilityState === 'visible'

/** Errores de red se callan: el siguiente ciclo vuelve a intentarlo. */
async function refrescar(): Promise<void> {
  if (consultando) return
  consultando = true
  try {
    items.value = (await me.notifications()).items
  } catch {
    // Silencioso a propósito (spec §avisos).
  } finally {
    consultando = false
  }
}

function onVisibilidad(): void {
  if (visible()) void refrescar()
}

function iniciar(): void {
  if (temporizador !== null) return
  document.addEventListener('visibilitychange', onVisibilidad)
  temporizador = setInterval(() => {
    if (visible()) void refrescar()
  }, INTERVALO_AVISOS_MS)
  if (visible()) void refrescar()
}

function detener(): void {
  if (temporizador !== null) clearInterval(temporizador)
  temporizador = null
  document.removeEventListener('visibilitychange', onVisibilidad)
}

function reiniciar(): void {
  detener()
  items.value = []
}

/** Optimista: si el servidor falla, el siguiente sondeo restaura el estado real. */
async function marcarLeidos(ids: string[]): Promise<void> {
  const pendientes = ids.filter((id) => items.value.some((a) => a.id === id && !a.read))
  if (pendientes.length === 0) return
  items.value = items.value.map((a) => (pendientes.includes(a.id) ? { ...a, read: true } : a))
  try {
    await me.markRead(pendientes)
  } catch {
    // Se reintenta la próxima vez que se abra la campana.
  }
}

function quitarInvitacion(token: string): NotificationOut | undefined {
  const aviso = items.value.find((a) => a.invite?.token === token)
  items.value = items.value.filter((a) => a.invite?.token !== token)
  return aviso
}

async function responder(token: string, aceptar: boolean): Promise<void> {
  const { mostrar } = useAvisos()
  try {
    if (aceptar) await invites.accept(token)
    else await invites.ignore(token)
  } catch {
    mostrar('No pudimos responder la invitación. Vuelve a intentarlo.', 'error')
    return
  }
  const aviso = quitarInvitacion(token)
  const nombre = aviso?.invite?.playlist_name ?? 'el casete'
  if (aceptar) {
    await useCasetes().cargar()
    mostrar(`Ya formas parte de «${nombre}».`)
  } else {
    mostrar(`Ignoraste la invitación a «${nombre}».`)
  }
}

const aceptar = (token: string) => responder(token, true)
const ignorar = (token: string) => responder(token, false)

export function useNotificaciones() {
  return { items, noLeidos, refrescar, iniciar, detener, reiniciar, marcarLeidos, aceptar, ignorar }
}
