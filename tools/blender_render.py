"""Headless Blender (bpy) shard renderer.  python tools/blender_render.py <scene_dir> --start N --end M --out DIR
<scene_dir>/scene.py must define build(bpy, scene_dir) -> dict(fps, frames, width, height, samples) and set up
objects, lights, camera and keyframes for frames 1..frames. Every shard renders its own frame range to PNG."""
import argparse, os, runpy, sys, time
import bpy

ap = argparse.ArgumentParser()
ap.add_argument("scene_dir"); ap.add_argument("--start", type=int, required=True)
ap.add_argument("--end", type=int, required=True); ap.add_argument("--out", required=True)
a = ap.parse_args()

bpy.ops.wm.read_factory_settings(use_empty=True)
mod = runpy.run_path(os.path.join(a.scene_dir, "scene.py"))
cfg = mod["build"](bpy, os.path.abspath(a.scene_dir))
sc = bpy.context.scene
sc.render.fps = cfg["fps"]; sc.render.resolution_x = cfg["width"]; sc.render.resolution_y = cfg["height"]
sc.render.resolution_percentage = 100
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"
sc.cycles.samples = cfg.get("samples", 32); sc.cycles.use_denoising = True
sc.render.image_settings.file_format = "PNG"
os.makedirs(a.out, exist_ok=True)
t0 = time.time()
for f in range(a.start, min(a.end, cfg["frames"]) + 1):
    sc.frame_set(f)
    sc.render.filepath = os.path.join(a.out, f"f{f:05d}.png")
    bpy.ops.render.render(write_still=True)
    print(f"frame {f} done {time.time()-t0:.0f}s", flush=True)
