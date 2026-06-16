# Cassie — Git deploy (PC → Pi)

No USB needed. Push from Windows, pull on Pi, one command to apply.

## One-time setup

### 1. On your PC (Windows)

Put this repo on GitHub/GitLab (private recommended):

```powershell
cd C:\Users\Anima\Desktop\cassie
git init
git add .
git commit -m "Cassie v1.2.2"
git branch -M main
git remote add origin https://github.com/YOUR_USER/cassie.git
git push -u origin main
```

**Never commit** `config/config.yaml` (API key). Only `config.template.yaml` is in git.

### 2. On the Pi (SSH, one time)

```bash
sudo apt-get install -y git
git clone https://github.com/YOUR_USER/cassie.git /home/cassie/cassie-git
cd /home/cassie/cassie-git
sudo bash install.sh
sudo nano /opt/cassie/config/config.yaml   # paste OpenRouter API key
sudo reboot
```

---

## Every update (normal workflow)

### PC — after you change code in Cursor:

```powershell
cd C:\Users\Anima\Desktop\cassie
git add .
git commit -m "describe your change"
git push
```

### Pi — apply update:

```bash
cd /home/cassie/cassie-git
git pull
sudo bash update.sh
```

Optional reboot if display looks stuck:

```bash
sudo reboot
```

That's it. No USB, no manual `cp` files.

---

## Quick Pi alias (optional)

Add to `~/.bashrc` on Pi:

```bash
alias cassie-update='cd ~/cassie-git && git pull && sudo bash update.sh'
```

Then updates are just: `cassie-update`

---

## Verify

```bash
curl -s http://127.0.0.1:8766/health
journalctl -u cassie -n 15 --no-pager
```

Expected: `"ok": true` and log line `Cassie ready. Listening for wake word...`
