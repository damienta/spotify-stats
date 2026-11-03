import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { ApiError, api, type StatDocument } from './api'
import type {
  ArtistPage,
  Compare,
  Friend,
  FriendSummary,
  InvitePreview,
  LeaderRow,
  Me,
  NowPlaying,
  Recent,
} from './types'

// A 4xx won't fix itself on retry (not built yet, reconnect needed); anything else might.
const retry = (failures: number, error: unknown) =>
  !(error instanceof ApiError && error.status < 500) && failures < 2

export function useMe() {
  return useQuery({ queryKey: ['me'], queryFn: () => api<Me>('/me'), retry, staleTime: Infinity })
}

function statQuery<T>(name: string, window?: string) {
  const query = window ? `?window=${window}` : ''
  return {
    queryKey: ['stat', name, window],
    queryFn: () => api<StatDocument<T>>(`/me/stats/${name}${query}`),
    retry,
    // Stats change at most hourly, so a 5-minute-old copy is fine.
    staleTime: 5 * 60_000,
  }
}

/** One stat document's data, e.g. useStat('top_artists', '4_weeks'). */
export function useStat<T>(name: string, window?: string) {
  return useQuery({ ...statQuery<T>(name, window), select: (doc) => doc.data })
}

/** One of your top artists' pages; a 404 means they aren't in your top artists. */
export function useArtist(name: string) {
  return useQuery({
    queryKey: ['stat', 'artist', name.toLowerCase()],
    queryFn: () => api<StatDocument<ArtistPage>>(`/me/artist?name=${encodeURIComponent(name)}`),
    retry,
    staleTime: 5 * 60_000,
    select: (doc) => doc.data,
  })
}

/** When a stat document was built; shares the cached request with useStat. */
export function useStatBuiltAt(name: string, window?: string) {
  return useQuery({ ...statQuery<unknown>(name, window), select: (doc) => doc.generated_at })
}

/** Fetch every stat again, ignoring the 5-minute cache. */
export function useRefreshStats() {
  const client = useQueryClient()
  return () => client.invalidateQueries({ queryKey: ['stat'] })
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

// Friends. Every friends query shares the 'friends' key, so adding or removing someone
// refetches them all.

export function useFriends() {
  return useQuery({
    queryKey: ['friends', 'list'],
    queryFn: () => api<{ friends: Friend[] }>('/friends').then((r) => r.friends),
    retry,
  })
}

export function useLeaderboard() {
  return useQuery({
    queryKey: ['friends', 'leaderboard'],
    queryFn: () =>
      api<{ leaderboard: LeaderRow[] }>('/friends/leaderboard').then((r) => r.leaderboard),
    retry,
    staleTime: 5 * 60_000,
  })
}

export function useInvite() {
  return useQuery({
    queryKey: ['friends', 'invite'],
    queryFn: () => api<{ invite: string }>('/friends/invite').then((r) => r.invite),
    retry,
    staleTime: Infinity,
  })
}

export function useInvitePreview(invite: string | null) {
  return useQuery({
    queryKey: ['friends', 'preview', invite],
    queryFn: () =>
      api<InvitePreview>('/friends/invite/preview', { method: 'POST', body: { invite } }),
    enabled: invite !== null,
    retry,
  })
}

// A friend's stats are as fresh as their hourly build, like your own.
export function useFriendSummary(userId: string) {
  return useQuery({
    queryKey: ['friends', 'summary', userId],
    queryFn: () => api<FriendSummary>(`/friends/${encodeURIComponent(userId)}/summary`),
    retry,
    staleTime: 5 * 60_000,
  })
}

export function useCompare(userId: string) {
  return useQuery({
    queryKey: ['friends', 'compare', userId],
    queryFn: () => api<Compare>(`/friends/${encodeURIComponent(userId)}/compare`),
    retry,
    staleTime: 5 * 60_000,
  })
}

function useFriendsChanged() {
  const client = useQueryClient()
  return () => client.invalidateQueries({ queryKey: ['friends'] })
}

export function useAcceptInvite() {
  const changed = useFriendsChanged()
  return useMutation({
    mutationFn: (invite: string) =>
      api<{ user_id: string; display_name: string }>('/friends', {
        method: 'POST',
        body: { invite },
      }),
    onSuccess: changed,
  })
}

export function useRemoveFriend() {
  const changed = useFriendsChanged()
  return useMutation({
    mutationFn: (userId: string) =>
      api<void>(`/friends/${encodeURIComponent(userId)}`, { method: 'DELETE' }),
    onSuccess: changed,
  })
}

export function useResetInvite() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: () => api<{ invite: string }>('/friends/invite/reset', { method: 'POST' }),
    onSuccess: (r) => client.setQueryData(['friends', 'invite'], r.invite),
  })
}

export function useSetSharing() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (share: boolean) =>
      api<Me>('/me', { method: 'PATCH', body: { share_with_friends: share } }),
    onSuccess: (me) => {
      client.setQueryData(['me'], me)
      // You drop off (or back onto) friends' boards; your own board shows you either way.
      client.invalidateQueries({ queryKey: ['friends'] })
    },
  })
}
