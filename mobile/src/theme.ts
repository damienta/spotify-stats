// Classic Spotify, like the web app: near-black surfaces, Spotify green, grey secondary text.
// The web app's glass is white at low opacity over the dark background; the same values here.

export const colors = {
  bg: '#121212',
  surface: '#181818',
  card: 'rgba(255,255,255,0.06)',
  border: 'rgba(255,255,255,0.1)',
  accent: '#1db954',
  accentBright: '#1ed760',
  text: '#ffffff',
  muted: '#b3b3b3',
  faint: '#6a6a6a',
  danger: '#f87171',
} as const

export const radius = { card: 16, art: 8 } as const

export const space = { page: 16, gap: 12, section: 28 } as const
