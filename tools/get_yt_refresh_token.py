#!/usr/bin/env python3
"""One-time local helper: mint the YouTube OAuth refresh token for the channel's Google account.

  pip install google-auth-oauthlib
  python get_yt_refresh_token.py client_secret.json      # OAuth client of type "Desktop app"

A browser opens: sign in with the Google account that OWNS the channel (the secondary Gmail) and, if asked,
pick the First on Record channel. Copy the printed values into GitHub Secrets. Never commit them.
IMPORTANT: set the OAuth consent screen to "In production" first; in "Testing" mode refresh tokens expire in 7 days.
"""
import json
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]

if len(sys.argv) != 2:
    sys.exit(__doc__)
cfg = json.load(open(sys.argv[1]))
flow = InstalledAppFlow.from_client_config(cfg, SCOPES)
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
if not creds.refresh_token:
    sys.exit("No refresh token returned: revoke the app at myaccount.google.com/permissions and run again.")
c = cfg.get("installed") or cfg.get("web")
print("\nAdd these as GitHub Actions secrets in rekanthg06-eng/first-on-record:")
print("YOUTUBE_CLIENT_ID     =", c["client_id"])
print("YOUTUBE_CLIENT_SECRET =", c["client_secret"])
print("YOUTUBE_REFRESH_TOKEN =", creds.refresh_token)
