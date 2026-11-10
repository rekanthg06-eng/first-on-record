#!/usr/bin/env python3
"""Visual quality gate, stage 1 (numbers). Stage 2 is the independent reviewer (docs/visual_qa_rubric.md).

Catches the "cheap placeholder" look that the luma check in blender_preview.py lets through:
flat untextured surfaces, washed-out low-contrast grade, beige/grey palette, empty frames,
white captions over bright areas, and text running off the frame.

  python3 tools/visual_qa.py frames  <dir with pngs>          [--json out.json]   # preview frames (no captions yet)
  python3 tools/visual_qa.py video   <final.mp4> --out <dir>  [--json out.json]   # samples 8 frames + a contact sheet

Exit 0 = pass, 1 = fail (reasons printed), 2 = error. Thresholds were set 2026-11-10 so that the
Antikythera Short (pWnOfSEXl70, judged "looks like shit" by the user) FAILS on every frame.
"""
import argparse, glob, json, os, subprocess, sys
import numpy as np
from PIL import Image

# ---- thresholds (per frame unless noted); tune only with a logged reason ----
T = dict(
    detail_min=0.022,       # mean |gradient| of luma in the picture area (flat clay/cardboard CG is ~0.01)
    contrast_min=0.42,      # luma p97 - p3 (washed-out grade is ~0.3)
    color_min=22.0,         # Hasler-Suesstrunk colorfulness (beige/grey scene ~12)
    empty_max=0.55,         # share of 24 px blocks that are featureless (flat sky/ground/walls)
    shadow_min=0.03,        # share of pixels darker than 0.12 luma: no shadows at all = no depth
    caption_band_luma_max=0.62,  # mean luma behind the caption band (white text needs a darker bed)
    first_frame_detail_min=0.026,  # the first frame must be the most striking, not an empty box
    fail_share_max=0.25,    # a video fails if more than this share of frames fail any check
)
CAPTION_BAND = (0.72, 0.82)   # caption rows as a share of height (gen_ass places them here)
PICTURE = (0.19, 0.70)        # picture area used for detail/colour (skips header/pills and captions)

def luma(a): return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]

def metrics(path):
    a = np.asarray(Image.open(path).convert("RGB").resize((540, 960)), dtype=np.float32) / 255.0
    h = a.shape[0]; pic = a[int(PICTURE[0]*h):int(PICTURE[1]*h)]; y = luma(pic)
    gx, gy = np.abs(np.diff(y, axis=1)).mean(), np.abs(np.diff(y, axis=0)).mean()
    rg = pic[..., 0] - pic[..., 1]; yb = 0.5 * (pic[..., 0] + pic[..., 1]) - pic[..., 2]
    col = 255 * (np.sqrt(rg.std()**2 + yb.std()**2) + 0.3 * np.sqrt(rg.mean()**2 + yb.mean()**2))
    B = 24; yy = luma(a); hb, wb = yy.shape[0] // B, yy.shape[1] // B
    blocks = yy[:hb*B, :wb*B].reshape(hb, B, wb, B).std(axis=(1, 3))
    gyb = np.abs(np.diff(yy, axis=0))[:hb*B-1]
    band = yy[int(CAPTION_BAND[0]*h):int(CAPTION_BAND[1]*h)]
    # text off the frame: bright, high-contrast pixels touching the left/right 2 px in the caption/source rows
    mx = a.max(axis=2); edge = np.concatenate([mx[:, :6], mx[:, -6:]], axis=1)
    rows = np.concatenate([edge[int(0.03*h):int(0.09*h)], edge[int(CAPTION_BAND[0]*h):int(0.98*h)]])
    return dict(detail=float(gx + gy), contrast=float(np.percentile(y, 97) - np.percentile(y, 3)), color=float(col),
                empty=float((blocks < 0.012).mean()), shadow=float((y < 0.12).mean()),
                caption_band_luma=float(band.mean()), edge_text=float((rows > 0.80).mean()))

def judge(ms, captions):
    out = []
    for i, (name, m) in enumerate(ms):
        r = []
        if m["detail"] < T["detail_min"]: r.append(f"flat/untextured surfaces (detail {m['detail']:.3f} < {T['detail_min']})")
        if m["contrast"] < T["contrast_min"]: r.append(f"washed-out grade (contrast {m['contrast']:.2f} < {T['contrast_min']})")
        if m["color"] < T["color_min"]: r.append(f"dull palette (colorfulness {m['color']:.1f} < {T['color_min']})")
        if m["empty"] > T["empty_max"]: r.append(f"empty frame ({m['empty']:.0%} featureless blocks > {T['empty_max']:.0%})")
        if m["shadow"] < T["shadow_min"]: r.append(f"no deep shadows ({m['shadow']:.1%} < {T['shadow_min']:.0%}): no depth")
        if i == 0 and m["detail"] < T["first_frame_detail_min"]: r.append("first frame is not striking (too little detail)")
        if not captions and m["caption_band_luma"] > T["caption_band_luma_max"]:
            r.append(f"bright area behind the caption band (luma {m['caption_band_luma']:.2f}): white captions will be unreadable")
        if captions and m["edge_text"] > 0.0005: r.append("text touches the frame edge (overflow)")
        out.append((name, m, r))
    bad = sum(1 for _, _, r in out if r)
    ok = bad <= T["fail_share_max"] * len(out) and not out[0][2]
    return ok, out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("mode", choices=["frames", "video"]); ap.add_argument("src")
    ap.add_argument("--out"); ap.add_argument("--json"); a = ap.parse_args()
    if a.mode == "frames":
        files = sorted(glob.glob(os.path.join(a.src, "*.png")))
    else:
        od = a.out or os.path.splitext(a.src)[0] + "_qa"; os.makedirs(od, exist_ok=True)
        dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", a.src]).decode())
        files = []
        for k in range(12):
            t = 0.3 if k == 0 else dur * (k + 0.5) / 12.5; f = os.path.join(od, f"q{k}_{t:05.1f}.png")
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{t:.2f}", "-i", a.src, "-frames:v", "1", f], check=True); files.append(f)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *sum([["-i", f] for f in files], []), "-filter_complex",
                        f"hstack=inputs={len(files)},scale=2160:-1", os.path.join(od, "contact_sheet.png")], check=True)
        print("contact sheet:", os.path.join(od, "contact_sheet.png"))
    if not files: print("no frames"); sys.exit(2)
    ok, res = judge([(os.path.basename(f), metrics(f)) for f in files], captions=(a.mode == "video"))
    for name, m, r in res:
        print(f"{'FAIL' if r else 'ok  '} {name}  " + " ".join(f"{k}={v:.3f}" for k, v in m.items()))
        for x in r: print("      -", x)
    print("VISUAL QA STAGE 1:", "PASS" if ok else "FAIL")
    if a.json: json.dump(dict(passed=ok, thresholds=T, frames=[dict(frame=n, metrics=m, reasons=r) for n, m, r in res]), open(a.json, "w"), indent=1)
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
