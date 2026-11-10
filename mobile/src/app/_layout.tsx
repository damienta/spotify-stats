import Ionicons from '@expo/vector-icons/Ionicons'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { DarkTheme, ThemeProvider } from 'expo-router'
import { Tabs } from 'expo-router/js-tabs'
import { StatusBar } from 'expo-status-bar'
import type { ComponentProps } from 'react'

import { colors } from '@/theme'

const queryClient = new QueryClient()

// The navigation's own surfaces in the app's colours, so screens don't flash white between tabs.
const theme = {
  ...DarkTheme,
  colors: { ...DarkTheme.colors, background: colors.bg, card: colors.surface, primary: colors.accent },
}

type IconName = ComponentProps<typeof Ionicons>['name']

/** The five tabs, as on the web app: icon outlined, filled when it's the open tab. */
const TABS: { name: string; title: string; icon: IconName; active: IconName }[] = [
  { name: 'index', title: 'Home', icon: 'home-outline', active: 'home' },
  { name: 'top', title: 'Top', icon: 'trophy-outline', active: 'trophy' },
  { name: 'stats', title: 'Stats', icon: 'stats-chart-outline', active: 'stats-chart' },
  { name: 'friends', title: 'Friends', icon: 'people-outline', active: 'people' },
  { name: 'settings', title: 'Settings', icon: 'settings-outline', active: 'settings' },
]

export default function Layout() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider value={theme}>
        <StatusBar style="light" />
        <Tabs
          screenOptions={{
            headerShown: false,
            tabBarActiveTintColor: colors.accent,
            tabBarInactiveTintColor: colors.muted,
            tabBarStyle: { backgroundColor: colors.surface, borderTopColor: colors.border },
          }}
        >
          {TABS.map((t) => (
            <Tabs.Screen
              key={t.name}
              name={t.name}
              options={{
                title: t.title,
                tabBarIcon: ({ color, size, focused }) => (
                  <Ionicons name={focused ? t.active : t.icon} color={color as string} size={size} />
                ),
              }}
            />
          ))}
        </Tabs>
      </ThemeProvider>
    </QueryClientProvider>
  )
}
