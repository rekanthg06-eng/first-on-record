"""Offline test of the ops helper with canned API answers: python tools/ops/test_ops.py"""
import csv, datetime as dt, json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yt_api as y

now = dt.datetime.now(dt.timezone.utc)
iso = lambda d: d.isoformat(timespec="seconds").replace("+00:00", "Z")
VID = [
    {"id": "ok1", "snippet": {"title": "fine"}, "status": {"uploadStatus": "processed", "privacyStatus": "public"}, "statistics": {"viewCount": "9"}, "contentDetails": {"duration": "PT30S"}},
    {"id": "late", "snippet": {"title": "late"}, "status": {"uploadStatus": "processed", "privacyStatus": "private", "publishAt": iso(now - dt.timedelta(hours=2))}, "contentDetails": {}},
    {"id": "soon", "snippet": {"title": "soon"}, "status": {"uploadStatus": "processed", "privacyStatus": "private", "publishAt": iso(now + dt.timedelta(hours=5))}, "contentDetails": {}},
    {"id": "rej", "snippet": {"title": "rej"}, "status": {"uploadStatus": "rejected", "rejectionReason": "copyright", "privacyStatus": "private"}, "contentDetails": {}},
]
sent = []


def fake_get(url, params, tok):
    end = url.rsplit("/", 1)[-1]
    if end == "channels":
        return {"items": [{"id": "UCx", "contentDetails": {"relatedPlaylists": {"uploads": "UUx"}}}]}
    if end == "playlistItems":
        return {"items": [{"contentDetails": {"videoId": v["id"]}} for v in VID]}
    if end == "videos":
        return {"items": VID}
    if end == "commentThreads":
        mk = lambda i, t: {"snippet": {"totalReplyCount": 0, "topLevelComment": {"id": i, "snippet": {"videoId": "ok1", "authorDisplayName": "a", "publishedAt": t, "textDisplay": "is this\nreal?"}}}}
        return {"items": [mk("c2", "2026-11-12T10:00:00Z"), mk("c1", "2026-11-10T10:00:00Z")]}
    if end == "reports":
        if params.get("dimensions") == "video":
            return {"columnHeaders": [{"name": n} for n in ["video", "views", "averageViewPercentage"]], "rows": [["ok1", 9, 55.5]]}
        if params.get("dimensions") == "elapsedVideoTimeRatio":
            return {"rows": [[0.01, 1.2], [0.5, 0.6]]}
        return {"rows": [["YT_SEARCH", 7], ["SHORTS", 2]]}
    raise AssertionError(url)


y.get, y.access_token = fake_get, lambda: "tok"
y.send = lambda m, u, p, b, t: sent.append((m, u.rsplit("/", 1)[-1], b)) or {}
d = tempfile.mkdtemp()
with open(os.path.join(d, "production.csv"), "w") as f:
    f.write("slug,status,video_id\na,PUBLISHED,ok1\nb,PUBLISHED,gone\nc,HELD,x\n")
with open(os.path.join(d, "comments_inbox.csv"), "w") as f:
    f.write("comment_id,video_id,author,published,text,replies\nc1,ok1,a,2026-11-10T10:00:00Z,old,0\n")
y.daily(d)
alerts = open(os.path.join(d, "alerts_latest.txt")).read().splitlines()
assert len(alerts) == 3 and any("late" in a for a in alerts) and any("rej" in a for a in alerts) and any("gone" in a for a in alerts), alerts
assert not any("soon" in a for a in alerts)
inbox = list(csv.DictReader(open(os.path.join(d, "comments_inbox.csv"))))
assert [r["comment_id"] for r in inbox] == ["c1", "c2"], inbox
an = json.load(open(os.path.join(d, "analytics_latest.json")))["analytics"]["ok1"]
assert an["views"] == 9 and an["traffic"]["YT_SEARCH"] == 7 and an["retention"][1] == [0.5, 0.6]
with open(os.path.join(d, "replies_queue.csv"), "w") as f:
    f.write("comment_id,video_id,reply,status,posted_at\nc2,ok1,Yes: Met 1988.433.1,ready,\nc9,ok1,no,skip,\n")
y.replies(d, True)
assert not sent
y.replies(d, False)
assert len(sent) == 1 and sent[0][2]["snippet"]["parentId"] == "c2"
q = list(csv.DictReader(open(os.path.join(d, "replies_queue.csv"))))
assert q[0]["status"] == "posted" and q[1]["status"] == "skip"
y.replies(d, False)
assert len(sent) == 1, "a posted reply must never be sent twice"
y.veto("ok1")
assert sent[-1][0] == "PUT" and sent[-1][2]["status"]["privacyStatus"] == "private"
print("ALL OPS TESTS PASSED")
