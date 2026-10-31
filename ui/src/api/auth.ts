import { request } from './http'
import type { TokenOut, UserOut } from './types'

export const login = (email: string, password: string) =>
  request<TokenOut>('/api/auth/login', { method: 'POST', json: { email, password } })

export const register = (name: string, email: string, password: string) =>
  request<TokenOut>('/api/auth/register', { method: 'POST', json: { name, email, password } })

export const logout = () => request<void>('/api/auth/logout', { method: 'POST' })

export const me = () => request<UserOut>('/api/auth/me')
