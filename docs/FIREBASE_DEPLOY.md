# Cassie on Firebase (project: hobbifinder)

Your Cassie **orb website** lives on Firebase Hosting. The **brain** (OpenRouter key, voice AI) runs on a server with WebSocket support — not inside static hosting.

## What goes where

| Thing | Where | Secret? |
|-------|--------|---------|
| Orb UI (`web/`) | Firebase Hosting → `hobbifinder.web.app` | No |
| Firebase `apiKey` in web | Client config (public by design) | Public OK |
| OpenRouter API key | `server/.env` or Cloud Run secrets | **Never in web/** |
| Passphrase | `server/.env` | Server only |
| Pi agent | Raspberry Pi | No API key |

## Step 1 — Deploy the website (your PC)

```powershell
cd C:\Users\Anima\Desktop\cassie
npx -y firebase-tools@latest login
npx -y firebase-tools@latest deploy --only hosting
```

Live URLs:
- https://hobbifinder.web.app
- https://hobbifinder.firebaseapp.com

## Step 2 — Run the brain (same PC for now)

```powershell
cd server
copy config.example.env .env
# Edit .env: OPENROUTER_API_KEY, PASSPHRASE=146 easy street, CASSIE_DEVICE_TOKEN=pick-a-secret

python -m venv venv
.\venv\Scripts\pip install -r requirements.txt
.\venv\Scripts\python main.py
```

Brain runs at `http://YOUR_PC_LAN_IP:8780`

## Step 3 — Connect website to brain

### Option A — Easiest at home (Pi + PC, no tunnel)

Pi opens the brain **directly** (HTTP, same LAN — no Firebase needed for WS):

```bash
chromium --kiosk "http://YOUR_PC_IP:8780/?device=pi-home&token=YOUR_TOKEN"
```

Orb UI is served by the Python server from `web/` — works immediately.

### Option B — Firebase site (https://hobbifinder.web.app)

Firebase is **HTTPS**. Browsers block `ws://` from an HTTPS page. Your brain must be **wss://**:

1. **Cloudflare Tunnel** (free): exposes `https://cassie.yourdomain.com` → PC port 8780  
2. **Cloud Run** (later): deploy `server/` to Google Cloud  

Then open:

```
https://hobbifinder.web.app/?server=wss://YOUR_TUNNEL_URL&device=pi-home&token=YOUR_TOKEN
```

After tunnel is set, put that URL in `web/js/cassie-config.js` → `brainServer` and redeploy hosting.

## Step 4 — Pi agent

```bash
export CASSIE_SERVER=ws://192.168.7.164:8780
export CASSIE_DEVICE_TOKEN=YOUR_TOKEN
/opt/cassie/venv/bin/python3 /opt/cassie/agent/agent.py
```

## Later: brain on Cloud Run (public HTTPS/WSS)

Then set in `web/js/cassie-config.js`:

```javascript
brainServer: "wss://cassie-brain-xxxxx.run.app"
```

And add to `firebase.json`:

```json
{ "source": "/ws", "run": { "serviceId": "cassie-brain", "region": "us-central1" } }
```

## Security notes

- Do **not** put OpenRouter key in Firebase web files or Realtime Database rules without auth.
- Change `CASSIE_DEVICE_TOKEN` from `change-me` before going live.
- Firebase client `apiKey` is not a secret — restrict with Firebase App Check / rules later.
