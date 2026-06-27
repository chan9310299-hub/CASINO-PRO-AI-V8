# CASINO PRO AI v9.2 모바일 간소화

Baccarat road analysis and AI record-keeping dashboard. Statistical analysis only — not betting advice.

## Run locally

```bash
pip install -r requirements.txt
python -m streamlit run app/app.py
```

## Mobile / LAN access

```bash
python -m streamlit run app/app.py --server.address 0.0.0.0 --server.port 8501
```

Open the Network URL on your phone (same Wi‑Fi). In Chrome, use **Add to Home screen** for app-like access.

## Optional access code (Streamlit Cloud)

Login is not required by default. To add a simple access-code guard on Streamlit Cloud:

1. Open your app settings → **Secrets**.
2. Add:

```toml
ACCESS_CODE = "your-secret-code"
```

3. Redeploy. Users must enter the code once per session.

If `ACCESS_CODE` is not set, the app runs normally with no gate.

## Streamlit Cloud

1. Push this repo to GitHub.
2. Deploy at [share.streamlit.io](https://share.streamlit.io).
3. Set **Main file path** to `app/app.py`.
4. Python 3.10+ recommended.

**Data safety:** Free cloud tiers may reset the filesystem. Use **Create backup now** / **Download latest DB backup** regularly and download backups to your device.

## Project layout

```
app/           Streamlit app and AI engines
app/storage.py SQLite storage facade (online-DB ready)
data/          SQLite DB (auto-created)
data/backups/  Daily and manual backups
data/exports/  CSV and DB exports
tests/         Unit tests
```

## Tests

```bash
python -m unittest discover -s tests -v
```

## Disclaimer

This software is for pattern analysis and record-keeping only. It does not provide betting advice or guaranteed outcomes.
