import { Check, ChevronRight, Copy, Share2, UserPlus } from 'lucide-react'
import { useState } from 'react'

import { Artwork } from '@/components/Artwork'
import { Minutes } from '@/components/Minutes'
import { Section } from '@/components/Section'
import SpotlightCard from '@/components/SpotlightCard'
import { Problem, Skeleton } from '@/components/States'
import { Button } from '@/components/ui/button'
import { inviteLink, useOpenFriend } from '@/lib/friends'
import { useFriends, useInvite, useLeaderboard, useMe } from '@/lib/queries'
import type { Friend, LeaderRow } from '@/lib/types'
import { cn } from '@/lib/utils'

/** Your invite link, to copy or (on phones) share. Having the link is the approval. */
function InviteCard({ first }: { first: boolean }) {
  const invite = useInvite()
  const [copied, setCopied] = useState(false)
  const link = invite.data ? inviteLink(invite.data) : null
  const canShare = typeof navigator !== 'undefined' && 'share' in navigator

  const copy = async () => {
    if (!link) return
    try {
      await navigator.clipboard.writeText(link)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // No clipboard access: the link is on screen to copy by hand.
    }
  }
  const share = () => {
    if (link) navigator.share({ title: 'Be my friend on Stats', url: link }).catch(() => {})
  }

  return (
    <SpotlightCard className="space-y-4 p-5">
      <div className="flex items-start gap-3">
        <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-accent/15 text-accent">
          <UserPlus className="size-5" />
        </span>
        <div>
          <p className="font-bold">{first ? 'Add your first friend' : 'Invite a friend'}</p>
          <p className="text-sm text-muted">
            Send them your link. When they open it and tap Add, you're friends: you'll see each
            other's top 10s and this week's minutes, and how your tastes compare.
          </p>
        </div>
      </div>
      {invite.isError ? (
        <Problem error={invite.error} onRetry={() => invite.refetch()} />
      ) : (
        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            readOnly
            aria-label="Your invite link"
            value={link ?? 'Making your link…'}
            onFocus={(e) => e.target.select()}
            className="glass h-10 min-w-0 flex-1 rounded-full px-4 text-sm text-muted outline-none focus-visible:ring-2 focus-visible:ring-accent/60"
          />
          <div className="flex gap-2">
            <Button onClick={copy} disabled={!link} className="flex-1 sm:flex-none">
              {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
              {copied ? 'Copied' : 'Copy link'}
            </Button>
            {canShare && (
              <Button
                variant="glass"
                onClick={share}
                disabled={!link}
                className="flex-1 sm:flex-none"
              >
                <Share2 className="size-4" />
                Share
              </Button>
            )}
          </div>
        </div>
      )}
      <p className="text-xs text-faint">
        Links last 14 days. Anyone with yours can add you, so reset it in Settings if it ends up
        somewhere public.
      </p>
    </SpotlightCard>
  )
}

function Leaderboard() {
  const board = useLeaderboard()
  const openFriend = useOpenFriend()
  const me = useMe()
  return (
    <Section title="This week">
      <SpotlightCard className="p-2">
        {board.isError ? (
          <Problem error={board.error} onRetry={() => board.refetch()} />
        ) : !board.data ? (
          <Skeleton className="h-40" />
        ) : (
          <ol aria-label="Minutes listened this week">
            {board.data.map((row) => (
              <LeaderItem key={row.user_id} row={row} onOpen={() => openFriend(row.user_id)} />
            ))}
          </ol>
        )}
        {me.data && !me.data.share_with_friends && (
          <p className="px-3 pt-1 pb-2 text-xs text-faint">
            Sharing is off in Settings, so only you see yourself here.
          </p>
        )}
      </SpotlightCard>
    </Section>
  )
}

function LeaderItem({ row, onOpen }: { row: LeaderRow; onOpen: () => void }) {
  const body = (
    <>
      <span
        className={cn(
          'w-6 text-center text-sm font-bold tabular',
          row.rank === 1 ? 'text-accent' : 'text-faint',
        )}
      >
        {row.rank}
      </span>
      <Artwork name={row.display_name} round className="size-10 text-xs" />
      <span className="min-w-0 flex-1 truncate text-sm font-semibold">
        {row.is_you ? 'You' : row.display_name}
      </span>
      <Minutes value={row.minutes} hours={false} className="text-sm font-semibold" />
    </>
  )
  const className = 'flex w-full items-center gap-3 rounded-xl p-2 text-left'
  return (
    <li>
      {row.is_you ? (
        <div className={cn(className, 'bg-accent/10 ring-1 ring-accent/25')}>{body}</div>
      ) : (
        <button
          type="button"
          onClick={onOpen}
          className={cn(className, 'transition-colors hover:bg-white/5')}
        >
          {body}
        </button>
      )}
    </li>
  )
}

function FriendItem({ friend }: { friend: Friend }) {
  const openFriend = useOpenFriend()
  const body = (
    <>
      <Artwork name={friend.display_name} round className="size-12 text-sm" />
      <span className="min-w-0 flex-1">
        <span className="block truncate font-semibold">{friend.display_name}</span>
        <span className="block text-xs text-muted">
          {friend.sharing ? (
            <>
              <Minutes value={friend.minutes_this_week ?? 0} hours={false} /> this week
            </>
          ) : (
            "Isn't sharing their stats"
          )}
        </span>
      </span>
      {friend.sharing && <ChevronRight className="size-4 text-faint" />}
    </>
  )
  const className = 'flex w-full items-center gap-3 rounded-xl p-2 text-left'
  return (
    <li>
      {friend.sharing ? (
        <button
          type="button"
          onClick={() => openFriend(friend.user_id)}
          className={cn(className, 'transition-colors hover:bg-white/5')}
        >
          {body}
        </button>
      ) : (
        <div className={cn(className, 'opacity-70')}>{body}</div>
      )}
    </li>
  )
}

export function Friends() {
  const friends = useFriends()
  const none = friends.data?.length === 0
  return (
    <div className="space-y-8">
      <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">Friends</h1>
      <InviteCard first={none} />
      {friends.isError ? (
        <Problem error={friends.error} onRetry={() => friends.refetch()} />
      ) : !friends.data ? (
        <Skeleton className="h-48" />
      ) : (
        !none && (
          <div className="grid gap-8 lg:grid-cols-2">
            <Leaderboard />
            <Section title={`Your friends (${friends.data.length})`}>
              <SpotlightCard className="p-2">
                <ul>
                  {friends.data.map((f) => (
                    <FriendItem key={f.user_id} friend={f} />
                  ))}
                </ul>
              </SpotlightCard>
            </Section>
          </div>
        )
      )}
    </div>
  )
}
