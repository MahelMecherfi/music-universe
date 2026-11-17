# Music Universe

An interactive constellation of your Last.fm listening history. Artists become animated, rotating vinyl planets with album artwork; planet sizes reflect recent listens. The frontend displays up to 200 recent scrobbles and includes every artist in those results. Built with a static HTML/Canvas frontend, Flask backend, a 90-second server-side cache, and Docker Compose.

## Start

1. Install and start Docker Desktop.
2. Copy `.env.example` to `.env` and enter your **Last.fm username** and **API key** from https://www.last.fm/api/account/create . **Never commit `.env`**.
3. In this folder, run `docker compose up --build`.
4. Open http://localhost:8081 .
5. Stop with `docker compose down`.

The app also starts if `.env` has not been created yet; `/api/tracks` will return a clear configuration message until the Last.fm credentials are added.

For a quick API check: http://localhost:8081/api/health and http://localhost:8081/api/tracks .

If port 8081 is busy, change `8081:80` in `compose.yaml` to `8083:80`, then open http://localhost:8083 .

## Public VPS deployment

The public repository is https://github.com/MahelMecherfi/music-universe . On the prepared Ubuntu VPS (`student17.wt.thomasjuldo.com`), clone the repository into a private deployment directory, create `.env` there from `.env.example`, and enter the Last.fm username and API key locally on the server. Keep `.env` out of Git.

Start the public HTTPS deployment from the repository directory:

```sh
docker compose -f compose.yaml -f compose.server.yaml up -d --build
```

Caddy obtains and renews the HTTPS certificate for `student17.wt.thomasjuldo.com`; ports 80 and 443 must be reachable and the DNS record must point to the VPS. Visit https://student17.wt.thomasjuldo.com after startup. For a code update, run `git pull` followed by the same Compose command.

## Architecture

Browser → nginx `site` → `/api/*` proxy → Flask `api` → Last.fm API. The API key is read only inside Flask from `.env`; the browser never calls Last.fm directly. Album artwork is fetched through a host-restricted Flask proxy. A lock-protected in-memory cache with a 90-second TTL reduces Last.fm requests, and cached data is displayed if Last.fm temporarily fails. The cache resets after a server restart; it is adequate for a single API worker for a course demo.

## Limitations

Uses the most recent 200 items, not full listening history. Last.fm now-playing items may be counted as provisional. If album artwork is missing or unavailable, the supplied local star-chart image is used instead. Artwork URLs are refreshed on each page load so failed covers are retried.
