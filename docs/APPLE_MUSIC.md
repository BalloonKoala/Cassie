# Apple Music on Cassie (Pi + web)

## Short answer

**Python cannot play Apple Music tracks like a library.** Apple Music uses DRM. On a Raspberry Pi there is no Apple Music app.

What Cassie does instead:

| Method | How it works | Limitation |
|--------|----------------|------------|
| **Web search (v3 default)** | Opens `music.apple.com/search?term=...` in Chromium | You log in once; you may tap Play manually |
| **Iframe on Cassie site** | Same URL inside the orb page | Autoplay often blocked until you interact |
| **Pi agent second window** | `apple_music.py` opens a separate Chromium profile | Music plays there; Cassie orb stays visible |
| **MusicKit JS (future)** | Apple Developer token + user login on your site | Best control; needs Apple Developer setup |

## What works today in Cassie v3

1. You say: **"Cassie, play jazz on Apple Music"**
2. Server (LLM) returns action `{ "action": "apple_music", "query": "jazz" }`
3. **Browser** loads Apple Music search in an overlay iframe
4. **Pi agent** also opens Apple Music in a logged-in Chromium profile (`~/.cassie-apple-music-profile`)

## One-time setup on Pi

```bash
# Log into Apple Music in the agent profile (once)
chromium-browser --user-data-dir=$HOME/.cassie-apple-music-profile https://music.apple.com
# Sign in with your Apple ID, then close
```

## What does NOT work (yet)

- "Play track 3 on playlist X" with no user interaction — needs **MusicKit** API
- Background Apple Music while orb is fullscreen in same tab — use agent's second window or MusicKit embed
- Spotify-style API from Python — Apple doesn't offer that for consumers on Linux

## Better long-term path

1. Enroll in [Apple Music API / MusicKit](https://developer.apple.com/musickit/)
2. Add developer token on server (secret)
3. User token after Sign in with Apple on `cassie.web.app`
4. Cassie sends song IDs to MusicKit player **inside your website** — orb stays up, music plays in-page

## Alternative if Apple Music on Pi is too painful

- **Spotify** — official API, easier automation (still needs Premium + dev app)
- **Local files** — agent plays MP3s with `mpg123` / pygame (100% automatable)
- **AirPlay** to HomePod from phone — Pi only shows orb (not Pi playback)
