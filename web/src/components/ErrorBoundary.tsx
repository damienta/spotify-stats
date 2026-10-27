import { Component, type ErrorInfo, type ReactNode } from 'react'

import { Button } from './ui/button'

/** If one screen crashes, show a way back instead of a blank page. */
export class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Screen crashed', error, info.componentStack)
  }

  render() {
    if (!this.state.failed) return this.props.children
    return (
      <div role="alert" className="flex flex-col items-center gap-4 py-24 text-center">
        <p className="text-lg font-bold">Something went wrong on this page.</p>
        <p className="text-sm text-muted">Your stats are safe. Reloading usually fixes it.</p>
        <Button onClick={() => window.location.reload()}>Reload</Button>
      </div>
    )
  }
}
