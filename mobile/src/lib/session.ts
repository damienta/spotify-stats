// Who's using the app: nobody yet, the demo, or someone logged in with Spotify.
//
// The session token is kept in the phone's keychain (expo-secure-store), never in plain storage.
// Expo's web build has no keychain, so there it falls back to localStorage, like the web app.

import * as Linking from 'expo-linking'
import * as SecureStore from 'expo-secure-store'
import * as WebBrowser from 'expo-web-browser'
import { useSyncExternalStore } from 'react'
import { Platform } from 'react-native'

import { API_URL } from './config'

export type Session =
  | { status: 'loading' }
  | { status: 'out'; error?: string }
  | { status: 'demo' }
  | { status: 'in'; token: string }

const TOKEN_KEY = 'spotify-stats.token'

let current: Session = { status: 'loading' }
const listeners = new Set<() => void>()

function set(next: Session) {
  current = next
  listeners.forEach((l) => l())
}

const store = {
  get: (): Promise<string | null> =>
    Platform.OS === 'web'
      ? Promise.resolve(localStorage.getItem(TOKEN_KEY))
      : SecureStore.getItemAsync(TOKEN_KEY),
  put: (token: string): Promise<void> =>
    Platform.OS === 'web'
      ? Promise.resolve(localStorage.setItem(TOKEN_KEY, token))
      : SecureStore.setItemAsync(TOKEN_KEY, token),
  clear: (): Promise<void> =>
    Platform.OS === 'web'
      ? Promise.resolve(localStorage.removeItem(TOKEN_KEY))
      : SecureStore.deleteItemAsync(TOKEN_KEY),
}

/** Read the saved token once, when the app starts. */
export async function restoreSession() {
  try {
    const token = await store.get()
    set(token ? { status: 'in', token } : { status: 'out' })
  } catch {
    set({ status: 'out' })
  }
}

export function getSession(): Session {
  return current
}

export function useSession(): Session {
  return useSyncExternalStore(
    (listener) => {
      listeners.add(listener)
      return () => listeners.delete(listener)
    },
    () => current,
  )
}

/**
 * "Log in with Spotify". Opens the API's login in an in-app browser; Spotify sends you back to
 * the API, and the API back to this app's own address (exp://…/--/auth in Expo Go) with
 * ?token= or ?error=. The API only accepts return addresses it trusts, and exp:// is one.
 */
export async function login() {
  const back = Linking.createURL('auth')
  const result = await WebBrowser.openAuthSessionAsync(
    `${API_URL}/auth/login?redirect_uri=${encodeURIComponent(back)}`,
    back,
  )
  // Closing the browser isn't an error; just stay on the login screen.
  if (result.type !== 'success') return
  const { queryParams } = Linking.parse(result.url)
  const token = typeof queryParams?.token === 'string' ? queryParams.token : null
  if (!token) {
    set({ status: 'out', error: String(queryParams?.error ?? 'login failed') })
    return
  }
  await store.put(token)
  set({ status: 'in', token })
}

export function tryDemo() {
  set({ status: 'demo' })
}

/** Log out, or leave the demo. Forgets the token on this phone. */
export async function logout() {
  await store.clear().catch(() => undefined)
  set({ status: 'out' })
}
