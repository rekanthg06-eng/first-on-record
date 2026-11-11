# Runs ON KAGGLE (GPU). Generates illustrated scene stills + depth maps for one Short.
# The workflow kaggle_images.yml replaces JOB_JSON below with the contents of scenes/<slug>/shots.json.
# Models (both Apache 2.0): black-forest-labs/FLUX.2-klein-4B (text-to-image + reference editing), Tongyi-MAI/Z-Image-Turbo.
# Depth: depth-anything/Depth-Anything-V2-Small-hf (Apache 2.0).
import json, os, subprocess, sys, time, traceback
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
    pipe = Flux2KleinPipeline.from_pretrained("black-forest-labs/FLUX.2-klein-4B", torch_dtype=torch.bfloat16)
    steps, guidance = 4, 1.0
else:
    from diffusers import ZImagePipeline
    pipe = ZImagePipeline.from_pretrained("Tongyi-MAI/Z-Image-Turbo", torch_dtype=torch.bfloat16)
    steps, guidance = 9, 0.0
pipe.enable_model_cpu_offload()
done = {}
for s in JOB["shots"]:
    for v in range(int(s.get("variants", JOB.get("variants", 1)))):
        name = f"{s['id']}_v{v}" if int(s.get("variants", JOB.get("variants", 1))) > 1 else s["id"]
        prompt = (s["prompt"].strip() + " " + style).strip()
        seed = int(s.get("seed", 1000)) + v * 77
        kw = dict(prompt=prompt, height=int(s.get("height", H)), width=int(s.get("width", W)),
                  guidance_scale=guidance, num_inference_steps=steps,
                  generator=torch.Generator(device="cpu").manual_seed(seed))
        refs = [done[r] for r in s.get("refs", []) if r in done]
        if refs and model == "klein":
            kw["image"] = refs if len(refs) > 1 else refs[0]
        t = time.time()
        try:
            img = pipe(**kw).images[0]
            img.save(f"{OUT}/{name}.png")
            if v == 0: done[s["id"]] = img
            log["shots"][name] = {"ok": True, "sec": round(time.time() - t, 1), "seed": seed, "refs": s.get("refs", [])}
        except Exception as e:
            traceback.print_exc()
            log["shots"][name] = {"ok": False, "err": str(e)[:300]}
        print(name, log["shots"][name], flush=True)
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
