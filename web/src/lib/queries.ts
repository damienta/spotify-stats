import { useQuery } from '@tanstack/react-query'

import { ApiError, api, stat } from './api'
import type { Me, NowPlaying, Recent } from './types'

// A 4xx won't fix itself on retry (not built yet, reconnect needed); anything else might.
const retry = (failures: number, error: unknown) =>
  !(error instanceof ApiError && error.status < 500) && failures < 2

export function useMe() {
  return useQuery({ queryKey: ['me'], queryFn: () => api<Me>('/me'), retry, staleTime: Infinity })
}

/** One stat document; they change at most hourly, so cache them for 5 minutes. */
export function useStat<T>(name: string, window?: string) {
  return useQuery({
    queryKey: ['stat', name, window],
    queryFn: () => stat<T>(name, window),
    retry,
    staleTime: 5 * 60_000,
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
