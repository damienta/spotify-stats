import { Image } from 'expo-image'
import { StyleSheet, Text, View } from 'react-native'

import { colors, radius } from '@/theme'

const initials = (name: string) =>
  name
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? '')
    .join('')

/**
 * A cover or artist photo from Spotify's image servers, cached on the phone by expo-image.
 * Without a picture (demo mode, or not looked up yet) it shows initials, like the web app.
 */
export function Artwork({
  src,
  name,
  size,
  round,
}: {
  src?: string | null
  name: string
  size: number
  round?: boolean
}) {
  const shape = { width: size, height: size, borderRadius: round ? size / 2 : radius.art }
  if (src) {
    return <Image source={src} style={shape} contentFit="cover" transition={200} accessible={false} />
  }
  return (
    <View style={[styles.fallback, shape]}>
      <Text style={[styles.initials, { fontSize: Math.max(11, size / 3.2) }]}>{initials(name)}</Text>
    </View>
  )
}

const styles = StyleSheet.create({
  fallback: { backgroundColor: '#1f3a29', alignItems: 'center', justifyContent: 'center' },
  initials: { color: colors.accentBright, fontWeight: '700' },
})
