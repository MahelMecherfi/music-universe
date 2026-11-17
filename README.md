# Music Universe

An interactive constellation of your Last.fm listening history. Artists become animated, rotating vinyl planets with album artwork; planet sizes reflect recent listens. The frontend displays up to 200 recent scrobbles and includes every artist in those results. Built with a static HTML/Canvas frontend, Flask backend, a 90-second server-side cache, and Docker Compose.

## Start

1. Install and start Docker Desktop.
2. Copy `.env.example` to `.env`.
3. Edit `.env` with your **Last.fm username** and **API key** from https://www.last.fm/api/account/create . **Never commit `.env`**.
4. In this folder, run `docker compose up -d --build`.
5. Open http://localhost:8081 .
6. Stop with `docker compose down`.

For a quick API check: http://localhost:8081/api/health and http://localhost:8081/api/tracks .

If port 8081 is busy, change `8081:80` in `compose.yaml` to `8083:80`, then open http://localhost:8083 .

## Architecture

Browser → nginx `site` → `/api/*` proxy → Flask `api` → Last.fm API. The API key is read only inside Flask from `.env`; the browser never calls Last.fm directly. Album artwork is fetched through a host-restricted Flask proxy. A lock-protected in-memory cache with a 90-second TTL reduces Last.fm requests, and cached data is displayed if Last.fm temporarily fails. The cache resets after a server restart; it is adequate for a single API worker for a course demo.

## Limitations

Uses the most recent 200 items, not full listening history. Last.fm now-playing items may be counted as provisional. If album artwork is missing or unavailable, the supplied local star-chart image is used instead. Artwork URLs are refreshed on each page load so failed covers are retried.
