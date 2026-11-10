"""Instrumental music bed with ACE-Step (Apache 2.0 weights, outputs usable commercially), CPU only, for GitHub Actions.
python tools/music/acestep_gen.py --prompt "..." --seconds 40 --out bed.wav [--steps 27] [--seed 7]"""
import argparse, time
ap = argparse.ArgumentParser(); ap.add_argument("--prompt", required=True); ap.add_argument("--seconds", type=float, default=40)
ap.add_argument("--out", required=True); ap.add_argument("--steps", type=int, default=27); ap.add_argument("--seed", type=int, default=7)
a = ap.parse_args()
import torch
from acestep.pipeline_ace_step import ACEStepPipeline
t0 = time.time()
p = ACEStepPipeline(device_id=0, dtype="float32", torch_compile=False, cpu_offload=False)
try: p.device = torch.device("cpu")
except Exception: pass
p(audio_duration=a.seconds, prompt=a.prompt, lyrics="[instrumental]", infer_step=a.steps, guidance_scale=15.0,
  scheduler_type="euler", cfg_type="apg", omega_scale=10.0, manual_seeds=str(a.seed), guidance_interval=0.5,
  guidance_interval_decay=0.0, min_guidance_scale=3.0, use_erg_tag=True, use_erg_lyric=False, use_erg_diffusion=True,
  oss_steps="", guidance_scale_text=0.0, guidance_scale_lyric=0.0, save_path=a.out)
print(f"music done in {time.time()-t0:.0f}s -> {a.out}", flush=True)
