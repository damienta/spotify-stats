import { RefreshCw } from 'lucide-react'

import { ApiError, login } from '@/lib/api'
import { cn } from '@/lib/utils'

import { Button } from './ui/button'

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('animate-pulse rounded-xl bg-white/5', className)} />
}

/** What to show when a request failed: stats not built yet, reconnect, or try again. */
export function Problem({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const status = error instanceof ApiError ? error.status : 0
  if (status === 404) {
    return (
      <p className="py-6 text-center text-sm text-muted">
        Not ready yet. Stats are rebuilt every hour.
      </p>
    )
  }
  if (status === 403) {
    return (
      <div className="flex flex-col items-center gap-3 py-6 text-center text-sm text-muted">
        Spotify needs you to log in again to allow this.
        <Button size="sm" onClick={login}>
          Reconnect Spotify
        </Button>
      </div>
    )
  }
  return (
    <div className="flex flex-col items-center gap-3 py-6 text-center text-sm text-muted">
      Couldn't load this.
      {onRetry && (
        <Button size="sm" variant="glass" onClick={onRetry}>
          <RefreshCw className="size-3.5" /> Try again
        </Button>
      )}
    </div>
  )
}
