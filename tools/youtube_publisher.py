#!/usr/bin/env python3
"""Module B: direct YouTube publisher + telemetry fetcher (replaces Zapier inside GitHub Actions).

Env (GitHub Secrets): YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN.

  python youtube_publisher.py upload --video f.mp4 --meta meta.json --privacy unlisted --out upload_result.json
  python youtube_publisher.py telemetry --days 14 --out telemetry.json

meta.json: {episode_id, title, description, tags[], institution, catalog_number, sources[>=2], ...}
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import random
import re
import sys
import time

TOKEN_URI = "https://oauth2.googleapis.com/token"
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]
RETRIABLE_STATUS = {500, 502, 503, 504}
MAX_RETRIES = 8
ANALYTICS_METRICS = ["views", "engagedViews", "likes", "comments", "shares", "averageViewDuration",
                     "averageViewPercentage", "subscribersGained", "subscribersLost"]
# Always include these in telemetry even if older than the window.
DEFAULT_EXTRA_IDS = "QBRDq7lKusI,zsKktBtPS3A"


class PublishError(RuntimeError):
    pass


# ---------- auth / clients ----------
def credentials():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    try:
        cid, sec, tok = (os.environ[k] for k in ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"))
    except KeyError as e:
        raise PublishError(f"missing env {e}") from e
    c = Credentials(None, refresh_token=tok, token_uri=TOKEN_URI, client_id=cid, client_secret=sec, scopes=SCOPES)
    c.refresh(Request())
    return c


def youtube(creds=None):
    from googleapiclient.discovery import build
    return build("youtube", "v3", credentials=creds or credentials(), cache_discovery=False)


def analytics(creds=None):
    from googleapiclient.discovery import build
    return build("youtubeAnalytics", "v2", credentials=creds or credentials(), cache_discovery=False)


# ---------- upload ----------
def validate_meta(meta: dict) -> dict:
    """Source gate at the publisher too: institution, catalog number, two sources must be present."""
    for k in ("episode_id", "title", "description", "institution", "catalog_number"):
        if not str(meta.get(k, "")).strip():
            raise PublishError(f"meta missing {k}")
    srcs = [s for s in meta.get("sources", []) if str(s).strip()]
    if len(srcs) < 2:
        raise PublishError("need at least two verified sources")
    desc = meta["description"]
    if meta["institution"].lower() not in desc.lower() or str(meta["catalog_number"]).lower() not in desc.lower():
        raise PublishError("description must name the institution and catalog number")
    title = re.sub(r"[<>]", "", meta["title"]).strip()[:100]
    tags, total = [], 0
    for t in meta.get("tags", []):
        t = re.sub(r"[<>,]", "", str(t)).strip()
        if t and total + len(t) + 1 <= 480:
            tags.append(t); total += len(t) + 1
    return {"title": title, "description": re.sub(r"[<>]", "", desc)[:4900], "tags": tags}


def build_body(meta: dict, privacy: str) -> dict:
    v = validate_meta(meta)
    if privacy not in ("public", "unlisted", "private"):
        raise PublishError(f"bad privacy {privacy}")
    return {
        "snippet": {**v, "categoryId": "27", "defaultLanguage": "en", "defaultAudioLanguage": "en"},
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False, "containsSyntheticMedia": False,
                   "embeddable": True, "license": "youtube", "publicStatsViewable": True},
    }


def _resumable(request, sleep=time.sleep):
    from googleapiclient.errors import HttpError
    response, retries = None, 0
    while response is None:
        try:
            _, response = request.next_chunk()
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS and retries < MAX_RETRIES:
                retries += 1
                sleep(min(60, 2 ** retries) + random.random())
                continue
            raise
        except (ConnectionError, TimeoutError, OSError):
            if retries >= MAX_RETRIES:
                raise
            retries += 1
            sleep(min(60, 2 ** retries) + random.random())
    return response


def upload(video_path: str, meta: dict, privacy: str = "unlisted", yt=None, sleep=time.sleep) -> dict:
    from googleapiclient.http import MediaFileUpload
    if not os.path.isfile(video_path):
        raise PublishError(f"no such file {video_path}")
    body = build_body(meta, privacy)
    yt = yt or youtube()
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(video_path, mimetype="video/mp4", chunksize=1024 * 1024, resumable=True))
    r = _resumable(req, sleep)
    out = {
        "episode_id": meta["episode_id"], "video_id": r["id"],
        "published_at": r.get("snippet", {}).get("publishedAt") or dt.datetime.now(dt.timezone.utc).isoformat(),
        "privacy_status": r.get("status", {}).get("privacyStatus", "unknown"),
        "requested_privacy": privacy,
    }
    if out["privacy_status"] != privacy:
        out["warning"] = "YouTube applied a different privacy status than requested"
    return out


# ---------- telemetry ----------
def _clean(s: str, n: int = 500) -> str:
    return re.sub(r"\s+", " ", s or "").strip()[:n]


def fetch_channel_telemetry(days: int = 14, extra_ids: str | None = None, yt=None, yta=None, today: dt.date | None = None) -> dict:
    from googleapiclient.errors import HttpError
    yt = yt or youtube()
    today = today or dt.datetime.now(dt.timezone.utc).date()
    cutoff = today - dt.timedelta(days=days)
    ch = yt.channels().list(part="id,contentDetails", mine=True).execute()["items"][0]
    channel_id = ch["id"]
    uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    ids, page = [], None
    while True:
        r = yt.playlistItems().list(part="contentDetails", playlistId=uploads, maxResults=50, pageToken=page).execute()
        for it in r.get("items", []):
            ids.append(it["contentDetails"]["videoId"])
        page = r.get("nextPageToken")
        if not page or len(ids) >= 200:
            break
    extra = [x for x in (extra_ids if extra_ids is not None else os.environ.get("EXTRA_VIDEO_IDS", DEFAULT_EXTRA_IDS)).split(",") if x.strip()]
    videos = {}
    for i in range(0, len(set(ids + extra)), 50):
        chunk = list(dict.fromkeys(ids + extra))[i:i + 50]
        for v in yt.videos().list(part="snippet,statistics,contentDetails,status", id=",".join(chunk)).execute().get("items", []):
            pub = v["snippet"]["publishedAt"][:10]
            if v["id"] in extra or dt.date.fromisoformat(pub) >= cutoff:
                st = v.get("statistics", {})
                videos[v["id"]] = {
                    "video_id": v["id"], "title": v["snippet"]["title"], "published_at": v["snippet"]["publishedAt"],
                    "duration": v["contentDetails"].get("duration", ""), "privacy_status": v["status"]["privacyStatus"],
                    "views_data_api": int(st.get("viewCount", 0)), "likes_data_api": int(st.get("likeCount", 0)),
                    "comment_count": int(st.get("commentCount", 0)),
                }
    metrics_by_video: dict = {}
    if videos:
        start = min(v["published_at"][:10] for v in videos.values())
        yta = yta or analytics()
        metrics = list(ANALYTICS_METRICS)
        for _ in range(2):
            try:
                res = yta.reports().query(
                    ids="channel==MINE", startDate=start, endDate=today.isoformat(), metrics=",".join(metrics),
                    dimensions="video", filters="video==" + ",".join(videos), sort="-views", maxResults=200).execute()
                names = [h["name"] for h in res.get("columnHeaders", [])]
                for row in res.get("rows", []):
                    d = dict(zip(names, row)); metrics_by_video[d.pop("video")] = d
                break
            except HttpError as e:
                if e.resp.status == 400 and "engagedViews" in metrics:
                    metrics.remove("engagedViews")  # metric not available for this channel; retry without
                    continue
                raise
    for vid, v in videos.items():
        v["analytics"] = metrics_by_video.get(vid, {})  # empty until YouTube processes (2-3 day lag)
    comments, page = [], None
    for _ in range(3):
        r = yt.commentThreads().list(part="snippet", allThreadsRelatedToChannelId=channel_id, maxResults=100,
                                     order="time", textFormat="plainText", pageToken=page).execute()
        stop = False
        for it in r.get("items", []):
            s = it["snippet"]["topLevelComment"]["snippet"]
            if s["publishedAt"][:10] < cutoff.isoformat():
                stop = True; continue
            comments.append({
                "comment_id": it["snippet"]["topLevelComment"]["id"], "video_id": s.get("videoId") or it["snippet"].get("videoId", ""),
                "author": _clean(s.get("authorDisplayName", ""), 80),
                "author_channel_id": (s.get("authorChannelId") or {}).get("value", ""),
                "text": _clean(s.get("textDisplay", "")), "like_count": int(s.get("likeCount", 0)), "published_at": s["publishedAt"],
            })
        page = r.get("nextPageToken")
        if stop or not page:
            break
    return {"fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(), "channel_id": channel_id,
            "videos": list(videos.values()), "comments": comments}


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("upload"); u.add_argument("--video", required=True); u.add_argument("--meta", required=True)
    u.add_argument("--privacy", default="unlisted"); u.add_argument("--out", default="upload_result.json")
    t = sub.add_parser("telemetry"); t.add_argument("--days", type=int, default=14); t.add_argument("--out", default="telemetry.json")
    a = ap.parse_args()
    try:
        if a.cmd == "upload":
            res = upload(a.video, json.load(open(a.meta)), a.privacy)
        else:
            res = fetch_channel_telemetry(a.days)
    except Exception as e:
        print(f"PUBLISHER ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    json.dump(res, open(a.out, "w"), indent=2)
    print(json.dumps(res if a.cmd == "upload" else {"videos": len(res["videos"]), "comments": len(res["comments"])}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
