"""Minimal YouTube Data / Analytics client for GitHub Actions (stdlib only).

Auth: refresh-token flow with secrets YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN.
Never prints tokens. Used by ops workflows (secrets_check, daily_ops, analytics).

CLI:
  python tools/ops/yt_api.py check                       # channel identity + 28-day views, exit 1 on failure
  python tools/ops/yt_api.py daily <state_dir>           # health + analytics + comments -> files in state_dir; prints ALERT lines
  python tools/ops/yt_api.py replies <state_dir> [--dry-run]   # post rows of replies_queue.csv with status=ready (max 5)
  python tools/ops/yt_api.py veto <video_id>             # set one video private (weekly veto)

Limits (YouTube API): copyright claims and strikes are NOT readable through the API; this detects rejected,
failed, deleted or unexpectedly private uploads only. Claims and strikes reach the owner by YouTube email.
"""
import csv
import datetime as dt
import json
import os
import sys
import urllib.parse
import urllib.request

TOKEN_URL = "https://oauth2.googleapis.com/token"
DATA = "https://www.googleapis.com/youtube/v3"
ANALYTICS = "https://youtubeanalytics.googleapis.com/v2/reports"


def access_token():
    missing = [k for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN") if not os.environ.get(k)]
    if missing:
        raise SystemExit(f"FAIL: missing secrets: {', '.join(missing)}")
    body = urllib.parse.urlencode({
        "client_id": os.environ["YT_CLIENT_ID"],
        "client_secret": os.environ["YT_CLIENT_SECRET"],
        "refresh_token": os.environ["YT_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(TOKEN_URL, data=body), timeout=30) as r:
            return json.load(r)["access_token"]
    except urllib.error.HTTPError as e:
        err = json.loads(e.read() or b"{}")
        raise SystemExit(f"FAIL: token refresh rejected ({e.code} {err.get('error')}: {err.get('error_description')})")


def get(url, params, token):
    q = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{url}?{q}", headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        msg = json.loads(e.read() or b"{}").get("error", {}).get("message", "")
        raise SystemExit(f"FAIL: {url.rsplit('/', 1)[-1]} -> HTTP {e.code} {msg}")


def check():
    tok = access_token()
    print("OK: refresh token works")
    ch = get(f"{DATA}/channels", {"part": "snippet,statistics", "mine": "true"}, tok)
    items = ch.get("items") or []
    if not items:
        raise SystemExit("FAIL: token has no YouTube channel (wrong account/channel chosen at consent?)")
    c = items[0]
    print(f"OK: Data API channel = {c['snippet']['title']} ({c['id']}), "
          f"subs={c['statistics'].get('subscriberCount')}, videos={c['statistics'].get('videoCount')}")
    end = dt.date.today()
    start = end - dt.timedelta(days=28)
    rep = get(ANALYTICS, {"ids": "channel==MINE", "startDate": start.isoformat(), "endDate": end.isoformat(),
                          "metrics": "views,estimatedMinutesWatched,subscribersGained"}, tok)
    row = (rep.get("rows") or [[0, 0, 0]])[0]
    print(f"OK: Analytics API last 28 days views={row[0]} minutes={row[1]} subsGained={row[2]}")
    expected = os.environ.get("EXPECTED_CHANNEL_ID")
    if expected and c["id"] != expected:
        raise SystemExit(f"FAIL: token is for channel {c['id']}, expected {expected}")


def send(method, url, params, body, token):
    q = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{url}?{q}", data=json.dumps(body).encode(), method=method,
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        msg = json.loads(e.read() or b"{}").get("error", {}).get("message", "")
        raise SystemExit(f"FAIL: {method} {url.rsplit('/', 1)[-1]} -> HTTP {e.code} {msg}")


def uploads(tok, n=25):
    ch = get(f"{DATA}/channels", {"part": "contentDetails", "mine": "true"}, tok)["items"][0]
    pl = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    items = get(f"{DATA}/playlistItems", {"part": "contentDetails", "playlistId": pl, "maxResults": n}, tok).get("items", [])
    ids = [i["contentDetails"]["videoId"] for i in items]
    if not ids:
        return []
    return get(f"{DATA}/videos", {"part": "snippet,status,statistics,contentDetails", "id": ",".join(ids)}, tok).get("items", [])


def health(videos, known_ids, now=None):
    """ALERT lines for uploads that are rejected/failed, or public-expected but not public, or missing."""
    now = now or dt.datetime.now(dt.timezone.utc)
    alerts, seen = [], set()
    for v in videos:
        seen.add(v["id"])
        st = v["status"]
        title = v["snippet"]["title"][:60]
        if st.get("uploadStatus") in ("rejected", "failed", "deleted"):
            alerts.append(f"ALERT: {v['id']} '{title}' uploadStatus={st['uploadStatus']} reason={st.get('rejectionReason') or st.get('failureReason')}")
        pub = st.get("publishAt")
        if pub and st.get("privacyStatus") == "private":
            due = dt.datetime.fromisoformat(pub.replace("Z", "+00:00"))
            if now - due > dt.timedelta(minutes=30):
                alerts.append(f"ALERT: {v['id']} '{title}' was due public at {pub} but is still private")
        if v.get("contentDetails", {}).get("regionRestriction", {}).get("blocked"):
            alerts.append(f"ALERT: {v['id']} '{title}' is blocked in some countries")
    for vid in known_ids:
        if vid and vid not in seen:
            alerts.append(f"ALERT: {vid} is in the ledger but no longer in the channel's recent uploads (removed?)")
    return alerts


def analytics(tok, ids, days=28):
    end = dt.date.today()
    start = end - dt.timedelta(days=days)
    base = {"ids": "channel==MINE", "startDate": start.isoformat(), "endDate": end.isoformat()}
    out = {}
    rep = get(ANALYTICS, {**base, "dimensions": "video", "sort": "-views", "maxResults": 50,
                          "metrics": "views,averageViewPercentage,averageViewDuration,subscribersGained,shares,comments,likes"}, tok)
    cols = [h["name"] for h in rep.get("columnHeaders", [])]
    for row in rep.get("rows") or []:
        out[row[0]] = dict(zip(cols[1:], row[1:]))
    for vid in ids:
        d = out.setdefault(vid, {})
        r = get(ANALYTICS, {**base, "dimensions": "elapsedVideoTimeRatio", "metrics": "audienceWatchRatio",
                            "filters": f"video=={vid}"}, tok)
        d["retention"] = [[x[0], round(x[1], 3)] for x in (r.get("rows") or [])]
        r = get(ANALYTICS, {**base, "dimensions": "insightTrafficSourceType", "metrics": "views",
                            "filters": f"video=={vid}", "sort": "-views"}, tok)
        d["traffic"] = {x[0]: x[1] for x in (r.get("rows") or [])}
    return out


def comments(tok, channel_id, since_iso):
    res = get(f"{DATA}/commentThreads", {"part": "snippet", "allThreadsRelatedToChannelId": channel_id,
                                         "maxResults": 100, "order": "time", "textFormat": "plainText"}, tok)
    rows = []
    for t in res.get("items", []):
        s = t["snippet"]["topLevelComment"]["snippet"]
        if s["publishedAt"] <= since_iso:
            continue
        rows.append({"comment_id": t["snippet"]["topLevelComment"]["id"], "video_id": s.get("videoId", ""),
                     "author": s.get("authorDisplayName", ""), "published": s["publishedAt"],
                     "text": s.get("textDisplay", "").replace("\n", " ")[:1000], "replies": t["snippet"].get("totalReplyCount", 0)})
    return rows


def daily(state):
    os.makedirs(state, exist_ok=True)
    tok = access_token()
    vids = uploads(tok)
    known = []
    prod = os.path.join(state, "production.csv")
    if os.path.exists(prod):
        known = [r.get("video_id", "") for r in csv.DictReader(open(prod, encoding="utf-8"))
                 if r.get("status") in ("SCHEDULED", "PUBLISHED")]
    alerts = health(vids, known)
    ids = [v["id"] for v in vids if v["status"].get("privacyStatus") == "public"]
    json.dump({"pulled": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
               "videos": [{"id": v["id"], "title": v["snippet"]["title"], "status": v["status"], "stats": v.get("statistics", {}),
                           "duration": v["contentDetails"].get("duration")} for v in vids],
               "analytics": analytics(tok, ids)}, open(os.path.join(state, "analytics_latest.json"), "w"), indent=1)
    cpath = os.path.join(state, "comments_inbox.csv")
    old = list(csv.DictReader(open(cpath, encoding="utf-8"))) if os.path.exists(cpath) else []
    since = max([r["published"] for r in old], default="1970")
    ch = get(f"{DATA}/channels", {"part": "id", "mine": "true"}, tok)["items"][0]["id"]
    new = comments(tok, ch, since)
    fields = ["comment_id", "video_id", "author", "published", "text", "replies"]
    with open(cpath, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows([{k: r.get(k, "") for k in fields} for r in old + sorted(new, key=lambda r: r["published"])])
    print(f"OK: {len(vids)} uploads checked, {len(ids)} public, {len(new)} new comments")
    for a in alerts:
        print(a)
    open(os.path.join(state, "alerts_latest.txt"), "w").write("\n".join(alerts))


def replies(state, dry):
    """replies_queue.csv columns: comment_id,video_id,reply,status (ready|posted|skip),posted_at"""
    path = os.path.join(state, "replies_queue.csv")
    if not os.path.exists(path):
        print("OK: no replies_queue.csv")
        return
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    todo = [r for r in rows if r.get("status") == "ready" and r.get("reply", "").strip()][:5]
    tok = None if dry and not os.environ.get("YT_REFRESH_TOKEN") else access_token()
    for r in todo:
        if dry:
            print(f"DRY: would reply to {r['comment_id']}: {r['reply'][:80]}")
            continue
        send("POST", f"{DATA}/comments", {"part": "snippet"},
             {"snippet": {"parentId": r["comment_id"], "textOriginal": r["reply"][:9000]}}, tok)
        r["status"], r["posted_at"] = "posted", dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        print(f"OK: replied to {r['comment_id']}")
    if not dry and todo:
        fields = list(rows[0].keys())
        for extra in ("status", "posted_at"):
            if extra not in fields:
                fields.append(extra)
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
    print(f"OK: {len(todo)} replies {'checked' if dry else 'posted'}")


def veto(video_id):
    tok = access_token()
    v = get(f"{DATA}/videos", {"part": "status", "id": video_id}, tok).get("items") or []
    if not v:
        raise SystemExit(f"FAIL: video {video_id} not found")
    st = v[0]["status"]
    body = {"id": video_id, "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": st.get("selfDeclaredMadeForKids", False),
                                       "embeddable": st.get("embeddable", True), "license": st.get("license", "youtube")}}
    send("PUT", f"{DATA}/videos", {"part": "status"}, body, tok)
    print(f"OK: {video_id} set to private (publishAt cleared)")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "check":
        check()
    elif cmd == "daily":
        daily(sys.argv[2])
    elif cmd == "replies":
        replies(sys.argv[2], "--dry-run" in sys.argv)
    elif cmd == "veto":
        veto(sys.argv[2])
    else:
        raise SystemExit(f"unknown command {cmd}")
