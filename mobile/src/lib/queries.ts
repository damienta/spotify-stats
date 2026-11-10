// The same queries as the web app (web/src/lib/queries.ts), so caching and refresh behave alike.
// Only what Home needs so far; the other screens add theirs as they're built.

import { useQuery } from '@tanstack/react-query'

import { ApiError, api, type StatDocument } from './api'
import type { Me, NowPlaying, Recent } from './types'

// A 4xx won't fix itself on retry (not built yet, reconnect needed); anything else might.
const retry = (failures: number, error: unknown) =>
  !(error instanceof ApiError && error.status < 500) && failures < 2

export function useMe() {
  return useQuery({ queryKey: ['me'], queryFn: () => api<Me>('/me'), retry, staleTime: Infinity })
}

/** One stat document's data, e.g. useStat('top_artists', '4_weeks'). */
export function useStat<T>(name: string, window?: string) {
  const query = window ? `?window=${window}` : ''
  return useQuery({
    queryKey: ['stat', name, window],
    queryFn: () => api<StatDocument<T>>(`/me/stats/${name}${query}`),
    retry,
    // Stats change at most hourly, so a 5-minute-old copy is fine.
    staleTime: 5 * 60_000,
    select: (doc) => doc.data,
  })
}

export function useNowPlaying() {
  return useQuery({
    queryKey: ['now-playing'],
    queryFn: () => api<NowPlaying>('/me/now-playing'),
    retry,
    refetchInterval: 10_000,
  })
}

export function useRecent(limit = 10) {
  return useQuery({
    queryKey: ['recent', limit],
    queryFn: () => api<Recent>(`/me/recent?limit=${limit}`),
    retry,
    refetchInterval: 60_000,
  })
}
