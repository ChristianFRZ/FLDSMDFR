/** Error de la API. `code` viene del cuerpo `{"error": {"code", "message"}}`. */
export class ApiError extends Error {
  status: number
  code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

const LOGIN_PATH = '/api/auth/login'

let unauthorizedHandler: (() => void) | null = null

/** Registra qué hacer ante un 401 (salvo en el login, donde 401 = credenciales incorrectas). */
export function onUnauthorized(handler: () => void): void {
  unauthorizedHandler = handler
}

async function readError(response: Response): Promise<ApiError> {
  try {
    const body = await response.json()
    const code = body?.error?.code
    const message = body?.error?.message
    if (typeof code === 'string' && typeof message === 'string') {
      return new ApiError(response.status, code, message)
    }
  } catch {
    // Cuerpo vacío o que no es JSON: se usa el error genérico.
  }
  return new ApiError(response.status, 'unknown_error', 'Algo salió mal. Vuelve a intentarlo.')
}

export async function request<T>(
  path: string,
  init: RequestInit & { json?: unknown } = {},
): Promise<T> {
  const { json, headers, ...rest } = init
  const finalHeaders = new Headers(headers)
  const options: RequestInit = { ...rest, credentials: 'same-origin', headers: finalHeaders }
  if (json !== undefined) {
    finalHeaders.set('Content-Type', 'application/json')
    options.body = JSON.stringify(json)
  }

  let response: Response
  try {
    response = await fetch(path, options)
  } catch {
    throw new ApiError(
      0,
      'network_error',
      'No pudimos conectar con el servidor. Revisa tu conexión y vuelve a intentarlo.',
    )
  }

  if (!response.ok) {
    const error = await readError(response)
    if (response.status === 401 && path !== LOGIN_PATH) unauthorizedHandler?.()
    throw error
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}
