// The API client. Requests go to /api, which the Vite dev server forwards to the API Lambda.

import { demoApi, isDemo, leaveDemo } from './demo'

const TOKEN_KEY = 'spotify-stats.token'
const demo = isDemo()

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
  }
}

export function getToken(): string | null {
  if (demo) return 'demo'
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function setToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    // Private mode: the session lasts until the tab closes.
  }
}

/** Start "Log in with Spotify": the API sends the browser back to /auth with ?token=. */
export function login() {
  const back = `${window.location.origin}/auth`
  window.location.assign(`/api/auth/login?redirect_uri=${encodeURIComponent(back)}`)
}

/** On /auth, keep the session token from the login redirect. Returns an error, if any. */
export function finishLogin(): string | null {
  if (window.location.pathname !== '/auth') return null
  const params = new URLSearchParams(window.location.search)
  const token = params.get('token')
  if (token) setToken(token)
  window.history.replaceState(null, '', '/')
  return token ? null : (params.get('error') ?? 'login failed')
}

export function logout() {
  leaveDemo()
  setToken(null)
  window.location.assign('/')
}

/** Delete the account and all of its data, then log out. */
export async function deleteAccount() {
  if (!demo) {
    const response = await fetch('/api/me', {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${getToken() ?? ''}` },
    })
    // 404: already gone, which is what was asked for.
    if (!response.ok && response.status !== 404) throw new ApiError(response.status, 'delete failed')
  }
  logout()
}

export async function api<T>(path: string): Promise<T> {
  if (demo) return demoApi(path) as Promise<T>
  const response = await fetch(`/api${path}`, {
    headers: { Authorization: `Bearer ${getToken() ?? ''}` },
  })
  if (response.status === 401) {
    logout()
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new ApiError(response.status, body.detail ?? response.statusText)
  }
  return response.json() as Promise<T>
}

export interface StatDocument<T> {
  stat_name: string
  generated_at: string
  data: T
}

/** One stat document, e.g. stat('top_artists', '4_weeks'). */
export function stat<T>(name: string, window?: string) {
  const query = window ? `?window=${window}` : ''
  return api<StatDocument<T>>(`/me/stats/${name}${query}`).then((d) => d.data)
}
