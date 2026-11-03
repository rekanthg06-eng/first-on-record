#!/usr/bin/env python3
"""One command on your laptop: Google login -> refresh token -> all 5 GitHub secrets set (nothing printed, nothing saved).

  pip install google-auth-oauthlib
  gh auth login            # once, if the GitHub CLI is not logged in (https://cli.github.com)
  python tools/setup_secrets.py client_secret.json

You will be asked to paste (hidden input) your Gemini API key and the private-for-learning token.
"""
import getpass
import json
import subprocess
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

REPO = "rekanthg06-eng/first-on-record"
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


def set_secret(name: str, value: str):
    r = subprocess.run(["gh", "secret", "set", name, "--repo", REPO], input=value, text=True, capture_output=True)
    if r.returncode:
        sys.exit(f"could not set {name}: {r.stderr.strip()} (is `gh auth login` done?)")
    print(f"set {name}")


if len(sys.argv) != 2:
    sys.exit(__doc__)
cfg = json.load(open(sys.argv[1]))
c = cfg.get("installed") or cfg.get("web")
creds = InstalledAppFlow.from_client_config(cfg, SCOPES).run_local_server(port=0, access_type="offline", prompt="consent")
if not creds.refresh_token:
    sys.exit("No refresh token returned: revoke the app at myaccount.google.com/permissions and run again.")
set_secret("YOUTUBE_CLIENT_ID", c["client_id"])
set_secret("YOUTUBE_CLIENT_SECRET", c["client_secret"])
set_secret("YOUTUBE_REFRESH_TOKEN", creds.refresh_token)
for name, prompt in (("GEMINI_API_KEY", "Paste Gemini API key (hidden): "), ("PRIVATE_LEARNING_PAT", "Paste GitHub token for private-for-learning (hidden): ")):
    v = getpass.getpass(prompt).strip()
    if v:
        set_secret(name, v)
    else:
        print(f"skipped {name} (add it later in repo Settings -> Secrets)")
print("Done.")
