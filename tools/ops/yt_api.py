"""Minimal YouTube Data / Analytics client for GitHub Actions (stdlib only).

Auth: refresh-token flow with secrets YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN.
Never prints tokens. Used by ops workflows (secrets_check, daily_ops, analytics).

CLI:
  python tools/ops/yt_api.py check      # channel identity + 7-day views, exit 1 on failure
"""
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


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "check":
        check()
    else:
        raise SystemExit(f"unknown command {cmd}")
