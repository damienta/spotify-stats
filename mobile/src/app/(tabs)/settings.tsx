import type { ReactNode } from 'react'
import { Linking, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { Card, Section } from '@/components/card'
import { useMe } from '@/lib/queries'
import { logout, useSession } from '@/lib/session'
import { colors, space } from '@/theme'

function Row({ label, hint, children }: { label: string; hint?: string; children?: ReactNode }) {
  return (
    <View style={styles.row}>
      <View style={styles.flex}>
        <Text style={styles.label}>{label}</Text>
        {hint && <Text style={styles.hint}>{hint}</Text>}
      </View>
      {children}
    </View>
  )
}

function Button({ title, onPress, danger }: { title: string; onPress: () => void; danger?: boolean }) {
  return (
    <Pressable onPress={onPress} accessibilityRole="button" style={styles.button} hitSlop={6}>
      <Text style={[styles.buttonText, danger && styles.danger]}>{title}</Text>
    </Pressable>
  )
}

/** Account for now; display settings (minutes or hours, contrast) come with the next screens. */
export default function Settings() {
  const insets = useSafeAreaInsets()
  const session = useSession()
  const me = useMe()
  const demo = session.status === 'demo'

  return (
    <ScrollView
      style={styles.screen}
      contentContainerStyle={[styles.content, { paddingTop: insets.top + 12 }]}
    >
      <Text style={styles.title} accessibilityRole="header">
        Settings
      </Text>
      <Section title="Account">
        <Card style={styles.card}>
          <Row
            label={demo ? 'Demo' : 'Logged in as'}
            hint={demo ? 'Made-up listening, nothing real.' : (me.data?.display_name ?? '…')}
          >
            <Button title={demo ? 'Leave demo' : 'Log out'} onPress={logout} danger={!demo} />
          </Row>
          {!demo && (
            <Row label="Spotify access" hint="Stop this app reading your Spotify, on Spotify's site.">
              <Button
                title="Manage"
                onPress={() => Linking.openURL('https://www.spotify.com/account/apps/')}
              />
            </Row>
          )}
        </Card>
      </Section>
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  content: { padding: space.page, gap: space.section },
  title: { color: colors.text, fontSize: 32, fontWeight: '800' },
  card: { gap: 18 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  flex: { flex: 1 },
  label: { color: colors.text, fontSize: 15, fontWeight: '700' },
  hint: { color: colors.muted, fontSize: 13 },
  button: {
    borderColor: colors.border,
    borderWidth: 1,
    backgroundColor: colors.card,
    borderRadius: 999,
    paddingHorizontal: 16,
    paddingVertical: 9,
  },
  buttonText: { color: colors.text, fontWeight: '700' },
  danger: { color: colors.danger },
})
