// The API client. The phone calls the API Lambda directly: there's no browser, so no CORS and
// no /api proxy like the web app has.

import { API_URL } from './config'
import { demoApi } from './demo'
import { ApiError } from './errors'
import { getSession, logout } from './session'

export { API_URL } from './config'
export { ApiError } from './errors'

export interface Send {
  method: 'POST' | 'PATCH' | 'DELETE'
  body?: unknown
}

export interface StatDocument<T> {
  stat_name: string
  generated_at: string
  data: T
}

export async function api<T>(path: string, send?: Send): Promise<T> {
  const session = getSession()
  if (session.status === 'demo') return demoApi(path, send) as Promise<T>
  if (session.status !== 'in') throw new ApiError(401, 'not logged in')

  const response = await fetch(`${API_URL}${path}`, {
    method: send?.method ?? 'GET',
    headers: {
      Authorization: `Bearer ${session.token}`,
      ...(send?.body !== undefined && { 'Content-Type': 'application/json' }),
    },
    body: send?.body !== undefined ? JSON.stringify(send.body) : undefined,
  })
  // The session has expired or been revoked: back to the login screen.
  if (response.status === 401) await logout()
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new ApiError(response.status, body.detail ?? `HTTP ${response.status}`)
  }
  // 204 No Content (removing a friend) has no body to read.
  return (response.status === 204 ? undefined : response.json()) as Promise<T>
}
