# 🛡️ qeme sentinel lite — ai & privacy compliance voor mkb

## 🔐 beveiliging
- **api-token (optioneel):** zet `API_TOKEN` in `.env`. ui stuurt `X-API-Token` mee.
- **cors:** stel `ALLOWED_ORIGINS` in (comma-separated), default `http://localhost:3000`.
- **request-limiet:** `MAX_JSON_SIZE_KB` (default 100 kb).
- **headers:** strikte security headers + csp standaard aan.
- **localhost binding:** compose bindt poorten op `127.0.0.1`.

## 📊 monitoring
- metrics: `http://localhost:3000/metrics`
- prometheus ui: `http://localhost:9090`
- standaard metrics: `sentinel_requests_total`, `sentinel_health_ok`

## 📜 regulatory updates
- endpoint: `GET /api/regulatory-status` (cache) of `GET /api/regulatory-status?refresh=1` (force refresh)
- cli: `make regulatory-check`
- configuratie:
  - `REGULATORY_CACHE_HOURS=24`
  - `REGULATORY_LOG_LEVEL=WARNING` (set `DEBUG` voor detail)
- **let op:** lichte change-detectie (hash + keywords). signaalfunctie, geen juridisch advies.

## ✉️ kritieke update per e-mail (optioneel)
vul in `.env`: `SMTP_HOST, SMTP_PORT, SMTP_FROM, SMTP_TO` (+ evt `SMTP_USER/SMTP_PASS`). bij impact `critical` verstuurt het systeem een korte melding.

## 💾 backup
- script: `scripts/lite_backup.sh`
- run: `make backup` → `backups/data_YYYYMMDD_HHMMSS.tgz`

## 🚀 quickstart
```bash
make setup
make start
# ui: http://localhost:3000   |  prometheus: http://localhost:9090
