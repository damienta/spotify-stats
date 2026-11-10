import { StyleSheet, Text, View } from 'react-native'

import { colors } from '@/theme'

/** A tab that's planned but not built yet: says what's coming, so it doesn't look broken. */
export function ComingSoon({ title, what }: { title: string; what: string }) {
  return (
    <View style={styles.screen}>
      <Text style={styles.title} accessibilityRole="header">
        {title}
      </Text>
      <Text style={styles.what}>{what}</Text>
      <Text style={styles.note}>Coming in the next update. The web app has it already.</Text>
    </View>
  )
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.bg,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 32,
    gap: 8,
  },
  title: { color: colors.text, fontSize: 28, fontWeight: '800' },
  what: { color: colors.muted, fontSize: 15, textAlign: 'center' },
  note: { color: colors.faint, fontSize: 13, textAlign: 'center', marginTop: 8 },
})
