import { request } from './http'
import type { Role, UserOut } from './types'

export const list = (q?: string) =>
  request<UserOut[]>(`/api/users${q ? `?q=${encodeURIComponent(q)}` : ''}`)

export const setRole = (id: string, role: Role) =>
  request<UserOut>(`/api/users/${id}/role`, { method: 'PATCH', json: { role } })
