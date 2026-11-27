import { motion } from 'framer-motion'
import type { ReactNode } from 'react'

import { fadeFrom, fadeTo, fadeTransition } from '@/lib/motion'
import { cn } from '@/lib/utils'

export function Section({
  title,
  action,
  children,
  className,
}: {
  title: string
  action?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <section className={cn('flex flex-col gap-3', className)}>
      <motion.div
        className="flex items-center justify-between gap-3 px-1"
        initial={fadeFrom}
        whileInView={fadeTo}
        viewport={{ once: true }}
        transition={fadeTransition}
      >
        <h2 className="text-lg font-bold tracking-tight">{title}</h2>
        {action}
      </motion.div>
      {children}
    </section>
  )
}
