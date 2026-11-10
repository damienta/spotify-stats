// The API client. The phone calls the API Lambda directly: there's no browser, so no CORS and
// no /api proxy like the web app has.
//
// For now the app only runs in demo mode; logging in with Spotify comes in the next PR.

import { demoApi } from './demo'

export const API_URL = 'https://5o2g53vz3bhz4cgroqkvquvosm0dorcs.lambda-url.eu-north-1.on.aws'

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
  return demoApi(path, send) as Promise<T>
}
