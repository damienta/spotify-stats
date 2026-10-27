import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis } from 'recharts'

import { duration } from '@/lib/format'

export interface ChartPoint {
  label: string
  minutes: number
  highlight?: boolean
}

/** Minutes listened per hour, day or month, as green bars. */
export function MinutesChart({ points, height = 140 }: { points: ChartPoint[]; height?: number }) {
  // Only label every nth bar so 24 hours or 31 days don't overlap.
  const every = Math.ceil(points.length / 8)
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={points} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
        <XAxis
          dataKey="label"
          tickLine={false}
          axisLine={false}
          interval={every - 1}
          tick={{ fill: '#6a6a6a', fontSize: 11 }}
        />
        <Tooltip
          cursor={{ fill: 'rgba(255,255,255,0.05)' }}
          content={({ active, payload }) =>
            active && payload?.length ? (
              <div className="glass rounded-lg px-2.5 py-1.5 text-xs">
                <span className="text-muted">{payload[0].payload.label}</span>{' '}
                <span className="font-semibold">{duration(Number(payload[0].value))}</span>
              </div>
            ) : null
          }
        />
        <Bar dataKey="minutes" radius={[3, 3, 0, 0]} isAnimationActive>
          {points.map((p, i) => (
            <Cell key={i} fill={p.highlight ? '#1ed760' : '#1db954'} fillOpacity={p.minutes ? 1 : 0.2} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
