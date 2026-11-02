import { onBeforeUnmount, ref, type Ref } from 'vue'
import { ApiError } from '../api/http'

const ESPERA_MS = 250

export interface Busqueda {
  /** Texto del campo de búsqueda (enlazar con v-model). */
  busqueda: Ref<string>
  /** Texto cuyos resultados se muestran (para el mensaje de vacío). */
  buscado: Ref<string>
  cargando: Ref<boolean>
  error: Ref<string>
  /** Busca ya con el texto actual; la última petición gana. */
  buscar: () => Promise<void>
  /** Para @input: busca 250 ms después de dejar de escribir. */
  alEscribir: () => void
  /** Identifica la búsqueda en curso, para descartar respuestas de otras operaciones. */
  token: () => number
  esVigente: (token: number) => boolean
}

/**
 * Búsqueda con espera al escribir y descarte de respuestas obsoletas, compartida por las
 * listas de la cabina. `aplicar` recibe solo resultados de la petición más reciente.
 */
export function useBusqueda<T>(opciones: {
  consultar: (q: string) => Promise<T>
  aplicar: (resultado: T) => void
  /** Se llama si la última petición falla (p. ej. para vaciar resultados viejos). */
  alFallar?: () => void
  mensajeError: string
}): Busqueda {
  const busqueda = ref('')
  const buscado = ref('')
  const cargando = ref(true)
  const error = ref('')
  let temporizador: ReturnType<typeof setTimeout> | undefined
  let peticion = 0

  async function buscar(): Promise<void> {
    clearTimeout(temporizador)
    const q = busqueda.value.trim()
    const mia = ++peticion
    cargando.value = true
    error.value = ''
    try {
      const resultado = await opciones.consultar(q)
      if (mia !== peticion) return
      opciones.aplicar(resultado)
      buscado.value = q
    } catch (e) {
      if (mia !== peticion) return
      opciones.alFallar?.()
      error.value = e instanceof ApiError ? e.message : opciones.mensajeError
    } finally {
      if (mia === peticion) cargando.value = false
    }
  }

  function alEscribir(): void {
    clearTimeout(temporizador)
    temporizador = setTimeout(() => void buscar(), ESPERA_MS)
  }

  onBeforeUnmount(() => clearTimeout(temporizador))

  return { busqueda, buscado, cargando, error, buscar, alEscribir, token: () => peticion, esVigente: (t) => t === peticion }
}

/** Conjunto de ids con una operación en curso, para no repetirla. */
export function useOcupados(): {
  ocupados: Ref<ReadonlySet<string>>
  marcar: (id: string, activo: boolean) => void
} {
  const ocupados = ref<ReadonlySet<string>>(new Set())
  function marcar(id: string, activo: boolean): void {
    const nuevos = new Set(ocupados.value)
    if (activo) nuevos.add(id)
    else nuevos.delete(id)
    ocupados.value = nuevos
  }
  return { ocupados, marcar }
}
