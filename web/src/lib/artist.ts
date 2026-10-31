import { createContext, useContext } from 'react'

/** Opens an artist's page from anywhere in the app; App provides it. */
export const OpenArtist = createContext<(name: string) => void>(() => {})

export const useOpenArtist = () => useContext(OpenArtist)

const PREFIX = '/artist/'

/** The artist in the address bar (/artist/<name>), if any. */
export function artistInPath(path = window.location.pathname): string | null {
  if (!path.startsWith(PREFIX)) return null
  try {
    return decodeURIComponent(path.slice(PREFIX.length)) || null
  } catch {
    return null
  }
}

export const artistPath = (name: string) => PREFIX + encodeURIComponent(name)
