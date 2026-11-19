import { useState } from 'react'
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { Artwork } from '@/components/artwork'
import { Card } from '@/components/card'
import { login, tryDemo, useSession } from '@/lib/session'
import { colors, space } from '@/theme'

// The web login page's made-up preview: never real artists in promotion.
const PREVIEW = [
  { name: 'Nova Lane', minutes: '1,748 minutes' },
  { name: 'The Static', minutes: '1,406 minutes' },
  { name: 'Kairo', minutes: '1,159 minutes' },
]

const MESSAGES: Record<string, string> = {
  access_denied: 'Spotify login was cancelled.',
}

export default function Login() {
  const insets = useSafeAreaInsets()
  const session = useSession()
  const [busy, setBusy] = useState(false)
  const [failed, setFailed] = useState(false)
  const error = session.status === 'out' ? session.error : undefined

  const start = async () => {
    setBusy(true)
    setFailed(false)
    try {
      await login()
    } catch {
      setFailed(true)
    } finally {
      setBusy(false)
    }
  }

  return (
    <View style={[styles.screen, { paddingTop: insets.top + 40, paddingBottom: insets.bottom + 24 }]}>
      <Text style={styles.title} accessibilityRole="header">
        Your listening,{'\n'}
        <Text style={styles.accent}>in numbers.</Text>
      </Text>
      <Text style={styles.lead}>
        Your own Wrapped, all year round: top artists, when you listen, streaks, and gigs by the
        artists you play most.
      </Text>

      <Card style={styles.preview}>
        <Text style={styles.previewTitle}>Your top artists, 4 weeks</Text>
        {PREVIEW.map((a, i) => (
          <View key={a.name} style={styles.previewRow}>
            <Text style={styles.rank}>{i + 1}</Text>
            <Artwork name={a.name} size={36} round />
            <Text style={styles.previewName}>{a.name}</Text>
            <Text style={styles.previewMinutes}>{a.minutes}</Text>
          </View>
        ))}
      </Card>

      <View style={styles.actions}>
        {(error || failed) && (
          <Text style={styles.error} accessibilityRole="alert">
            {failed
              ? "Couldn't open Spotify login. Check your connection and try again."
              : (MESSAGES[error ?? ''] ?? "That didn't work. Try logging in again.")}
          </Text>
        )}
        <Pressable
          onPress={start}
          disabled={busy}
          accessibilityRole="button"
          style={({ pressed }) => [styles.primary, pressed && styles.pressed]}
        >
          {busy ? (
            <ActivityIndicator color="#000" />
          ) : (
            <Text style={styles.primaryText}>Log in with Spotify</Text>
          )}
        </Pressable>
        <Pressable onPress={tryDemo} accessibilityRole="button" style={styles.secondary}>
          <Text style={styles.secondaryText}>Try the demo first</Text>
        </Pressable>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg, paddingHorizontal: space.page, gap: 20 },
  title: { color: colors.text, fontSize: 40, fontWeight: '800', lineHeight: 46 },
  accent: { color: colors.accent },
  lead: { color: colors.muted, fontSize: 16, lineHeight: 23 },
  preview: { gap: 10 },
  previewTitle: { color: colors.muted, fontSize: 12 },
  previewRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  rank: { color: colors.faint, width: 14, fontWeight: '700' },
  previewName: { color: colors.text, fontWeight: '700', flex: 1 },
  previewMinutes: { color: colors.muted, fontSize: 12 },
  actions: { marginTop: 'auto', gap: 12 },
  error: { color: colors.danger, textAlign: 'center' },
  primary: {
    backgroundColor: colors.accent,
    borderRadius: 999,
    height: 52,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pressed: { backgroundColor: colors.accentBright },
  primaryText: { color: '#000', fontSize: 16, fontWeight: '800' },
  secondary: { height: 48, alignItems: 'center', justifyContent: 'center' },
  secondaryText: { color: colors.text, fontSize: 15, fontWeight: '700' },
})
