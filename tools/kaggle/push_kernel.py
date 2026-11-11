"""Build a Kaggle script-kernel folder for the image job. Usage: push_kernel.py scenes/<slug>/shots.json kernel_dir"""
import json, os, sys
from kaggle.api.kaggle_api_extended import KaggleApi
job_path, out = sys.argv[1], sys.argv[2]
job = json.load(open(job_path))
api = KaggleApi(); api.authenticate()
user = None
for getter in (lambda: api.get_config_value("username"), lambda: api.config_values.get("username"), lambda: os.environ.get("KAGGLE_USERNAME")):
    try:
        user = getter()
    except Exception:
        user = None
    if user: break
if not user:
    try:
        import subprocess
        txt = subprocess.run(["kaggle", "config", "view"], capture_output=True, text=True).stdout
        for line in txt.splitlines():
            if "username" in line: user = line.split(":")[-1].strip()
    except Exception: pass
if not user: sys.exit("could not determine Kaggle username")
os.makedirs(out, exist_ok=True)
src = open(os.path.join(os.path.dirname(__file__), "imggen_kernel.py")).read()
open(os.path.join(out, "imggen.py"), "w").write(src.replace("__JOB_JSON__", json.dumps(job).replace("'''", "")))
meta = {"id": f"{user}/for-imggen", "title": "for-imggen", "code_file": "imggen.py", "language": "python",
        "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_internet": True,
        "machine_shape": "NvidiaTeslaT4", "dataset_sources": [], "competition_sources": [], "kernel_sources": []}
json.dump(meta, open(os.path.join(out, "kernel-metadata.json"), "w"), indent=1)
print("kernel folder ready")
