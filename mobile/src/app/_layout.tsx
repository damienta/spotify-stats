import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { DarkTheme, ThemeProvider } from 'expo-router'
import { Stack } from 'expo-router/stack'
import * as SplashScreen from 'expo-splash-screen'
import { StatusBar } from 'expo-status-bar'
import { useEffect } from 'react'

import { restoreSession, useSession } from '@/lib/session'
import { colors } from '@/theme'

// Keep the splash screen up until we know whether someone is logged in, so the login screen
// doesn't flash before Home.
SplashScreen.preventAutoHideAsync()
restoreSession()

const queryClient = new QueryClient()

// The navigation's own surfaces in the app's colours, so screens don't flash white between tabs.
const theme = {
  ...DarkTheme,
  colors: { ...DarkTheme.colors, background: colors.bg, card: colors.surface, primary: colors.accent },
}

export default function RootLayout() {
  const session = useSession()
  const inside = session.status === 'in' || session.status === 'demo'

  useEffect(() => {
    if (session.status !== 'loading') SplashScreen.hideAsync()
    // Logged out or switched between demo and a real account: drop the last person's data.
    if (session.status === 'out') queryClient.clear()
  }, [session.status])

  // The navigator always renders (the router needs it); while the token is read, the splash
  // screen still covers the login screen underneath.
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider value={theme}>
        <StatusBar style="light" />
        <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colors.bg } }}>
          {/* Logged out, only Login (and the login return address) exist; logged in or in the
              demo, only the tabs. Switching the session swaps them, so no screen navigates. */}
          <Stack.Protected guard={!inside}>
            <Stack.Screen name="login" />
            <Stack.Screen name="auth" />
          </Stack.Protected>
          <Stack.Protected guard={inside}>
            <Stack.Screen name="(tabs)" />
          </Stack.Protected>
        </Stack>
      </ThemeProvider>
    </QueryClientProvider>
  )
}
