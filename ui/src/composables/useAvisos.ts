import { readonly, ref, type Ref } from 'vue'

export type TipoAviso = 'info' | 'error'

export interface AvisoItem {
  id: number
  texto: string
  tipo: TipoAviso
}

const AUTODESCARTE_MS = 5000

// Estado singleton a nivel de módulo: los avisos se comparten entre vistas.
const avisos = ref<AvisoItem[]>([])
let siguienteId = 1

function descartar(id: number): void {
  avisos.value = avisos.value.filter((aviso) => aviso.id !== id)
}

function mostrar(texto: string, tipo: TipoAviso = 'info'): void {
  const id = siguienteId++
  avisos.value = [...avisos.value, { id, texto, tipo }]
  setTimeout(() => descartar(id), AUTODESCARTE_MS)
}

export function useAvisos(): {
  avisos: Readonly<Ref<readonly AvisoItem[]>>
  mostrar: (texto: string, tipo?: TipoAviso) => void
} {
  return { avisos: readonly(avisos), mostrar }
}
