import os
import threading
import time
from datetime import datetime, timezone
from urllib.parse import quote, urlsplit

import requests
from flask import Flask, Response, jsonify, request

app = Flask(__name__)
lock = threading.Lock()
cache = {"expires": 0, "data": None}


def parse_track(track):
    artist = track.get("artist", {})
    album = track.get("album", {})
    images = track.get("image") or []
    if not isinstance(artist, (dict, str)):
        artist = {}
    if not isinstance(album, (dict, str)):
        album = {}
    if not isinstance(images, list):
        images = []
    images = [image for image in images if isinstance(image, dict)]
    image = next((x.get("#text", "") for x in reversed(images) if x.get("#text")), "")
    date = track.get("date") or {}
    if not isinstance(date, dict):
        date = {}
    timestamp = int(date["uts"]) if date.get("uts") is not None else None
    attributes = track.get("@attr") or {}
    now_playing = isinstance(attributes, dict) and attributes.get("nowplaying") == "true"
    return {
        "title": track.get("name", "Unknown track"),
        "artist": artist.get("#text", "") if isinstance(artist, dict) else artist,
        "album": album.get("#text", "") if isinstance(album, dict) else album,
        "cover": f"/api/cover?url={quote(image, safe='')}" if image else "",
        "timestamp": timestamp,
        "now_playing": now_playing,
    }


@app.get("/api/health")
def health():
    return jsonify(status="ok")


@app.get("/api/cover")
def album_cover():
    url = request.args.get("url", "")
    try:
        parsed_url = urlsplit(url)
        port = parsed_url.port
    except ValueError:
        return jsonify(error="Invalid album cover URL."), 400
    if (parsed_url.scheme != "https"
            or parsed_url.hostname not in {"lastfm-img.freetls.fastly.net", "lastfm.freetls.fastly.net"}
            or parsed_url.username or parsed_url.password
            or port not in (None, 443)):
        return jsonify(error="Invalid album cover URL."), 400

    try:
        with requests.get(url, timeout=6, stream=True, allow_redirects=False) as upstream:
            upstream.raise_for_status()
            content_type = upstream.headers.get("Content-Type", "").split(";", 1)[0].lower()
            if content_type not in {"image/jpeg", "image/png", "image/webp", "image/gif"}:
                return jsonify(error="Album cover is unavailable."), 502

            content = bytearray()
            for chunk in upstream.iter_content(chunk_size=64 * 1024):
                content.extend(chunk)
                if len(content) > 5 * 1024 * 1024:
                    return jsonify(error="Album cover is too large."), 502
    except requests.RequestException as exc:
        app.logger.warning("Album cover request failed (%s).", type(exc).__name__)
        return jsonify(error="Album cover is temporarily unavailable."), 502

    return Response(bytes(content), mimetype=content_type,
                    headers={"Cache-Control": "public, max-age=86400"})


@app.get("/api/tracks")
def recent_tracks():
    username = os.getenv("LASTFM_USERNAME", "").strip()
    key = os.getenv("LASTFM_API_KEY", "").strip()
    if not username or not key or username == "your_lastfm_username" or key == "your_api_key_here":
        return jsonify(error="Configure LASTFM_USERNAME and LASTFM_API_KEY in your .env file."), 503

    now = time.monotonic()
    with lock:
        if cache["data"] and now < cache["expires"]:
            return jsonify(**cache["data"], cached=True, stale=False)

        try:
            response = requests.get(
                "https://ws.audioscrobbler.com/2.0/",
                params={"method": "user.getrecenttracks", "user": username,
                        "api_key": key, "format": "json", "limit": 200},
                timeout=9,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("Invalid Last.fm response")
            if "error" in payload:
                raise ValueError(payload.get("message", "Last.fm API error"))
            recent_tracks = payload.get("recenttracks")
            if not isinstance(recent_tracks, dict):
                raise ValueError("Invalid Last.fm recent tracks response")
            raw = recent_tracks.get("track", [])
            if isinstance(raw, dict):
                raw = [raw]
            if not isinstance(raw, list) or any(not isinstance(track, dict) for track in raw):
                raise ValueError("Invalid Last.fm track list")
            tracks = [parse_track(t) for t in raw]
            data = {"username": username, "tracks": tracks,
                    "updated_at": datetime.now(timezone.utc).isoformat()}
            cache.update(expires=time.monotonic() + max(30, int(os.getenv("CACHE_SECONDS", "90"))), data=data)
            return jsonify(**data, cached=False, stale=False)
        except (requests.RequestException, ValueError, TypeError, KeyError) as exc:
            if cache["data"]:
                return jsonify(**cache["data"], cached=True, stale=True,
                               message="Last.fm is temporarily unavailable. Showing recent saved data.")
            app.logger.warning("Last.fm request failed (%s).", type(exc).__name__)
            return jsonify(error="Last.fm is temporarily unavailable. Please try again shortly."), 502
