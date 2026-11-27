import type { Transition } from 'framer-motion'

/**
 * How everything on a page appears: it un-blurs and settles into place over 0.6 seconds,
 * the same as the page titles (BlurText). Cards and section headings use this as they
 * scroll into view; list rows do the same in CSS (index.css, `main li`). Everything starts
 * together: titles un-blur all their words at once (delay={0}), and nothing is staggered.
 */
export const FADE_SECONDS = 0.6

export const fadeFrom = { opacity: 0, filter: 'blur(10px)', y: -8 }
export const fadeTo = { opacity: 1, filter: 'blur(0px)', y: 0 }
export const fadeTransition: Transition = { duration: FADE_SECONDS, ease: [0.2, 0.7, 0.2, 1] }
