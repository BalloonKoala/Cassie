# Cassie v3 — web + agent + server

Three parts:

```
┌─────────────┐     WebSocket      ┌──────────────┐     OpenRouter
│  web/       │ ◄────────────────► │  server/     │ ◄──────────────► STT / LLM / TTS
│  (orb UI)   │                    │  (brain)     │
└─────────────┘                    └──────▲───────┘
       ▲                                  │
       │ kiosk browser                    │ WebSocket
┌──────┴──────┐                    ┌─────┴──────┐
│  Pi         │                    │  agent/    │ mic + speakers
│  Chromium   │                    │  agent.py  │ apple_music.py
└─────────────┘                    └────────────┘
```

## 1. Server (your PC or cloud later)

```powershell
cd C:\Users\Anima\Desktop\cassie\server
copy config.example.env .env
# Edit .env — set OPENROUTER_API_KEY, PASSPHRASE, CASSIE_DEVICE_TOKEN

python -m venv venv
.\venv\Scripts\pip install -r requirements.txt
.\venv\Scripts\python main.py
```

Open on laptop: http://localhost:8780/?device=pi-home&token=change-me

Console test: `cassieTest("146 easy street")` then `cassieTest("Cassie what time is it")`

## 2. Pi agent (mic + TTS + Apple Music helper)

```bash
export CASSIE_SERVER=http://YOUR_PC_IP:8780
export CASSIE_DEVICE_TOKEN=change-me
/opt/cassie/venv/bin/python3 /opt/cassie/agent/agent.py
```

## 3. Pi kiosk (browser = website only)

```bash
chromium-browser --kiosk \
  "http://YOUR_PC_IP:8780/?device=pi-home&token=change-me"
```

## Apple Music

See [docs/APPLE_MUSIC.md](APPLE_MUSIC.md). Summary: **web player + login**, not native Python playback.

## Firebase (later)

- Host `web/` on Firebase Hosting
- Move `server/` to Cloud Run (WebSocket + secrets)
- Pi kiosk → `https://your-project.web.app?device=pi-home&token=...`
