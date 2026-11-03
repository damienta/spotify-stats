import { UserPlus } from 'lucide-react'

import { Artwork } from '@/components/Artwork'
import SpotlightCard from '@/components/SpotlightCard'
import { Problem, Skeleton } from '@/components/States'
import { Button } from '@/components/ui/button'
import { ApiError } from '@/lib/api'
import { useAcceptInvite, useInvitePreview } from '@/lib/queries'

/**
 * Opened from someone's invite link (/add/<invite>), after logging in if needed. Asks before
 * adding, so a link opened by mistake doesn't make a friendship.
 */
export function AddFriend({
  invite,
  onDone,
}: {
  invite: string
  onDone: (added: boolean) => void
}) {
  const preview = useInvitePreview(invite)
  const accept = useAcceptInvite()
  const status = preview.error instanceof ApiError ? preview.error.status : 0
  const p = preview.data

  let body
  if (status === 404) {
    body = (
      <Message title="This link doesn't work any more" onDone={() => onDone(false)}>
        Invite links last 14 days, and stop working if the sender resets theirs. Ask them for a new
        one.
      </Message>
    )
  } else if (preview.isError) {
    body = <Problem error={preview.error} onRetry={() => preview.refetch()} />
  } else if (!p) {
    body = <Skeleton className="h-48" />
  } else if (p.is_you) {
    body = (
      <Message title="That's your own link" onDone={() => onDone(false)}>
        Send it to a friend: when they open it, they can add you.
      </Message>
    )
  } else if (p.already_friends) {
    body = (
      <Message
        title={`You and ${p.display_name} are already friends`}
        onDone={() => onDone(true)}
      />
    )
  } else {
    const failed = accept.error instanceof ApiError ? accept.error : null
    body = (
      <SpotlightCard className="space-y-5 p-6 text-center">
        <Artwork name={p.display_name} round className="mx-auto size-20 text-2xl" />
        <div className="space-y-2">
          <h1 className="text-2xl font-extrabold tracking-tight">Add {p.display_name}?</h1>
          <p className="text-sm text-muted">
            You'll both see each other's top 10 artists and tracks, minutes this week, streak and
            taste match. Never your full history or recent plays. Turn sharing off or remove each
            other any time.
          </p>
        </div>
        {failed && (
          <p role="alert" className="text-sm text-red-400">
            {failed.status === 422
              ? 'One of you already has the most friends allowed (50).'
              : failed.status === 409
                ? "You're already friends."
                : "That didn't work. Try again in a minute."}
          </p>
        )}
        <div className="flex justify-center gap-2">
          <Button
            onClick={() => accept.mutate(invite, { onSuccess: () => onDone(true) })}
            disabled={accept.isPending}
          >
            <UserPlus className="size-4" />
            {accept.isPending ? 'Adding…' : 'Add'}
          </Button>
          <Button variant="ghost" onClick={() => onDone(false)} disabled={accept.isPending}>
            Not now
          </Button>
        </div>
      </SpotlightCard>
    )
  }
  return <div className="mx-auto max-w-md pt-8">{body}</div>
}

function Message({
  title,
  children,
  onDone,
}: {
  title: string
  children?: React.ReactNode
  onDone: () => void
}) {
  return (
    <SpotlightCard className="space-y-4 p-6 text-center">
      <h1 className="text-xl font-extrabold tracking-tight">{title}</h1>
      {children && <p className="text-sm text-muted">{children}</p>}
      <Button onClick={onDone}>Go to Friends</Button>
    </SpotlightCard>
  )
}
