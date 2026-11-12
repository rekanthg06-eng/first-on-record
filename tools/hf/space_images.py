"""Generate scene stills through a Hugging Face Space (free ZeroGPU) with gradio_client.
Usage: space_images.py scenes/<slug>/<shots.json> out_dir
shots.json: same file the Kaggle lane uses ("style", "shots":[{"id","prompt","seed"}], "variants").
Space: mcp-tools/Qwen-Image-Fast (Qwen-Image, Apache 2.0). HF_TOKEN (optional) raises the ZeroGPU quota."""
import json, os, shutil, sys, time
from gradio_client import Client
job = json.load(open(sys.argv[1])); out = sys.argv[2]; os.makedirs(out, exist_ok=True)
space = job.get("space", "mcp-tools/Qwen-Image-Fast")
tok = os.environ.get("HF_TOKEN") or None
try:
    c = Client(space, token=tok)
except TypeError:
    c = Client(space, hf_token=tok)
print(c.view_api(return_format="str")[:1500])
log = {"space": space, "token": bool(tok), "shots": {}}
nv = int(job.get("variants", 1))
for v in range(nv):
    for s in job["shots"]:
        name = f"{s['id']}_v{v}" if nv > 1 else s["id"]
        prompt = (s["prompt"].strip() + " " + job.get("style", "")).strip()
        seed = int(s.get("seed", 1000)) + v * 77
        for attempt in range(3):
            t = time.time()
            try:
                r = c.predict(prompt=prompt, seed=seed, randomize_seed=False, aspect_ratio=job.get("aspect_ratio", "9:16"),
                              guidance_scale=1, num_inference_steps=8, api_name=job.get("api_name", "/generate_image"))
                img = r[0] if isinstance(r, (list, tuple)) else r
                if isinstance(img, dict): img = img.get("path") or img.get("url")
                ext = os.path.splitext(str(img))[1] or ".png"
                shutil.copy(img, os.path.join(out, name + ext))
                log["shots"][name] = {"ok": True, "sec": round(time.time() - t, 1), "seed": seed}
                break
            except Exception as e:
                log["shots"][name] = {"ok": False, "err": str(e)[:300], "attempt": attempt}
                if "ZeroGPU" in str(e) or "quota" in str(e).lower():
                    log["stopped"] = "quota"; break
                time.sleep(20)
        print(name, log["shots"][name], flush=True)
        json.dump(log, open(os.path.join(out, "hf_log.json"), "w"), indent=1)
        if log.get("stopped"): break
    if log.get("stopped"): print("STOPPED: GPU quota exhausted"); break

# depth maps for 2.5D parallax (Depth Anything V2 Small, Apache 2.0), CPU
try:
    from transformers import pipeline as tpipe
    from PIL import Image
    dp = tpipe("depth-estimation", model="depth-anything/Depth-Anything-V2-Small-hf", device=-1)
    for f in sorted(os.listdir(out)):
        if f.rsplit(".", 1)[-1].lower() in ("png", "webp", "jpg", "jpeg") and "_depth" not in f:
            im = Image.open(os.path.join(out, f)).convert("RGB")
            stem = f.rsplit(".", 1)[0]
            im.save(os.path.join(out, stem + ".png"))
            dp(im)["depth"].save(os.path.join(out, stem + "_depth.png"))
            if not f.endswith(".png"): os.remove(os.path.join(out, f))
    log["depth"] = True
except Exception as e:
    log["depth"] = str(e)[:300]; print("depth failed", e)
json.dump(log, open(os.path.join(out, "hf_log.json"), "w"), indent=1)
