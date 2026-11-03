import csv, json, os, sys, tempfile, datetime as dt
sys.path.insert(0, os.path.dirname(__file__))
import youtube_publisher as yp
import telemetry_bridge as tb

META = {"episode_id": "20261103-x", "title": "T <b>" + "a" * 120, "description": "Hook.\n\nSources:\n- British Museum, 1953,0411.71\n- B",
        "tags": ["a", "b,c", "d" * 600], "institution": "British Museum", "catalog_number": "1953,0411.71", "sources": ["s1", "s2"]}


def test_body_and_validation():
    b = yp.build_body(META, "unlisted")
    assert len(b["snippet"]["title"]) == 100 and "<" not in b["snippet"]["title"]
    assert b["snippet"]["categoryId"] == "27" and b["status"]["containsSyntheticMedia"] is False
    assert b["status"]["selfDeclaredMadeForKids"] is False and b["snippet"]["tags"] == ["a", "bc"]
    for bad in (dict(META, sources=["one"]), dict(META, catalog_number="ZZZ"), dict(META, title="")):
        try: yp.build_body(bad, "public"); assert False
        except yp.PublishError: pass
    try: yp.build_body(META, "weird"); assert False
    except yp.PublishError: pass


class Resp:  # httplib2-like
    def __init__(s, status): s.status, s.reason = status, "x"


def test_retry_on_5xx():
    from googleapiclient.errors import HttpError
    class Req:
        n = 0
        def next_chunk(self):
            Req.n += 1
            if Req.n < 3: raise HttpError(Resp(503), b"x")
            return None, {"id": "VID"}
    slept = []
    assert yp._resumable(Req(), sleep=slept.append) == {"id": "VID"} and len(slept) == 2
    class Bad:
        def next_chunk(self): raise HttpError(Resp(403), b"x")
    try: yp._resumable(Bad(), sleep=lambda s: None); assert False
    except HttpError: pass


class Exec:
    def __init__(s, v): s.v = v
    def execute(s): return s.v


class FakeYT:
    def channels(s): return type("C", (), {"list": lambda self, **k: Exec({"items": [{"id": "UCx", "contentDetails": {"relatedPlaylists": {"uploads": "UU"}}}]})})()
    def playlistItems(s): return type("P", (), {"list": lambda self, **k: Exec({"items": [{"contentDetails": {"videoId": "A"}}, {"contentDetails": {"videoId": "OLD"}}]})})()
    def videos(s):
        def lst(self, **k):
            mk = lambda i, d: {"id": i, "snippet": {"title": i, "publishedAt": d + "T10:00:00Z"}, "contentDetails": {"duration": "PT32S"},
                               "status": {"privacyStatus": "public"}, "statistics": {"viewCount": "100", "likeCount": "5", "commentCount": "1"}}
            return Exec({"items": [mk("A", "2026-11-02"), mk("OLD", "2026-01-01")]})
        return type("V", (), {"list": lst})()
    def commentThreads(s):
        def lst(self, **k):
            c = lambda i, d: {"snippet": {"topLevelComment": {"id": i, "snippet": {"videoId": "A", "authorDisplayName": "n", "authorChannelId": {"value": "UCa"},
                              "textDisplay": "hi\nthere", "likeCount": 2, "publishedAt": d + "T00:00:00Z"}}}}
            return Exec({"items": [c("c1", "2026-11-02"), c("c2", "2025-01-01")]})
        return type("T", (), {"list": lst})()


class FakeYTA:
    def reports(s):
        return type("R", (), {"query": lambda self, **k: Exec({"columnHeaders": [{"name": n} for n in ["video", "views", "engagedViews", "averageViewPercentage", "subscribersGained"]],
                                                              "rows": [["A", 200, 150, 88.5, 3]]})})()


def test_telemetry_filters_window():
    t = yp.fetch_channel_telemetry(14, extra_ids="", yt=FakeYT(), yta=FakeYTA(), today=dt.date(2026, 11, 3))
    assert [v["video_id"] for v in t["videos"]] == ["A"]  # OLD is outside 14 days
    assert t["videos"][0]["analytics"]["views"] == 200
    assert [c["comment_id"] for c in t["comments"]] == ["c1"] and t["comments"][0]["text"] == "hi there"


def test_bridge_upsert_preserves_and_dedupes():
    d = tempfile.mkdtemp()
    open(os.path.join(d, "results.csv"), "w").write(",".join(tb.BASE_RESULTS) + "\n2026-11-02,A,short,Old title,text,comment,32.6,,,,,,,,paper-atlas; hook 90\n")
    t = yp.fetch_channel_telemetry(14, extra_ids="", yt=FakeYT(), yta=FakeYTA(), today=dt.date(2026, 11, 3))
    up = {"video_id": "N", "episode_id": "e2", "published_at": "2026-11-03T12:00:00Z", "privacy_status": "public"}
    qa = {"passed": False, "overall_score": 6.0, "hook_strength_0_to_3s": 5, "visual_bugs": ["x"], "audio_issues": [], "clamped_overrides": {"pacing_multiplier": 1.2}, "code_patch_instructions": "fix y"}
    for _ in range(2):  # run twice: idempotent
        tb.update_results(d, t, up, {"title": "New", "hook_score": 85, "visual_style": "three"}, qa)
        assert tb.update_comments(d, t) in (1, 0)
    f, rows = tb.read_csv(os.path.join(d, "results.csv"))
    a = next(r for r in rows if r["video_id"] == "A")
    assert a["notes"].startswith("paper-atlas") and a["lever"] == "comment" and a["views"] == "200"
    assert a["swipe_away_rate_est"] == "25.0" and a["viewed_vs_swiped_pct"] == "75.0" and a["subs_per_1k_views"] == "15.0"
    assert len(rows) == 2 and next(r for r in rows if r["video_id"] == "N")["hook_score"] == "85"
    assert tb.log_qa_rejection(d, qa, {"episode_id": "e2"}) and os.path.exists(os.path.join(d, "qa_patch_notes.md"))
    assert not tb.log_qa_rejection(d, {"passed": True}, None)
    tb.ensure_overrides(d); assert json.load(open(os.path.join(d, "showrunner_overrides.json")))["pacing_multiplier"] == 1.0
    assert len(tb.read_csv(os.path.join(d, "comments.csv"))[1]) == 1


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"): f(); print("ok", n)
