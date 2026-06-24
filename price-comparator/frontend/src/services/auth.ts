import Cookies from 'js-cookie'
import api from './api'
import type { AuthToken, User } from '@/types'

export async function login(email: string, password: string): Promise<AuthToken> {
  const { data } = await api.post<AuthToken>('/auth/login', { email, password })
  Cookies.set('token', data.access_token, { expires: 1, sameSite: 'strict' })
  Cookies.set('user', JSON.stringify({
    id: data.user_id, name: data.name, email: data.email, role: data.role,
  }), { expires: 1 })
  return data
}

export function logout() {
  Cookies.remove('token')
  Cookies.remove('user')
  window.location.href = '/auth/login'
}

export function getStoredUser(): Partial<User> | null {
  const raw = Cookies.get('user')
  if (!raw) return null
  try { return JSON.parse(raw) } catch { return null }
}

export function isAuthenticated(): boolean {
  return !!Cookies.get('token')
}

export async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  await api.post('/auth/change-password', {
    current_password: currentPassword,
    new_password: newPassword,
  })
}

export async function forgotPassword(email: string): Promise<{ token: string; expires_at: string }> {
  const { data } = await api.post('/auth/forgot-password', { email })
  return data
}

export async function resetPassword(token: string, newPassword: string): Promise<void> {
  await api.post('/auth/reset-password', { token, new_password: newPassword })
}
