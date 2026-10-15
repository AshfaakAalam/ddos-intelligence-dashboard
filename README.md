# DDoS Intelligence

A FastAPI dashboard for **aggregated Cloudflare Radar Layer 7 DDoS activity**. It includes session-based login, a 3D interactive globe, a complete table of returned country-to-country records, persistent snapshots, and WebSocket updates.

> **Data accuracy:** Cloudflare Radar's endpoint returns aggregated/ranked observations, not individual source IPs or packet-by-packet events. The globe animates the returned aggregate routes between API observations. The default upstream polling interval is five minutes; the dashboard does not fabricate live attack records.

## Requirements
- Python 3.10+
- A Cloudflare API token with permission to read the Radar endpoint
- Internet access in the browser for the Globe.gl and Earth texture CDN assets

## Setup (Linux Mint / Ubuntu)

```bash
cd DDos
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env
```

Set `API_TOKEN` and replace `SESSION_SECRET` with a long random secret. Do not commit `.env`.

Start the server from this directory:

```bash
uvicorn main:app --host 127.0.0.1 --port 8000
```

## Data flow
1. FastAPI polls Cloudflare Radar on startup and then every `POLL_INTERVAL_SECONDS` (default 300; minimum 60).
2. Successful observations are stored in `ddos.db` in the `attack_snapshots` table.
3. A WebSocket broadcasts each new observation to connected, authenticated dashboards.
4. If the upstream API is unavailable, the last saved observation remains available and the dashboard displays a stale/error status.
5. Browser fallback polling is used if the WebSocket cannot connect. It reads the local cache; it does not call Cloudflare directly.

## API endpoints
- `GET /health` — application health check (no API credentials exposed)
- `GET /api/attacks` — latest cached observation and metadata
- `GET /api/attacks?refresh=true` — manually request an upstream refresh
- `WS /ws/attacks` — authenticated live updates




