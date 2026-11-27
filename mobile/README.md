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

Log in with Spotify, or tap **Try the demo first** for made-up data. In the browser build
(`npm run web`) only the demo works: browsers block direct calls to the API, phones don't.

Checks: `npm run typecheck` and `npm run lint`.
