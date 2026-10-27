/**
 * Adapted from Skiper UI — Skiper 41 (ProgressiveBlur).
 * https://skiper-ui.com — free version, attribution required.
 */
export function ProgressiveBlur({
  className = '',
  backgroundColor = '#05070b',
  position = 'top',
  height = '150px',
  blurAmount = '4px',
}: {
  className?: string
  backgroundColor?: string
  position?: 'top' | 'bottom'
  height?: string
  blurAmount?: string
}) {
  const isTop = position === 'top'

  return (
    <div
      aria-hidden="true"
      className={`pointer-events-none absolute left-0 w-full select-none ${className}`}
      style={{
        [isTop ? 'top' : 'bottom']: 0,
        height,
        background: isTop
          ? `linear-gradient(to top, transparent, ${backgroundColor})`
          : `linear-gradient(to bottom, transparent, ${backgroundColor})`,
        maskImage: isTop
          ? `linear-gradient(to bottom, ${backgroundColor} 50%, transparent)`
          : `linear-gradient(to top, ${backgroundColor} 50%, transparent)`,
        WebkitBackdropFilter: `blur(${blurAmount})`,
        backdropFilter: `blur(${blurAmount})`,
      }}
    />
  )
}
