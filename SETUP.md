# Zapier-free publishing: one-time setup

Flow: scheduled Claude run stages `shorts/<id>.mp4` + `shorts/<id>.json` on the `media` branch -> GitHub Action `publish_short` -> Gemini QA gate -> YouTube upload -> telemetry/comments synced into the private `private-for-learning` repo.

## 1. Google Cloud (about 10 minutes, $0)
1. console.cloud.google.com -> new project "first-on-record".
2. APIs & Services -> Library: enable **YouTube Data API v3** and **YouTube Analytics API**.
3. OAuth consent screen: External, add your channel's Google account as a test user, add the 3 scopes (youtube.upload, youtube.readonly, yt-analytics.readonly), then **Publish app -> In production**. (In "Testing" mode the refresh token dies after 7 days. An unverified app is fine for your own account; click through the "unverified" warning.)
4. Credentials -> Create OAuth client ID -> type **Desktop app** -> download JSON as `client_secret.json`.
5. On your laptop: `pip install google-auth-oauthlib` then `python tools/get_yt_refresh_token.py client_secret.json`. Sign in with the account that owns the First on Record channel (pick the channel if asked). It prints three values.

## 2. Gemini key
aistudio.google.com -> Get API key (billing must be enabled: gemini-4-argon has no free tier, roughly 10-15 cents per video). Optional: repo variable `QA_MODEL` to use another model.

## 3. GitHub secrets (first-on-record -> Settings -> Secrets and variables -> Actions)
`GEMINI_API_KEY`, `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`, `PRIVATE_LEARNING_PAT` (fine-grained token, repo `private-for-learning` only, Contents: read and write). Optional: `GOOGLE_SPREADSHEET_ID` + `GOOGLE_SERVICE_ACCOUNT_JSON` for the Sheets mirror (tabs `Published_Telemetry`, `QA_Rejections`).

## 4. Test, then go live
Actions -> publish_short -> Run workflow (privacy `unlisted`). Check the run log, the unlisted video, and new rows in `private-for-learning/results.csv`.
Only after that succeeds: set repository **variable** `LIVE_PUBLISH` = `true`, and switch the daily task from Zapier upload to staging mp4 + json (contract below). Until `LIVE_PUBLISH` is true, push-triggered runs do QA only and never upload.

## Metadata contract: `shorts/<episode_id>.json`
```json
{"episode_id": "20261103-slug", "video_file": "20261103-slug.mp4", "title": "...", "description": "... must name institution and catalog number ...",
 "tags": ["..."], "institution": "British Museum", "catalog_number": "1953,0411.71", "sources": ["url or citation 1", "url or citation 2"],
 "topic_type": "text", "lever": "comment", "hook_score": 90, "visual_style": "paper-atlas", "duration_s": 32.6}
```

## 5. Voice (workflow `tts_voice`, no keys)
Narration runs in Actions with the open-source Chatterbox model (MIT, CPU). No secrets needed. Contract and flow: `tts/README.md`.
