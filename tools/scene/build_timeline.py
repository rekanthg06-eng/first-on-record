#!/usr/bin/env python3
"""Builder (runbook v4, agent 14): turn the locked script + the art director's shot plan + the voice word timings
into the compositor's timeline.json. No model needed.

  build_timeline.py <scene_dir> --words words.json --audio voice.m4a --img-dir <dir> [--picks picks.json] [--tail 0.6]

scene_dir holds script.json (lines[{n,text}]) and shots_plan.json (shots[{id,line,type,motion,chip,crop,share}]).
words.json: [{"w","s","e"}] or [{"word","start","end"}] over the whole narration, in script order.
picks.json (optional): {"s01_x": "v1"}: which image variant to use per shot (default v0; file <id>_<pick>.png).
Real-object shots (type real_coin / real_object) use <img-dir>/real_coin.png (a 9:16 plate with the object centred at 40% height).
Cuts land on word starts. Every shot gets a camera move; no two neighbours share the same move.
"""
import argparse, json, os, re

MOVES = {  # zoom [from,to], pan [x0,y0,x1,y1] in image fractions, parallax amplitude
    "push-in":   dict(zoom=[1.06, 1.22], pan=[0, 0, 0, -0.01], par=20),
    "pull-back": dict(zoom=[1.24, 1.08], pan=[0, -0.01, 0, 0], par=18),
    "pan-left":  dict(zoom=[1.14, 1.16], pan=[0.035, 0, -0.035, 0], par=24),
    "pan-right": dict(zoom=[1.14, 1.16], pan=[-0.035, 0, 0.035, 0], par=24),
    "tilt-up":   dict(zoom=[1.14, 1.18], pan=[0, 0.03, 0, -0.03], par=18, par_dir=[0.2, 1]),
    "tilt-down": dict(zoom=[1.14, 1.18], pan=[0, -0.03, 0, 0.03], par=18, par_dir=[0.2, 1]),
}
REAL = {  # crops on the real-object plate (object centred at x 0.5, y 0.40, about 80% of the width); the object stays
    # above the caption band (66% of frame height) and below the chip (12%)
    "whole": dict(zoom=[1.20, 1.08], pan=[0, 0.0, 0, 0.01], par=0),          # slam in close, settle
    "pullback": dict(zoom=[1.45, 1.02], pan=[0, -0.015, 0, 0.018], par=0),
    "lion": dict(zoom=[1.6, 1.75], pan=[-0.10, -0.028, -0.08, -0.03], par=0),
    "bull": dict(zoom=[1.6, 1.75], pan=[0.08, -0.028, 0.10, -0.03], par=0),
    "lion_to_bull": dict(zoom=[1.7, 1.7], pan=[-0.10, -0.03, 0.10, -0.03], par=0),
}


def norm(w):
    return re.sub(r"[^a-z0-9]", "", w.lower())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scene"); ap.add_argument("--words", required=True); ap.add_argument("--audio", required=True)
    ap.add_argument("--img-dir", required=True); ap.add_argument("--picks"); ap.add_argument("--tail", type=float, default=0.6)
    ap.add_argument("--out")
    a = ap.parse_args()
    script = json.load(open(os.path.join(a.scene, "script.json")))
    plan = json.load(open(os.path.join(a.scene, "shots_plan.json")))
    picks = json.load(open(a.picks)) if a.picks else {}
    words = [{"w": w.get("w", w.get("word")), "s": float(w.get("s", w.get("start"))), "e": float(w.get("e", w.get("end")))}
             for w in json.load(open(a.words))]
    # line -> (start, end) by walking the word list
    spans, i = {}, 0
    for ln in script["lines"]:
        toks = [x for x in ln["text"].split() if norm(x)]
        j = i
        for tok in toks:
            t = norm(tok)
            while j < len(words) and norm(words[j]["w"]) != t:
                j += 1
            if j >= len(words):
                raise SystemExit(f"FAIL: could not align line {ln['n']} word '{tok}' to the voice timings")
            words[j]["w"] = tok  # keep the script's spelling and punctuation for the captions
            j += 1
        spans[ln["n"]] = (i, j - 1)
        i = j
    dur = round(words[-1]["e"] + a.tail, 2)
    shots, prev_move = [], None
    by_line = {}
    for s in plan["shots"]:
        by_line.setdefault(s["line"], []).append(s)
    for n in sorted(by_line):
        group = by_line[n]
        w0, w1 = spans[n]
        nxt = words[w1 + 1]["s"] if w1 + 1 < len(words) else dur
        t0, t1 = (0.0 if n == min(by_line) else words[w0]["s"]), nxt
        total = sum(float(s.get("share", 1)) for s in group)
        acc = 0.0
        for k, s in enumerate(group):
            t = t0 + (t1 - t0) * acc / total
            acc += float(s.get("share", 1))
            if k > 0:  # snap an inner cut to the nearest word start inside the line
                cands = [words[x]["s"] for x in range(w0 + 1, w1 + 1)]
                if cands:
                    t = min(cands, key=lambda c: abs(c - t))
            shot = {"t": round(t, 2), "id": s["id"]}
            if s.get("type", "illustration").startswith("real"):
                crop = (s.get("crop") or "whole").lower()
                key = "lion_to_bull" if ("lion" in crop and "bull" in crop) or (("lion" in crop or "bull" in crop) and s.get("motion", "").startswith("pan")) else "pullback" if "pull" in crop else "lion" if "lion" in crop else "bull" if "bull" in crop else "whole"
                shot.update(img="real_coin", **REAL[key])
                if s.get("chip"):
                    shot["chip"] = s["chip"]
            else:
                move = s.get("motion", "push-in")
                if move not in MOVES:
                    move = "push-in"
                if move == prev_move:  # never the same move twice in a row
                    move = {"push-in": "pull-back", "pull-back": "push-in", "pan-left": "pan-right", "pan-right": "pan-left",
                            "tilt-up": "tilt-down", "tilt-down": "tilt-up"}[move]
                prev_move = move
                src = s.get("img_of", s["id"])  # "img_of": reuse another shot's still with a different move/crop
                name = f"{src}_{picks.get(src, 'v0')}"
                if not os.path.exists(os.path.join(a.img_dir, name + ".png")) and os.path.exists(os.path.join(a.img_dir, src + ".png")):
                    name = src  # single-variant runs have no _v0 suffix
                shot.update(img=name, **MOVES[move])
                if s.get("zoom"): shot["zoom"] = s["zoom"]
                if s.get("pan"): shot["pan"] = s["pan"]
            shots.append(shot)
    # drop accidental duplicate cut times and report the pacing
    shots = [s for k, s in enumerate(shots) if k == 0 or s["t"] > shots[k - 1]["t"] + 0.25]
    gaps = [round((shots[k + 1]["t"] if k + 1 < len(shots) else dur) - s["t"], 2) for k, s in enumerate(shots)]
    tl = {"fps": 30, "duration": dur, "caption_y": float(plan.get("caption_y", 0.72)), "audio": os.path.abspath(a.audio), "words": os.path.abspath(a.words) + ".norm.json",
          "img_dir": os.path.abspath(a.img_dir), "shots": shots, "picks": picks}
    json.dump(words, open(tl["words"], "w"))
    out = a.out or os.path.join(a.scene, "timeline.json")
    json.dump(tl, open(out, "w"), indent=1)
    print(f"wrote {out}: {len(shots)} shots, {dur} s, longest hold {max(gaps)} s, shots over 2.5 s: {[shots[k]['id'] for k, g in enumerate(gaps) if g > 2.5]}")


if __name__ == "__main__":
    main()
