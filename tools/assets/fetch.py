"""Fetch and prepare the real-object assets for one Short, with their licences.  Runs on GitHub Actions (the sandbox cannot reach
museum sites).  python tools/assets/fetch.py blender/<scene>/assets.json --out assets/<scene>

assets.json = {"items": [ {...}, ... ]}; every item has an "id" (output file stem) and a "kind":
  url             {"url", "license", "credit", "source_page"}        any direct file (GLB/OBJ/zip/jpg); licence is DECLARED by the caller
  met_image       {"object_id"}                                      primary image of a Met object; refused unless isPublicDomain (CC0)
  commons         {"query"}                                          best Commons match via tools/commons_images.py (PD/CC0/CC BY only)
  polyhaven_hdri  {"name", "res": "2k"}                              CC0 HDRI
  depth           {"from": "<id of an image item>"}                  monocular depth map (16-bit PNG, white = near)
  cutout          {"from": "<id of an image item>"}                  RGBA cut-out of the main object
Writes <out>/<id>.<ext> and <out>/manifest.json [{id, file, license, credit, source_page}].  Anything whose licence is not
commercial-safe (CC0, public domain, CC BY) is refused: the channel is monetized.
"""
import argparse, json, os, re, subprocess, sys, urllib.request

OK = re.compile(r"^(cc0|public ?domain|pd|cc[- ]by( \d\.\d)?)$", re.I)   # no SA/NC/ND (same rule as commons_images.py)
UA = {"User-Agent": "FirstOnRecordBot/1.0 (github.com/rekanthg06-eng/first-on-record)"}

def get(url, path=None):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    if path:
        open(path, "wb").write(data)
    return data

def ext_of(url, default=".bin"):
    e = os.path.splitext(url.split("?")[0])[1].lower()
    return e if e and len(e) <= 6 else default

def check(lic):
    if not OK.match((lic or "").strip()):
        raise SystemExit(f"REFUSED licence '{lic}': only CC0 / public domain / CC BY are allowed")

def do_url(it, out):
    check(it.get("license")); f = os.path.join(out, it["id"] + ext_of(it["url"])); get(it["url"], f)
    return f, it["license"], it.get("credit", ""), it.get("source_page", it["url"])

def do_met(it, out):
    o = json.loads(get(f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{int(it['object_id'])}"))
    if not o.get("isPublicDomain"): raise SystemExit(f"Met object {it['object_id']} is not Open Access (isPublicDomain false)")
    url = o.get("primaryImage") or ""
    if not url: raise SystemExit(f"Met object {it['object_id']} has no primaryImage")
    f = os.path.join(out, it["id"] + ext_of(url, ".jpg")); get(url, f)
    credit = f"The Metropolitan Museum of Art, {o.get('title','')}, {o.get('accessionNumber','')} (CC0)"
    return f, "CC0", credit, o.get("objectURL", "")

def do_commons(it, out):
    tmp = os.path.join(out, "_c_" + it["id"])
    subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "..", "commons_images.py"), it["query"], "--out", tmp, "--limit", "6", "--width", "2000"], check=True)
    kept = json.load(open(os.path.join(tmp, "manifest.json")))["kept"]
    if not kept: raise SystemExit(f"no reusable Commons image for '{it['query']}'")
    k = kept[int(it.get("pick", 0))]; f = os.path.join(out, it["id"] + ".jpg"); os.replace(os.path.join(tmp, k["file"]), f)
    return f, ("CC0" if k["kind"] == "pd" else k["license"]), k["attribution"], k["page"]

def do_hdri(it, out):
    res = it.get("res", "2k"); files = json.loads(get(f"https://api.polyhaven.com/files/{it['name']}"))
    url = files["hdri"][res]["hdr"]["url"]; f = os.path.join(out, it["id"] + ".hdr"); get(url, f)
    return f, "CC0", f"Poly Haven, {it['name']} (CC0)", f"https://polyhaven.com/a/{it['name']}"

def src_file(out, sid):
    for x in os.listdir(out):
        if os.path.splitext(x)[0] == sid and not x.endswith(".json"): return os.path.join(out, x)
    raise SystemExit(f"source item '{sid}' not found (order items so sources come first)")

def do_depth(it, out):
    from transformers import pipeline
    from PIL import Image
    import numpy as np
    model = it.get("model", "depth-anything/Depth-Anything-V2-Small-hf")
    im = Image.open(src_file(out, it["from"])).convert("RGB")
    d = np.array(pipeline("depth-estimation", model=model, device=-1)(im)["predicted_depth"].squeeze(), dtype="float32")
    d = (d - d.min()) / max(1e-6, d.max() - d.min())
    Image.fromarray((d * 65535).astype("uint16")).resize(im.size, Image.BICUBIC).save(os.path.join(out, it["id"] + ".png"))
    return os.path.join(out, it["id"] + ".png"), "derived", f"depth map from '{it['from']}' ({model})", ""

def do_cutout(it, out):
    from rembg import remove, new_session
    from PIL import Image
    im = Image.open(src_file(out, it["from"])).convert("RGB")
    res = remove(im, session=new_session(it.get("model", "isnet-general-use")))
    f = os.path.join(out, it["id"] + ".png"); res.save(f)
    return f, "derived", f"cut-out of '{it['from']}'", ""

KINDS = dict(url=do_url, met_image=do_met, commons=do_commons, polyhaven_hdri=do_hdri, depth=do_depth, cutout=do_cutout)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("spec"); ap.add_argument("--out", required=True); a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True); man = []
    for it in json.load(open(a.spec))["items"]:
        f, lic, credit, page = KINDS[it["kind"]](it, a.out)
        man.append(dict(id=it["id"], file=os.path.basename(f), license=lic, credit=credit, source_page=page))
        print("ok", it["id"], os.path.basename(f), lic, flush=True)
    json.dump(man, open(os.path.join(a.out, "manifest.json"), "w"), indent=1)
    # credit lines for the description (CC BY needs them)
    open(os.path.join(a.out, "credits.txt"), "w").write("\n".join(m["credit"] for m in man if m["license"] not in ("derived",) and m["credit"]) + "\n")
