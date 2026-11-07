# Cliente HTTP

| Archivo | Para qué sirve |
| --- | --- |
| [`client.ts`](client.ts) | Peticiones a la API, sesión, descargas y subidas |
| [`queries.ts`](queries.ts) | Consultas de TanStack Query que usan varias pantallas |
| [`types.ts`](types.ts) | Tipos de lo que devuelve la API |

`api<T>(path, opts)` añade el token a cada petición. Ante un `401`, lo renueva con el refresh token y reintenta una sola vez. Si varias peticiones vencen a la vez, comparten la misma renovación. Los errores se lanzan como `ApiError(status, code, message)`.

`upload()` usa `XMLHttpRequest` porque `fetch` no informa del avance de una subida.

El access token vive solo en memoria. El refresh token se guarda en `localStorage` para sobrevivir a una recarga.
