// Shapes of what the API returns (see api/src/stats_api/app.py and jobs/src/stats_jobs).

export interface Me {
  user_id: string
  display_name: string
}

export interface Track {
  id: string | null
  name: string | null
  artists: string[]
  album: string | null
  image: string | null
  duration_ms: number | null
  url: string | null
}

export interface NowPlaying {
  is_playing: boolean
  progress_ms: number | null
  track: Track | null
}

export interface Recent {
  items: { played_at: string; track: Track }[]
}

export interface Totals {
  streams: number
  hours: number
  artists: number
  tracks: number
  first_played: string
  last_played: string
}

export interface TopRow {
  name: string
  artist_name: string | null
  streams: number
  hours: number
}

export interface Period {
  start: string
  minutes: number
}

export interface ClockCell {
  weekday: number
  hour: number
  minutes: number
}

export interface Streak {
  days: number
  start: string | null
  end: string | null
}

export interface Streaks {
  current: Streak
  longest: Streak
}

export interface Skips {
  skip_rate: number | null
  most_skipped_artists: { name: string; plays: number; skip_rate: number }[]
}

export interface Discovery {
  artist_name: string
  first_played: string
  streams: number
}

export interface Repeat {
  track_name: string
  artist_name: string
  day: string
  streams: number
}
