import { useEffect } from 'react'
import { type DimensionValue, Pressable, StyleSheet, Text, View } from 'react-native'
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withTiming,
} from 'react-native-reanimated'

import { ApiError } from '@/lib/api'
import { colors } from '@/theme'

/** A grey block that gently pulses while data loads. */
export function Skeleton({
  height,
  width = '100%',
  round,
}: {
  height: number
  width?: DimensionValue
  round?: boolean
}) {
  const opacity = useSharedValue(0.5)
  useEffect(() => {
    opacity.value = withRepeat(withTiming(1, { duration: 800 }), -1, true)
  }, [opacity])
  const pulse = useAnimatedStyle(() => ({ opacity: opacity.value }))
  return (
    <Animated.View
      style={[styles.skeleton, { height, width, borderRadius: round ? height / 2 : 12 }, pulse]}
    />
  )
}

/** Something went wrong: say what, and offer to try again. */
export function Problem({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  const message =
    error instanceof ApiError && error.status === 404
      ? "This isn't ready yet. Your stats are rebuilt every hour."
      : "That didn't load."
  return (
    <View style={styles.problem}>
      <Text style={styles.message}>{message}</Text>
      <Pressable onPress={onRetry} accessibilityRole="button" hitSlop={8}>
        <Text style={styles.retry}>Try again</Text>
      </Pressable>
    </View>
  )
}

const styles = StyleSheet.create({
  skeleton: { backgroundColor: 'rgba(255,255,255,0.08)' },
  problem: { alignItems: 'center', gap: 8, paddingVertical: 12 },
  message: { color: colors.muted, fontSize: 14, textAlign: 'center' },
  retry: { color: colors.accent, fontSize: 14, fontWeight: '700' },
})
