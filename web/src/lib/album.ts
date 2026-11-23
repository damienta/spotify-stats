import { createContext, useContext } from 'react'

/** An album is its name plus its artist: "Greatest Hits" is many albums. */
export interface AlbumKey {
  name: string
  artist: string
}

/** Opens an album's page from anywhere in the app; App provides it. */
export const OpenAlbum = createContext<(album: AlbumKey) => void>(() => {})

export const useOpenAlbum = () => useContext(OpenAlbum)

const PREFIX = '/album/'

/** The album in the address bar (/album/<artist>/<album>), if any. */
export function albumInPath(path = window.location.pathname): AlbumKey | null {
  if (!path.startsWith(PREFIX)) return null
  const [artist, name] = path.slice(PREFIX.length).split('/')
  try {
    return artist && name
      ? { artist: decodeURIComponent(artist), name: decodeURIComponent(name) }
      : null
  } catch {
    return null
  }
}

export const albumPath = ({ name, artist }: AlbumKey) =>
  `${PREFIX}${encodeURIComponent(artist)}/${encodeURIComponent(name)}`

// Pages exist for each range's top 50 albums (stats_jobs.albums), so a row ranked within
// that always has one.
export const PAGES_FROM_EACH = 50
