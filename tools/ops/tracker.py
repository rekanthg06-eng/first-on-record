#!/usr/bin/env python3
"""production.csv tracker: the single source of truth for the weekly studio session (runbook v4).

One row per Short. Every phase calls `set` when it finishes, so a restarted session reads the file and
skips finished work. stdlib only.

  tracker.py <production.csv> init
  tracker.py <production.csv> add <slug> week=2026-W47 route=STORY
  tracker.py <production.csv> set <slug> status=SCRIPT_LOCKED g2a=pass tts_run=123 note="hook 88"
  tracker.py <production.csv> get <slug>            # JSON row
  tracker.py <production.csv> todo [week]           # rows that still need work + the phase to resume at
  tracker.py <production.csv> week-done <week> [n]  # exit 0 when n (default 3) rows are SCHEDULED/PUBLISHED

Rules enforced: status only moves forward (or to HELD/CUT); video_id and external run ids are never
overwritten with a different value (no double upload, no double dispatch) unless force=1 is passed.
"""
import csv, datetime as dt, json, os, sys

ORDER = ["SLATED", "GREENLIT", "SCRIPT_LOCKED", "VOICED", "IMAGES_DISPATCHED", "IMAGES_PASSED",
         "PREVIEW_LOCKED", "RENDERED", "FINAL_PASS", "PACKAGED", "SCHEDULED", "PUBLISHED"]
SIDE = ["HELD", "CUT"]
RESUME = {"SLATED": "S2 greenlight", "GREENLIT": "S3 research/fact-check/write", "SCRIPT_LOCKED": "S3 voice (check tts_run first)",
          "VOICED": "S4 shot list + image dispatch", "IMAGES_DISPATCHED": "S5 wait for images (check img_run), defect screen",
          "IMAGES_PASSED": "S5 build timeline + preview QA", "PREVIEW_LOCKED": "S6 full render + technical checks",
          "RENDERED": "S6 final visual QA", "FINAL_PASS": "S7 package + licence check", "PACKAGED": "S7 upload (check video_id first)"}
GATES = ["g1", "g2a", "g2b", "g2c", "g3a", "g3b", "g3c", "g4", "g5"]
ONCE = ["video_id", "tts_run", "img_run", "render_run"]
COLS = ["slug", "week", "route", "status"] + GATES + ONCE + ["publish_at", "escalations", "note", "updated"]


def load(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return [{c: r.get(c, "") or "" for c in COLS} for r in csv.DictReader(f)]


def save(path, rows):
    tmp = path + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, path)


def find(rows, slug):
    for r in rows:
        if r["slug"] == slug:
            return r
    raise SystemExit(f"FAIL: no row for slug {slug}")


def apply(row, kv):
    force = kv.pop("force", "") == "1"
    for k, v in kv.items():
        if k == "note":
            row["note"] = (row["note"] + " | " if row["note"] else "") + v
            continue
        if k not in COLS or k in ("slug", "updated"):
            raise SystemExit(f"FAIL: unknown column {k}")
        if k == "status":
            if v not in ORDER + SIDE:
                raise SystemExit(f"FAIL: unknown status {v}")
            cur = row["status"]
            if cur in SIDE and not force:
                raise SystemExit(f"FAIL: {row['slug']} is {cur}; pass force=1 to reopen")
            if v in ORDER and cur in ORDER and ORDER.index(v) < ORDER.index(cur) and not force:
                raise SystemExit(f"FAIL: status would move back {cur} -> {v}; pass force=1")
        if k in GATES and v not in ("pass", "fail", ""):
            raise SystemExit(f"FAIL: gate {k} must be pass or fail")
        if k in ONCE and row[k] and row[k] != v and not force:
            raise SystemExit(f"FAIL: {k} already set to {row[k]} for {row['slug']}; refusing to overwrite (no double dispatch/upload)")
        row[k] = v
    row["updated"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def main(a):
    if len(a) < 2:
        raise SystemExit(__doc__)
    path, cmd, rest = a[0], a[1], a[2:]
    rows = load(path)
    kv = dict(x.split("=", 1) for x in rest if "=" in x)
    pos = [x for x in rest if "=" not in x]
    if cmd == "init":
        if not os.path.exists(path):
            save(path, [])
        print("ok", path)
    elif cmd == "add":
        if any(r["slug"] == pos[0] for r in rows):
            print("exists", pos[0])  # idempotent
            return
        row = {c: "" for c in COLS}
        row["slug"], row["status"] = pos[0], "SLATED"
        apply(row, kv)
        rows.append(row)
        save(path, rows)
        print("added", pos[0])
    elif cmd == "set":
        apply(find(rows, pos[0]), kv)
        save(path, rows)
        print("ok", pos[0], find(rows, pos[0])["status"])
    elif cmd == "get":
        print(json.dumps(find(rows, pos[0]), indent=1))
    elif cmd == "todo":
        for r in rows:
            if (not pos or r["week"] == pos[0]) and r["status"] in RESUME:
                print(f"{r['slug']}\t{r['status']}\t-> {RESUME[r['status']]}")
    elif cmd == "week-done":
        need = int(pos[1]) if len(pos) > 1 else 3
        done = [r for r in rows if r["week"] == pos[0] and r["status"] in ("SCHEDULED", "PUBLISHED")]
        print(f"{len(done)}/{need} scheduled for {pos[0]}")
        sys.exit(0 if len(done) >= need else 1)
    else:
        raise SystemExit(f"unknown command {cmd}")


if __name__ == "__main__":
    main(sys.argv[1:])
