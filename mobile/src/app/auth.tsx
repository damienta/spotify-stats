import { Redirect } from 'expo-router'
import * as WebBrowser from 'expo-web-browser'

// Where the API sends you back after Spotify login (…/auth?token=…). In Expo Go the login
// browser catches this address itself; this screen only exists so the web build can close its
// login popup, and so the router has somewhere to land if the link arrives anyway.
WebBrowser.maybeCompleteAuthSession()

export default function Auth() {
  return <Redirect href="/login" />
}
