"""Quick look at a Blender scene: python tools/blender_preview.py blender/<slug> --times 0.5,6,12 --out /tmp/pv [--w 540 --h 960 --samples 12]
Run with the venv python that has bpy (python3 -m venv /tmp/bp && /tmp/bp/bin/pip install bpy). Prints seconds per frame; then view the pngs."""
import argparse, os, runpy, sys, time
import bpy
ap = argparse.ArgumentParser(); ap.add_argument("scene_dir"); ap.add_argument("--times", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--w", type=int, default=540); ap.add_argument("--h", type=int, default=960); ap.add_argument("--samples", type=int, default=12)
a = ap.parse_args()
bpy.ops.wm.read_factory_settings(use_empty=True)
cfg = runpy.run_path(os.path.join(a.scene_dir, "scene.py"))["build"](bpy, os.path.abspath(a.scene_dir))
sc = bpy.context.scene; sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = a.samples; sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = a.w, a.h; os.makedirs(a.out, exist_ok=True)
for t in [float(x) for x in a.times.split(",")]:
    sc.frame_set(int(t * cfg["fps"]) + 1); sc.render.filepath = os.path.join(a.out, f"t{t:05.1f}.png"); t0 = time.time()
    bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(sc.render.filepath); px = list(im.pixels); n = len(px)//4
    lum = sum(0.2126*px[i*4] + 0.7152*px[i*4+1] + 0.0722*px[i*4+2] for i in range(0, n, 37)) / len(range(0, n, 37))
    flag = "  <-- WARNING: too dark/black" if lum < 0.06 else ("  <-- WARNING: blown out" if lum > 0.85 else "")
    print(f"t={t}s {time.time()-t0:.1f}s/frame mean_luma={lum:.2f}{flag}", flush=True)
