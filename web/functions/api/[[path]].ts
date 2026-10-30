// Cloudflare Pages Function: forwards /api/* to the API Lambda, like the Vite dev server's
// proxy does locally. The browser only ever talks to this site, so the API needs no CORS.
// Set API_URL in the Pages project's settings to point somewhere else.

const DEFAULT_API = 'https://5o2g53vz3bhz4cgroqkvquvosm0dorcs.lambda-url.eu-north-1.on.aws'

interface Context {
  request: Request
  env: { API_URL?: string }
}

export async function onRequest({ request, env }: Context): Promise<Response> {
  const url = new URL(request.url)
  const target = new URL(url.pathname.replace(/^\/api/, '') + url.search, env.API_URL || DEFAULT_API)
  // Keep the method, headers (the Authorization bearer token) and body, but not Host: the
  // Lambda URL only answers to its own name.
  const headers = new Headers(request.headers)
  headers.delete('host')
  const hasBody = request.method !== 'GET' && request.method !== 'HEAD'
  // Redirects pass straight back to the browser: /auth/login sends it on to Spotify's login.
  return fetch(target, {
    method: request.method,
    headers,
    body: hasBody ? request.body : null,
    redirect: 'manual',
  })
}
