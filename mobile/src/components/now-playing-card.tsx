import { Image } from 'expo-image'
import { useEffect, useState } from 'react'
import { Linking, Pressable, StyleSheet, Text, View } from 'react-native'
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withDelay,
  withRepeat,
  withTiming,
} from 'react-native-reanimated'

import { clock } from '@/lib/format'
import { useNowPlaying, useRecent } from '@/lib/queries'
import { colors } from '@/theme'

import { Artwork } from './artwork'
import { Card } from './card'
import { Problem, Skeleton } from './states'

function Bar({ delay }: { delay: number }) {
  const height = useSharedValue(4)
  useEffect(() => {
    height.value = withDelay(delay, withRepeat(withTiming(12, { duration: 500 }), -1, true))
  }, [delay, height])
  const style = useAnimatedStyle(() => ({ height: height.value }))
  return <Animated.View style={[styles.eqBar, style]} />
}

function Equalizer() {
  return (
    <View style={styles.eq} accessible={false}>
      {[0, 180, 360].map((d) => (
        <Bar key={d} delay={d} />
      ))}
    </View>
  )
}

/**
 * What's playing, polled every 10 seconds. Between polls the progress bar moves on by itself,
 * so it ticks every second like Spotify's own player. Tapping it opens the song in Spotify.
 */
export function NowPlayingCard() {
  const playing = useNowPlaying()
  const recent = useRecent()
  // A lazy initial value, so the clock is read once rather than on every render.
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(id)
  }, [])

  if (playing.isPending) return <Skeleton height={108} />
  if (playing.isError) {
    return (
      <Card>
        <Problem error={playing.error} onRetry={() => playing.refetch()} />
      </Card>
    )
  }

  const { track, is_playing, progress_ms } = playing.data
  const shown = track ?? recent.data?.items[0]?.track
  if (!shown) {
    return (
      <Card>
        <Text style={styles.nothing}>Nothing playing right now.</Text>
      </Card>
    )
  }

  const length = shown.duration_ms ?? 0
  const elapsed = track
    ? Math.min(length, (progress_ms ?? 0) + (is_playing ? now - playing.dataUpdatedAt : 0))
    : 0
  const label = !track ? 'Last played' : is_playing ? 'Now playing' : 'Paused'
  const url = shown.url

  return (
    <Card style={styles.card}>
      {shown.image && (
        <Image
          source={shown.image}
          style={[StyleSheet.absoluteFill, { opacity: 0.25 }]}
          blurRadius={40}
          accessible={false}
        />
      )}
      <Pressable
        onPress={url ? () => Linking.openURL(url) : undefined}
        disabled={!url}
        accessibilityRole={url ? 'link' : undefined}
        style={styles.row}
      >
        <Artwork src={shown.image} name={shown.name ?? '?'} size={72} />
        <View style={styles.body}>
          <View style={styles.labelRow}>
            {track && is_playing && <Equalizer />}
            <Text style={styles.label}>{label}</Text>
          </View>
          <Text style={styles.name} numberOfLines={1}>
            {shown.name}
          </Text>
          <Text style={styles.artists} numberOfLines={1}>
            {shown.artists.join(', ')}
          </Text>
          {track && length > 0 && (
            <View style={styles.progressRow}>
              <Text style={styles.time}>{clock(elapsed)}</Text>
              <View style={styles.track}>
                <View style={[styles.fill, { width: `${(elapsed / length) * 100}%` }]} />
              </View>
              <Text style={styles.time}>{clock(length)}</Text>
            </View>
          )}
        </View>
      </Pressable>
    </Card>
  )
}

const styles = StyleSheet.create({
  card: { padding: 0 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 14, padding: 14 },
  body: { flex: 1, minWidth: 0 },
  labelRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  label: { color: colors.accent, fontSize: 12, fontWeight: '700' },
  eq: { flexDirection: 'row', alignItems: 'flex-end', gap: 2, height: 12 },
  eqBar: { width: 3, borderRadius: 2, backgroundColor: colors.accent },
  name: { color: colors.text, fontSize: 17, fontWeight: '700', marginTop: 2 },
  artists: { color: colors.muted, fontSize: 14 },
  progressRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 8 },
  time: { color: colors.muted, fontSize: 11, fontVariant: ['tabular-nums'] },
  track: {
    flex: 1,
    height: 4,
    borderRadius: 2,
    backgroundColor: 'rgba(255,255,255,0.15)',
    overflow: 'hidden',
  },
  fill: { height: '100%', backgroundColor: colors.text },
  nothing: { color: colors.muted, textAlign: 'center', paddingVertical: 12 },
})
