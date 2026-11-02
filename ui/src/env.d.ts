/// <reference types="vite/client" />

import 'vue-router'

declare module 'vue-router' {
  interface RouteMeta {
    /** La ruta requiere sesión iniciada. */
    auth?: boolean
    /** La ruta requiere rol admin. */
    admin?: boolean
    /** La vista ocupa toda la pantalla, sin barra lateral ni reproductor (acceso). */
    sinLayout?: boolean
  }
}

