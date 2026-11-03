#!/usr/bin/env python3
"""Word timings straight from Kokoro's own phoneme durations: no Whisper, no HuggingFace.

Drop-in replacement for faceless-shorts `words.py` (same output: data/words.json [{w,line,s,e}] + data/words.txt).
Run it AFTER voice.py, with the faceless-shorts venv python:

    ~/.faceless-shorts/venv/bin/python tools/kokoro_words.py <project>

How: the public kokoro-v1.0.onnx model computes a duration per phoneme internally but does not export it. We add that
tensor (`/encoder/Round_output_0`) as an extra graph output (cached as kokoro-v1.0-dur.onnx next to the original);
kokoro-onnx >= 0.6 then reports per-phoneme timings through `create_timed`. Each sentence is re-synthesized exactly the
way voice.py does it (same text, voice, speed), so the timings match data/narration.wav. The audio is identical to the
unpatched model (checked by --selfcheck).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

SR = 24000
HOME = Path(os.environ.get("FACELESS_HOME", Path.home() / ".faceless-shorts"))
KDIR = HOME / "kokoro"
DUR_NODE = "/encoder/Round_output_0"
MARKS = set(",.;:!?…—-\"'()")
norm = lambda w: re.sub(r"[^a-z0-9]+", "", w.lower())


def patched_model() -> Path:
    src, dst = KDIR / "kokoro-v1.0.onnx", KDIR / "kokoro-v1.0-dur.onnx"
    if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
        return dst
    try:
        import onnx
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "onnx"], check=True)
        import onnx
    from onnx import TensorProto, helper
    m = onnx.load(str(src))
    if not any(DUR_NODE in n.output for n in m.graph.node):
        raise SystemExit(f"duration tensor {DUR_NODE} not found: this Kokoro model build differs; use words.py")
    m.graph.node.append(helper.make_node("Identity", [DUR_NODE], ["duration"]))
    m.graph.output.append(helper.make_tensor_value_info("duration", TensorProto.FLOAT, None))
    onnx.save(m, str(dst))
    return dst


def load_kokoro():
    import onnxruntime as ort
    from kokoro_onnx import Kokoro
    sess = ort.InferenceSession(str(patched_model()), providers=["CPUExecutionProvider"])
    k = Kokoro.from_session(sess, str(KDIR / "voices-v1.0.bin"))
    if not k.has_timings:
        raise SystemExit("installed kokoro-onnx has no timing support (need >= 0.6): pip install -U kokoro-onnx")
    return k


def head_trim_seconds(x: np.ndarray, thr: float = 0.008) -> float:
    """Mirror of voice.py trim(): seconds cut from the start of the sentence audio."""
    idx = np.where(np.abs(x) > thr)[0]
    return 0.0 if not len(idx) else max(0, idx[0] - int(0.01 * SR)) / SR


def phoneme_words(timings) -> list[tuple[float, float, int]]:
    """[(start, end, n_letters)] per space-separated phoneme word; punctuation marks do not extend a word."""
    words, cur = [], []
    for t in list(timings) + [None]:
        if t is None or t.phoneme == " ":
            core = [c for c in cur if c.phoneme not in MARKS]
            if core:
                words.append((core[0].start, core[-1].end, len(core)))
            cur = []
        else:
            cur.append(t)
    return words


def map_words(script_words: list[str], pw: list[tuple[float, float, int]]) -> list[tuple[float, float]]:
    """script word -> (start, end). Equal counts map 1:1; otherwise by cumulative size along the phoneme timeline."""
    if len(script_words) == len(pw):
        return [(s, e) for s, e, _ in pw]
    sizes = np.array([max(1, len(norm(w))) for w in script_words], dtype=float)
    cum = np.concatenate([[0], np.cumsum(sizes)]) / sizes.sum()
    psz = np.array([n for *_, n in pw], dtype=float)
    pcum = np.concatenate([[0], np.cumsum(psz)]) / psz.sum()
    starts, ends = np.array([p[0] for p in pw]), np.array([p[1] for p in pw])

    def at(frac: float, edge: str) -> float:
        j = min(len(pw) - 1, int(np.searchsorted(pcum, frac, side="right") - 1))
        j = max(0, j)
        span = pcum[j + 1] - pcum[j] or 1.0
        local = min(1.0, max(0.0, (frac - pcum[j]) / span))
        return float(starts[j] + local * (ends[j] - starts[j]))

    out = []
    for i in range(len(script_words)):
        s, e = at(cum[i], "s"), at(cum[i + 1] - 1e-9, "e")
        out.append((s, max(e, s + 0.04)))
    return out


def run(project: Path):
    S = json.loads((project / "script.json").read_text())
    L = json.loads((project / "data/lines.json").read_text())
    voice = L.get("voice") or S.get("voice", "am_michael")
    speed = L.get("speed") or S.get("speed", 1.0)
    lang = "en-gb" if voice.startswith("b") else "en-us"
    k = load_kokoro()
    groups, cur = [], []
    for i, ln in enumerate(S["lines"]):  # identical grouping to voice.py
        cur.append(i)
        if re.search(r'[.?!]["\')]*$', ln["text"].strip()) or ln.get("break") or i == len(S["lines"]) - 1:
            groups.append(cur); cur = []
    words = []
    for g in groups:
        text = " ".join(S["lines"][i]["text"] for i in g)
        # pauses off: with timings available kokoro-onnx would top up pauses, which voice.py's audio does not have
        audio, _, tm = k.create_timed(text, voice, speed, lang, sentence_pause=0.0, clause_pause=0.0)
        x = np.asarray(audio, dtype=np.float64)
        head = head_trim_seconds(x)
        t0 = L["lines"][g[0]]["start"]
        toks = [(w, i) for i in g for w in S["lines"][i]["text"].split() if norm(w)]
        spans = map_words([w for w, _ in toks], phoneme_words(tm))
        for (w, i), (s, e) in zip(toks, spans):
            lo, hi = L["lines"][i]["start"], L["lines"][i]["end"]
            s = min(max(t0 + s - head, lo), hi)
            e = min(max(t0 + e - head, s), hi)
            words.append({"w": w, "line": i, "s": round(s, 3), "e": round(e, 3)})
    (project / "data/words.json").write_text(json.dumps(words, indent=1))
    (project / "data/words.txt").write_text("\n".join(f"{w['s']:7.2f} {w['e']:7.2f}  L{w['line']:<2d} {w['w']}" for w in words))
    print(f"data/words.json: {len(words)} words (Kokoro phoneme durations; no Whisper)")
    return words


def selfcheck(text="Three thousand years ago, a man wrote a letter."):
    import onnxruntime as ort
    from kokoro_onnx import Kokoro
    a = Kokoro(str(KDIR / "kokoro-v1.0.onnx"), str(KDIR / "voices-v1.0.bin")).create(text, "am_michael", 1.0, "en-us")[0]
    b = load_kokoro().create_timed(text, "am_michael", 1.0, "en-us", sentence_pause=0.0, clause_pause=0.0)[0]
    same = a.shape == b.shape and float(np.abs(a - b).max()) < 1e-5
    print("patched model audio identical to original:", same)
    return same


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("project", nargs="?"); ap.add_argument("--selfcheck", action="store_true")
    a = ap.parse_args()
    if a.selfcheck:
        sys.exit(0 if selfcheck() else 1)
    if not a.project:
        ap.error("project folder missing")
    run(Path(a.project))
