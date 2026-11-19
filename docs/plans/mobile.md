# Phone app (Expo)

Status: PR 1 (set-up, demo data, Home) merged; PR 2 (login) built. Runs locally in Expo Go only: no App Store, no
EAS builds, no hosting.

## What it is

The web app's screens on a phone, talking to the same API. Damien picked layout **E1, like the
web app**: one column of the same cards, five tabs at the bottom (Home, Top, Stats, Friends,
Settings), Spotify green on near-black.

## How it runs

- `cd mobile && npx expo start`, then scan the QR code with the **Expo Go** app. Phone and PC on
  the same Wi-Fi, or `npx expo start --tunnel`.
- `npm run web` opens the same app in a browser, which is how screens are checked from a PC.
  Demo mode only there: the browser blocks calls to the API (no CORS on the Lambda), which a
  phone doesn't.
- Expo Go only runs the newest Expo SDK, so the project stays on it (SDK 58 now).

## Login (PR 2)

No API change is needed: `ALLOWED_REDIRECT_SCHEMES` already allows `exp://`, which is Expo Go's
address scheme.

1. The app opens `{API}/auth/login?redirect_uri=<Linking.createURL('auth')>` with
   `expo-web-browser`'s auth session.
2. Spotify returns to the API's callback, as for the web app.
3. The API redirects to `exp://…/--/auth?token=…`; the auth session hands that URL back.
4. The token goes in `expo-secure-store` (the phone's keychain), not plain storage.

The Spotify redirect URI in the developer dashboard doesn't change.

## Choices

| Choice | Why |
|---|---|
| **Expo Router tabs (`expo-router/js-tabs`)** | The same tab bar on iPhone and Android, styled in the app's colours. Native tabs look different on each and need a PNG per icon |
| **`StyleSheet` + `src/theme.ts`, not NativeWind** | Nothing to configure, works in Expo Go on every SDK. The colours are the web app's, in one file |
| **Bars drawn with plain views** | The charts are bars and a few labels; a chart library (Skia, victory-native) adds weight for nothing yet |
| **TanStack Query, same queries as the web** | Same caching, refetch and retry rules, so both apps behave alike |
| **Types, formatting and demo data copied from `web/src/lib`** | Simple for now. Move to a shared package once both apps change them often |
| **Reanimated for the equalizer and skeletons** | Already in Expo Go; runs on the UI thread |
| **`expo-image` for pictures** | Caches Spotify's artwork on the phone |
| **Demo mode first** | Screens are built and checked without logging in or showing real listening |

What doesn't carry over from the web: React Bits (Aurora, BlurText, SpotlightCard), Skiper UI,
shadcn/Radix and framer-motion are DOM libraries. Their effects get simple Reanimated versions
where they matter.

## PRs

1. **Set-up, demo mode, Home** (done): Expo project in `mobile/`, tab bar, Home in layout E1,
   placeholder tabs, CI (type-check and lint).
2. **Login and real data** (built): Login screen with "Try the demo first", Spotify login through
   Expo Go, token in the keychain, Settings with log out / leave demo. `Stack.Protected` guards
   swap Login and the tabs when the session changes, so no screen navigates by hand. A 401 from
   the API logs out.
3. **Top and Stats**: top 10, 50 and 100 for each window; day, week, month and year charts, the
   listening clock.
4. **Friends, artist pages, Settings**: Friends tab, friend page, invites through the share
   sheet, artist pages, minutes or hours, contrast.
