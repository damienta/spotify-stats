# Stats on your phone

The web app's screens as a phone app, built with Expo and React Native. It runs locally in
**Expo Go**; there's no App Store build. Plan and choices: [docs/plans/mobile.md](../docs/plans/mobile.md).

```bash
cd mobile
npm install
npx expo start          # scan the QR code with Expo Go (same Wi-Fi as this PC)
npx expo start --tunnel # if the phone can't reach the PC over Wi-Fi
npm run web             # the same app in a browser
```

For now it shows demo data; logging in with Spotify comes next.

Checks: `npm run typecheck` and `npm run lint`.
