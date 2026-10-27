# Web app

The Spotify stats web app: React + TypeScript + Vite, styled with Tailwind, shadcn/ui, Framer
Motion, React Bits (Aurora, SpotlightCard, BlurText) and Skiper UI (animated link, progressive
blur). Classic Spotify colours with glass cards.

It runs locally and talks to the deployed API through the Vite dev server, which forwards
`/api/*` to the API Lambda (so no CORS setup is needed).

```bash
npm install
npm run dev        # http://localhost:5173
```

- **Log in with Spotify** goes through the API's `/auth/login` and comes back to `/auth`.
- **Try the demo** (or open `/?demo`) shows made-up data without logging in, for testing and
  screenshots.
- Point it at another API with `API_URL=...` in `web/.env.local`.

Screens: **Home** (now playing, today's minutes and streams, top artists, recently played),
**Top** (tracks, artists, albums for 4 weeks to all time; genres coming), **Stats** (day, week,
month or year: total time, charts, listening clock, streaks, on repeat, new artists).

Skiper UI components are the free versions, used with attribution (https://skiper-ui.com).
