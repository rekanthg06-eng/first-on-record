# Runs ON KAGGLE (GPU). Generates illustrated scene stills + depth maps for one Short.
# The workflow kaggle_images.yml replaces JOB_JSON below with the contents of scenes/<slug>/shots.json.
# Models (both Apache 2.0): black-forest-labs/FLUX.2-klein-4B (text-to-image + reference editing), Tongyi-MAI/Z-Image-Turbo.
# Depth: depth-anything/Depth-Anything-V2-Small-hf (Apache 2.0).
import json, os, subprocess, sys, time, traceback
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
JOB = json.loads(r'''__JOB_JSON__''')
OUT = "/kaggle/working"
def sh(c): print("+", c, flush=True); subprocess.run(c, shell=True, check=False)
sh("nvidia-smi --query-gpu=name,memory.total --format=csv")
sh("pip install -q -U git+https://github.com/huggingface/diffusers.git transformers accelerate safetensors sentencepiece protobuf 2>&1 | tail -2")
import torch
from PIL import Image
print("torch", torch.__version__, "cuda", torch.cuda.is_available(), flush=True)
model = JOB.get("model", "klein")
style = JOB.get("style", "")
W, H = JOB.get("width", 864), JOB.get("height", 1536)
log = {"model": model, "shots": {}}
if model == "klein":
    from diffusers import Flux2KleinPipeline
    cls, repo = Flux2KleinPipeline, "black-forest-labs/FLUX.2-klein-4B"
    steps, guidance = 4, 1.0
else:
    from diffusers import ZImagePipeline
    cls, repo = ZImagePipeline, "Tongyi-MAI/Z-Image-Turbo"
    steps, guidance = 9, 0.0
ngpu = torch.cuda.device_count()
print("gpus", ngpu, [torch.cuda.get_device_name(i) for i in range(ngpu)], flush=True)
log["gpus"] = ngpu
# FLUX.2 klein 4B does not fit a 15 GB T4 with whole-model offload or a two-card split (measured 2026-11-11: OOM both ways),
# so use sequential offload: slower per image, but safe on any card. Z-Image-Turbo with whole-model offload ALSO runs out of memory on a T4 (measured 2026-11-12); untested with "offload": "sequential".
pipe = cls.from_pretrained(repo, torch_dtype=torch.bfloat16)
if model == "klein" or JOB.get("offload") == "sequential":
    pipe.enable_sequential_cpu_offload()
else:
    pipe.enable_model_cpu_offload()
try: pipe.vae.enable_tiling()
except Exception as e: print("no vae tiling", e)
done = {}
NV = int(JOB.get("variants", 1))
T0 = time.time()
for v in range(NV):
    for s in JOB["shots"]:
        if v >= int(s.get("variants", NV)): continue
        if time.time() - T0 > float(JOB.get("budget_min", 70)) * 60: print("time budget reached"); break
        name = f"{s['id']}_v{v}" if NV > 1 else s["id"]
        prompt = (s["prompt"].strip() + " " + style).strip()
        seed = int(s.get("seed", 1000)) + v * 77
        kw = dict(prompt=prompt, height=int(s.get("height", H)), width=int(s.get("width", W)),
                  guidance_scale=guidance, num_inference_steps=steps,
                  generator=torch.Generator(device="cpu").manual_seed(seed))
        refs = [done[r] for r in s.get("refs", []) if r in done]
        if refs:  # full-size references run out of memory on a T4 (measured 2026-11-13): shrink them first
            rm = int(JOB.get("ref_max", 640))
            refs = [r.resize((max(16, int(r.width * rm / max(r.size)) // 16 * 16), max(16, int(r.height * rm / max(r.size)) // 16 * 16))) for r in refs]
            torch.cuda.empty_cache()
        if refs and model == "klein":
            kw["image"] = refs if len(refs) > 1 else refs[0]
        t = time.time()
        try:
            img = pipe(**kw).images[0]
            img.save(f"{OUT}/{name}.png")
            if v == 0: done[s["id"]] = img
            log["shots"][name] = {"ok": True, "sec": round(time.time() - t, 1), "seed": seed}
        except Exception as e:
            traceback.print_exc()
            log["shots"][name] = {"ok": False, "err": str(e)[:300]}
            torch.cuda.empty_cache()
        print(name, log["shots"][name], flush=True)
        json.dump(log, open(f"{OUT}/imggen_log.json", "w"), indent=1)
del pipe; torch.cuda.empty_cache()
try:
    from transformers import pipeline as tpipe
    dp = tpipe("depth-estimation", model="depth-anything/Depth-Anything-V2-Small-hf", device=0)
    for f in sorted(os.listdir(OUT)):
        if f.endswith(".png") and not f.endswith("_depth.png"):
            d = dp(Image.open(f"{OUT}/{f}").convert("RGB"))["depth"]
            d.save(f"{OUT}/{f[:-4]}_depth.png")
    log["depth"] = True
except Exception as e:
    traceback.print_exc(); log["depth"] = str(e)[:300]
json.dump(log, open(f"{OUT}/imggen_log.json", "w"), indent=1)
print("DONE", json.dumps(log)[:2000])
