import { StyleSheet, Text, View } from 'react-native'

import { duration } from '@/lib/format'
import { colors } from '@/theme'

export interface ChartPoint {
  label: string
  minutes: number
  highlight?: boolean
}

/**
 * Minutes listened per hour, day or month, as green bars. Plain views rather than a chart
 * library: bars and a few labels are all the web chart shows too.
 */
export function MinutesChart({ points, height = 120 }: { points: ChartPoint[]; height?: number }) {
  const max = Math.max(1, ...points.map((p) => p.minutes))
  // Only label every nth bar so 24 hours or 31 days don't overlap.
  const every = Math.ceil(points.length / 6)
  const busiest = points.reduce((a, b) => (b.minutes > a.minutes ? b : a), points[0])
  const total = points.reduce((sum, p) => sum + p.minutes, 0)
  // Screen readers get a sentence instead of the bars.
  const summary = busiest?.minutes
    ? `Bar chart: ${duration(total)} in total, busiest ${busiest.label} with ${duration(busiest.minutes)}.`
    : 'Bar chart: no listening yet.'

  return (
    <View accessible accessibilityRole="image" accessibilityLabel={summary}>
      <View style={[styles.bars, { height }]}>
        {points.map((p, i) => (
          <View
            key={i}
            style={[
              styles.bar,
              {
                height: `${Math.max(2, (p.minutes / max) * 100)}%`,
                backgroundColor: p.highlight ? colors.accentBright : colors.accent,
                opacity: p.minutes ? 1 : 0.2,
              },
            ]}
          />
        ))}
      </View>
      {/* One label per group of `every` bars, each as wide as its group so it never wraps. */}
      <View style={styles.labels}>
        {points
          .filter((_, i) => i % every === 0)
          .map((p, n) => (
            <Text
              key={p.label}
              style={[styles.label, { flex: Math.min(every, points.length - n * every) }]}
              numberOfLines={1}
            >
              {p.label}
            </Text>
          ))}
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  bars: { flexDirection: 'row', alignItems: 'flex-end', gap: 2 },
  bar: { flex: 1, borderTopLeftRadius: 3, borderTopRightRadius: 3 },
  labels: { flexDirection: 'row', marginTop: 4 },
  label: { color: colors.faint, fontSize: 10 },
})
