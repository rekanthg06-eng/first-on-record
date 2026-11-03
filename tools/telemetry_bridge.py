#!/usr/bin/env python3
"""Module C: write upload results, analytics, comments and QA logs into a checkout of private-for-learning.

  python telemetry_bridge.py --repo-dir private [--telemetry telemetry.json] [--upload upload_result.json]
        [--meta meta.json] [--qa qa_verdict.json] [--no-push]

private-for-learning is the source of truth the scheduled Claude runs read. Optional Google Sheets mirror when
GOOGLE_SPREADSHEET_ID and GOOGLE_SERVICE_ACCOUNT_JSON are set (not exercised by tests).
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import subprocess
import sys

BASE_RESULTS = ["date", "video_id", "format", "title", "topic_type", "lever", "duration_s", "views", "viewed_vs_swiped_pct",
                "avg_pct_viewed", "subs_gained", "subs_per_1k_views", "shares", "comments", "notes"]
EXTRA_RESULTS = ["episode_id", "engaged_views", "avg_view_duration_s", "swipe_away_rate_est", "likes", "subs_lost",
                 "hook_score", "gemini_qa_score", "visual_style", "privacy_status", "metrics_updated"]
COMMENT_COLS = ["comment_id", "video_id", "author_channel_id", "date", "likes", "type", "requested_topic",
                "sarcasm_label", "sarcasm_confidence", "excerpt"]
QA_COLS = ["timestamp", "episode_id", "qa_score", "hook_score_0_to_3s", "visual_bugs", "audio_issues", "clamped_overrides"]
DEFAULT_OVERRIDES = {
    "_doc": "Showrunner knobs read by the scheduled Claude run at the start of every episode. Values are clamped by the reader.",
    "style_weights": {"paper-atlas": 0.5, "three": 0.5},
    "pacing_multiplier": 1.0,
    "hook_rules": [],
    "notes": "",
}


def _iso_duration_s(d: str) -> float | None:
    import re
    m = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?", d or "")
    return None if not m else int(m[1] or 0) * 3600 + int(m[2] or 0) * 60 + float(m[3] or 0)


def read_csv(path: str):
    if not os.path.exists(path):
        return [], []
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        rows = list(r)
        return list(r.fieldnames or []), rows


def write_csv(path: str, fields: list, rows: list):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def _set(row: dict, key: str, val):
    """Only overwrite with real values; never blank out what Claude or a human already wrote."""
    if val is not None and val != "":
        row[key] = val


def upsert_result(rows: list, video_id: str, **vals) -> dict:
    row = next((r for r in rows if r.get("video_id") == video_id), None)
    if row is None:
        row = {"video_id": video_id}
        rows.append(row)
    for k, v in vals.items():
        _set(row, k, v)
    return row


def update_results(repo: str, telemetry: dict | None, upload: dict | None, meta: dict | None, qa: dict | None):
    path = os.path.join(repo, "results.csv")
    fields, rows = read_csv(path)
    fields = fields or list(BASE_RESULTS)
    for c in BASE_RESULTS + EXTRA_RESULTS:
        if c not in fields:
            fields.append(c)
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    if upload:
        vid = upload["video_id"]
        m = meta or {}
        upsert_result(rows, vid, date=upload["published_at"][:10], format="short", title=m.get("title"),
                      topic_type=m.get("topic_type"), lever=m.get("lever"), duration_s=m.get("duration_s"),
                      episode_id=upload.get("episode_id"), hook_score=m.get("hook_score"),
                      visual_style=m.get("visual_style"), privacy_status=upload.get("privacy_status"),
                      gemini_qa_score=(qa or {}).get("overall_score"))
    for v in (telemetry or {}).get("videos", []):
        a = v.get("analytics") or {}
        views = a.get("views", v.get("views_data_api"))
        eng = a.get("engagedViews")
        swipe = round(100 * (1 - eng / views), 1) if (eng is not None and views) else None  # PROXY: not YouTube's viewed-vs-swiped
        subs = a.get("subscribersGained")
        upsert_result(
            rows, v["video_id"], date=v["published_at"][:10], title=v.get("title"),
            duration_s=_iso_duration_s(v.get("duration")), views=views, engaged_views=eng,
            avg_view_duration_s=a.get("averageViewDuration"), avg_pct_viewed=a.get("averageViewPercentage"),
            swipe_away_rate_est=swipe, viewed_vs_swiped_pct=(round(100 - swipe, 1) if swipe is not None else None),
            likes=a.get("likes", v.get("likes_data_api")), shares=a.get("shares"),
            comments=a.get("comments", v.get("comment_count")), subs_gained=subs, subs_lost=a.get("subscribersLost"),
            subs_per_1k_views=(round(1000 * subs / views, 2) if subs is not None and views else None),
            privacy_status=v.get("privacy_status"), metrics_updated=now)
    write_csv(path, fields, rows)
    return rows


def update_comments(repo: str, telemetry: dict | None) -> int:
    path = os.path.join(repo, "comments.csv")
    fields, rows = read_csv(path)
    fields = fields or list(COMMENT_COLS)
    seen = {r["comment_id"] for r in rows}
    n = 0
    for c in (telemetry or {}).get("comments", []):
        if c["comment_id"] in seen:
            continue
        # type/requested_topic/sarcasm columns stay blank: the scheduled Claude run classifies them.
        rows.append({"comment_id": c["comment_id"], "video_id": c["video_id"], "author_channel_id": c["author_channel_id"],
                     "date": c["published_at"][:10], "likes": c["like_count"], "excerpt": c["text"][:300]})
        seen.add(c["comment_id"]); n += 1
    write_csv(path, fields, rows)
    return n


def log_qa_rejection(repo: str, qa: dict | None, meta: dict | None):
    if not qa or qa.get("passed"):
        return False
    path = os.path.join(repo, "qa_rejections.csv")
    fields, rows = read_csv(path)
    fields = fields or list(QA_COLS)
    rows.append({
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "episode_id": (meta or {}).get("episode_id", ""), "qa_score": qa.get("overall_score", ""),
        "hook_score_0_to_3s": qa.get("hook_strength_0_to_3s", ""),
        "visual_bugs": json.dumps(qa.get("visual_bugs", [])) if "error" not in qa else json.dumps([qa["error"]]),
        "audio_issues": json.dumps(qa.get("audio_issues", [])),
        "clamped_overrides": json.dumps(qa.get("clamped_overrides", {})),
    })
    write_csv(path, fields, rows)
    # full patch instructions are kept for the next Claude run
    if qa.get("code_patch_instructions"):
        with open(os.path.join(repo, "qa_patch_notes.md"), "a", encoding="utf-8") as f:
            f.write(f"\n## {rows[-1]['timestamp']} {rows[-1]['episode_id']}\n{qa['code_patch_instructions']}\n")
    return True


def ensure_overrides(repo: str):
    p = os.path.join(repo, "showrunner_overrides.json")
    if not os.path.exists(p):
        json.dump(DEFAULT_OVERRIDES, open(p, "w"), indent=2)


def git(repo: str, *args: str, check=True):
    return subprocess.run(["git", "-C", repo, *args], check=check, capture_output=True, text=True)


def commit_and_push(repo: str, message: str) -> bool:
    git(repo, "add", "-A")
    if not git(repo, "status", "--porcelain").stdout.strip():
        return False
    git(repo, "-c", "user.name=first-on-record-bot", "-c", "user.email=bot@users.noreply.github.com", "commit", "-m", message)
    for _ in range(4):
        if git(repo, "push", "origin", "HEAD", check=False).returncode == 0:
            return True
        git(repo, "pull", "--rebase", "origin", "main", check=False)
    raise RuntimeError("push to private-for-learning failed")


def mirror_sheets(repo: str):
    sid, sa = os.environ.get("GOOGLE_SPREADSHEET_ID"), os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not (sid and sa):
        return False
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    creds = service_account.Credentials.from_service_account_info(json.loads(sa), scopes=["https://www.googleapis.com/auth/spreadsheets"])
    svc = build("sheets", "v4", credentials=creds, cache_discovery=False).spreadsheets()
    for fname, tab in (("results.csv", "Published_Telemetry"), ("qa_rejections.csv", "QA_Rejections")):
        p = os.path.join(repo, fname)
        if not os.path.exists(p):
            continue
        vals = list(csv.reader(open(p, newline="", encoding="utf-8")))
        svc.values().clear(spreadsheetId=sid, range=tab).execute()
        svc.values().update(spreadsheetId=sid, range=f"{tab}!A1", valueInputOption="RAW", body={"values": vals}).execute()
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-dir", required=True)
    for k in ("telemetry", "upload", "meta", "qa"):
        ap.add_argument(f"--{k}")
    ap.add_argument("--no-push", action="store_true")
    a = ap.parse_args()
    load = lambda p: json.load(open(p)) if p and os.path.exists(p) else None
    tel, up, meta, qa = (load(a.telemetry), load(a.upload), load(a.meta), load(a.qa))
    update_results(a.repo_dir, tel, up, meta, qa)
    n = update_comments(a.repo_dir, tel)
    rej = log_qa_rejection(a.repo_dir, qa, meta)
    ensure_overrides(a.repo_dir)
    try:
        sheets = mirror_sheets(a.repo_dir)
    except Exception as e:  # mirror is optional; never fail the run for it
        print(f"sheets mirror skipped: {e}", file=sys.stderr); sheets = False
    pushed = False if a.no_push else commit_and_push(a.repo_dir, "Sync telemetry from GitHub Actions")
    print(json.dumps({"new_comments": n, "qa_rejection_logged": rej, "sheets": sheets, "pushed": pushed}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
