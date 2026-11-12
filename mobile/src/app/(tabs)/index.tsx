import { Linking, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { Artwork } from '@/components/artwork'
import { Card, Section } from '@/components/card'
import { MinutesChart } from '@/components/minutes-chart'
import { NowPlayingCard } from '@/components/now-playing-card'
import { Problem, Skeleton } from '@/components/states'
import { ago, count, greeting, listened, timeTile } from '@/lib/format'
import { fillPeriod } from '@/lib/periods'
import { useMe, useRecent, useStat } from '@/lib/queries'
import type { Period, TopRow, Totals } from '@/lib/types'
import { colors, space } from '@/theme'

const open = (url?: string | null) => (url ? () => Linking.openURL(url) : undefined)

function Header() {
  const me = useMe()
  return (
    <Text style={styles.greeting} accessibilityRole="header">
      {greeting()},{'\n'}
      <Text style={styles.name}>{me.data?.display_name ?? ' '}</Text>
    </Text>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <Card style={styles.metric}>
      <Text style={styles.small}>{label}</Text>
      <Text style={styles.metricValue}>{value}</Text>
    </Card>
  )
}

/** Today's top artist or track, with its picture. Opens in Spotify. */
function TodayTop({ label, row, round }: { label: string; row?: TopRow; round?: boolean }) {
  return (
    <Card style={styles.todayTop}>
      <Pressable onPress={open(row?.url)} disabled={!row?.url} style={styles.rowLine}>
        {row && <Artwork src={row.image} name={row.name} size={52} round={round} />}
        <View style={styles.flex}>
          <Text style={styles.small}>{label}</Text>
          <Text style={styles.strong} numberOfLines={1}>
            {row?.name ?? '–'}
          </Text>
          {row && (
            <Text style={styles.small} numberOfLines={1}>
              {listened(row.hours * 60)}
              {row.artist_name && ` · ${row.artist_name}`}
            </Text>
          )}
        </View>
      </Pressable>
    </Card>
  )
}

function Today() {
  const totals = useStat<Totals>('totals', 'today')
  const hours = useStat<Period[]>('minutes_by_hour', 'today')
  const artists = useStat<TopRow[]>('top_artists', 'today')
  const tracks = useStat<TopRow[]>('top_tracks', 'today')
  const t = totals.data
  const time = timeTile(t ? t.hours * 60 : 0)
  return (
    <Section title="Today">
      <View style={styles.grid}>
        <Metric label={time.label} value={t ? time.value : '–'} />
        <Metric label="Streams" value={t ? count(t.streams) : '–'} />
        <Metric label="Artists" value={t ? count(t.artists) : '–'} />
        <Metric label="Tracks" value={t ? count(t.tracks) : '–'} />
      </View>
      <Card>
        <Text style={[styles.small, styles.chartTitle]}>Minutes by hour</Text>
        {hours.isError ? (
          <Problem error={hours.error} onRetry={() => hours.refetch()} />
        ) : hours.data ? (
          <MinutesChart points={fillPeriod('today', hours.data)} height={110} />
        ) : (
          <Skeleton height={126} />
        )}
      </Card>
      <TodayTop label="Top artist today" row={artists.data?.[0]} round />
      <TodayTop label="Top track today" row={tracks.data?.[0]} />
    </Section>
  )
}

function RecentlyPlayed() {
  const recent = useRecent(10)
  return (
    <Section title="Recently played">
      <Card style={styles.list}>
        {recent.isError ? (
          <Problem error={recent.error} onRetry={() => recent.refetch()} />
        ) : !recent.data ? (
          <Skeleton height={240} />
        ) : (
          recent.data.items.map(({ played_at, track }) => (
            <Pressable
              key={played_at}
              onPress={open(track.url)}
              disabled={!track.url}
              style={styles.recentRow}
            >
              <Artwork src={track.image} name={track.name ?? '?'} size={44} />
              <View style={styles.flex}>
                <Text style={styles.strong} numberOfLines={1}>
                  {track.name}
                </Text>
                <Text style={styles.small} numberOfLines={1}>
                  {track.artists.join(', ')}
                </Text>
              </View>
              <Text style={styles.ago}>{ago(played_at)}</Text>
            </Pressable>
          ))
        )}
      </Card>
    </Section>
  )
}

function TopArtists() {
  const top = useStat<TopRow[]>('top_artists', '4_weeks')
  return (
    <Section title="Your top artists recently">
      {top.isError ? (
        <Problem error={top.error} onRetry={() => top.refetch()} />
      ) : (
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.carousel}
          style={styles.bleed}
        >
          {top.data
            ? top.data.slice(0, 10).map((a) => (
                <Pressable key={a.name} onPress={open(a.url)} style={styles.artist}>
                  <Artwork src={a.image} name={a.name} size={104} round />
                  <Text style={[styles.strong, styles.center]} numberOfLines={1}>
                    {a.name}
                  </Text>
                  <Text style={[styles.small, styles.center]}>{listened(a.hours * 60)}</Text>
                </Pressable>
              ))
            : Array.from({ length: 4 }, (_, i) => <Skeleton key={i} height={104} width={104} round />)}
        </ScrollView>
      )}
    </Section>
  )
}

/** Home, laid out like the web app on a phone (layout E1): one column, the same cards. */
export default function Home() {
  const insets = useSafeAreaInsets()
  return (
    <ScrollView
      style={styles.screen}
      contentContainerStyle={[styles.content, { paddingTop: insets.top + 12 }]}
    >
      <Header />
      <NowPlayingCard />
      <Today />
      <RecentlyPlayed />
      <TopArtists />
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  content: { padding: space.page, gap: space.section, paddingBottom: 40 },
  greeting: { color: colors.text, fontSize: 34, fontWeight: '800', lineHeight: 40 },
  name: { color: colors.accent },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: space.gap },
  metric: { flexBasis: '47%', flexGrow: 1 },
  metricValue: {
    color: colors.text,
    fontSize: 28,
    fontWeight: '800',
    fontVariant: ['tabular-nums'],
  },
  chartTitle: { marginBottom: 8 },
  todayTop: { padding: 0 },
  rowLine: { flexDirection: 'row', alignItems: 'center', gap: 12, padding: 14 },
  flex: { flex: 1, minWidth: 0 },
  small: { color: colors.muted, fontSize: 12 },
  strong: { color: colors.text, fontSize: 15, fontWeight: '700' },
  list: { padding: 6 },
  recentRow: { flexDirection: 'row', alignItems: 'center', gap: 12, padding: 8 },
  ago: { color: colors.faint, fontSize: 12, fontVariant: ['tabular-nums'] },
  bleed: { marginHorizontal: -space.page },
  carousel: { paddingHorizontal: space.page, gap: 16 },
  artist: { width: 104, gap: 4 },
  center: { textAlign: 'center' },
})
