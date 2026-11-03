import { createContext, useContext } from 'react'

/** Opens a friend's page from anywhere in the app; App provides it. */
export const OpenFriend = createContext<(userId: string) => void>(() => {})

export const useOpenFriend = () => useContext(OpenFriend)

const FRIEND = '/friend/'
const ADD = '/add/'
const PENDING_KEY = 'spotify-stats.invite'

/** The friend in the address bar (/friend/<id>), if any. */
export function friendInPath(path = window.location.pathname): string | null {
  if (!path.startsWith(FRIEND)) return null
  try {
    return decodeURIComponent(path.slice(FRIEND.length)) || null
  } catch {
    return null
  }
}

export const friendPath = (userId: string) => FRIEND + encodeURIComponent(userId)

/** The link to send a friend. Built here, not by the API, so it points at whichever site
 * you're on: the real one, a preview deployment or localhost. */
export const inviteLink = (invite: string) => `${window.location.origin}${ADD}${invite}`

/**
 * Picks up an invite from /add/<invite>, or one saved before logging in. Runs once, before
 * the first render (like finishLogin). The invite goes in sessionStorage so it survives the
 * trip to Spotify's login and back in this tab, and the address bar goes back to /.
 */
export function startInvite(): string | null {
  try {
    const path = window.location.pathname
    if (path.startsWith(ADD) && path.length > ADD.length) {
      sessionStorage.setItem(PENDING_KEY, decodeURIComponent(path.slice(ADD.length)))
      window.history.replaceState(null, '', '/')
    }
    return sessionStorage.getItem(PENDING_KEY)
  } catch {
    return null
  }
}

export function forgetInvite() {
  try {
    sessionStorage.removeItem(PENDING_KEY)
  } catch {
    // Nothing to forget.
  }
}
