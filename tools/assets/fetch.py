"""Fetch and prepare the real-object assets for one Short, with their licences.  Runs on GitHub Actions (the sandbox cannot reach
museum sites).  python tools/assets/fetch.py blender/<scene>/assets.json --out assets/<scene>

assets.json = {"items": [ {...}, ... ]}; every item has an "id" (output file stem) and a "kind":
  url             {"url", "license", "credit", "source_page"}        any direct file (GLB/OBJ/zip/jpg); licence is DECLARED by the caller
  met_image       {"object_id"}                                      primary image of a Met object; refused unless isPublicDomain (CC0)
  commons         {"query"}                                          best Commons match via tools/commons_images.py (PD/CC0/CC BY only)
  polyhaven_hdri  {"name", "res": "2k"}                              CC0 HDRI
  met_3d          {"object_id"}                                      Met 3D scan (GLB, Vntana CDN); needs the object to be Open Access
  smithsonian_3d  {"si_id"}                                           Smithsonian Open Access 3D (CC0 only), GLB; key: env SI_API_KEY or DEMO_KEY
  sketchfab       {"uid"}                                            Sketchfab model, CC0 or CC BY only; needs env SKETCHFAB_TOKEN (free account)
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

def met_obj(oid):
    return json.loads(get(f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{int(oid)}"))

def do_met3d(it, out):
    o = met_obj(it["object_id"])
    if not o.get("isPublicDomain"): raise SystemExit(f"Met object {it['object_id']} is not Open Access")
    urls = []
    try:     # live object page -> vntanaAssets (same method as github.com/InconsolableCellist/met_scans)
        html = get(f"https://www.metmuseum.org/art/collection/search/{int(it['object_id'])}").decode("utf8", "replace")
        i = html.find("vntanaAssets")
        if i >= 0:
            ch = html[i:i+40000].replace('\\\\', '\\').replace('\\"', '"')
            for m in re.finditer(r'"uuid":"([0-9a-f-]{36})".{0,4000}?"clientSlug":"([^"]+)"', ch):
                uuid, client = m.group(1), m.group(2)
                for b in re.finditer(r'"conversionFormat":"GLB"[^{}]{0,400}?"modelBlobId":"([0-9a-f-]{36})"|"modelBlobId":"([0-9a-f-]{36})"[^{}]{0,400}?"conversionFormat":"GLB"', ch[m.start():m.start()+8000]):
                    urls.append(f"https://api.vntana.com/assets/products/{uuid}/organizations/The-Metropolitan-Museum-of-Art/clients/{client}/{b.group(1) or b.group(2)}")
    except Exception as e:
        print("met page parse failed:", e, flush=True)
    if not urls:  # fallback: community catalog of the same CDN links
        cat = json.loads(get("https://raw.githubusercontent.com/InconsolableCellist/met_scans/main/catalog.json"))
        for e in (cat if isinstance(cat, list) else cat.values()):
            if int(e.get("object_id", 0)) == int(it["object_id"]):
                urls += [f["download_url"] for f in e.get("files", []) if f.get("format") == "GLB"]
    if not urls: raise SystemExit(f"no Met 3D model found for {it['object_id']}")
    f = os.path.join(out, it["id"] + ".glb"); get(urls[0], f)
    return f, "CC0", f"The Metropolitan Museum of Art, {o.get('title','')}, {o.get('accessionNumber','')} (3D model, Open Access CC0)", o.get("objectURL", "")

def do_si3d(it, out):
    key = os.environ.get("SI_API_KEY") or "DEMO_KEY"
    r = json.loads(get(f"https://api.si.edu/openaccess/api/v1.0/content/{it["si_id"]}?api_key={key}"))["response"]
    media = (((r.get("content") or {}).get("descriptiveNonRepeating") or {}).get("online_media") or {}).get("media", [])
    best = None
    for m in media:
        if m.get("type") != "3d_voyager" or (m.get("usage") or {}).get("access") != "CC0": continue
        for res in m.get("resources", []):
            u = res.get("url", "")
            if u.endswith(".glb"):
                score = (("150k" in u) * 3) + (("std" in u) * 2) + ("high" in u)
                if not best or score > best[0]: best = (score, u)
    if not best: raise SystemExit(f"no CC0 GLB for Smithsonian {it["si_id"]}")
    f = os.path.join(out, it["id"] + ".glb"); get(best[1], f)
    return f, "CC0", f"Smithsonian Institution, {r.get('title','')} (3D, CC0)", (r.get("content") or {}).get("descriptiveNonRepeating", {}).get("record_link", "")

def do_sketchfab(it, out):
    tok = os.environ.get("SKETCHFAB_TOKEN")
    if not tok: raise SystemExit("SKETCHFAB_TOKEN secret not set (free Sketchfab account -> settings -> password & API)")
    info = json.loads(get(f"https://api.sketchfab.com/v3/models/{it['uid']}"))
    lic = ((info.get("license") or {}).get("label") or "").strip()
    norm = {"CC0 Public Domain": "CC0", "CC Attribution": "CC BY", "Public Domain": "CC0"}.get(lic, lic)
    check(norm)
    req = urllib.request.Request(f"https://api.sketchfab.com/v3/models/{it['uid']}/download", headers={**UA, "Authorization": f"Token {tok}"})
    dl = json.loads(urllib.request.urlopen(req, timeout=60).read())
    g = dl.get("glb") or dl.get("gltf"); z = os.path.join(out, it["id"] + (".glb" if dl.get("glb") else ".zip")); get(g["url"], z)
    if z.endswith(".zip"):
        import zipfile; d = os.path.join(out, it["id"] + "_gltf"); zipfile.ZipFile(z).extractall(d); os.remove(z)
        z = next(os.path.join(dp, f) for dp, _, fs in os.walk(d) for f in fs if f.endswith(".gltf"))
    who = (info.get("user") or {}).get("displayName", "")
    return z, norm, f"{info.get('name','')} by {who}, Sketchfab ({norm})", info.get("viewerUrl", "")

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
    from PIL import ImageFilter
    res = remove(im, session=new_session(it.get("model", "birefnet-general")))   # MIT weights; NOT the rembg default (bria-rmbg needs a paid licence) nor isnet (weights licence unstated)
    # pull the edge in a few px and feather it: kills the bright background halo around cut-out objects (seen in test 2026-11-10)
    r, g, b, a = res.split(); px = max(3, im.size[0] // 600) | 1
    a = a.filter(ImageFilter.MinFilter(px)).filter(ImageFilter.GaussianBlur(px / 2)); res = Image.merge("RGBA", (r, g, b, a))
    f = os.path.join(out, it["id"] + ".png"); res.save(f)
    return f, "derived", f"cut-out of '{it['from']}'", ""

KINDS = dict(url=do_url, met_image=do_met, met_3d=do_met3d, smithsonian_3d=do_si3d, sketchfab=do_sketchfab, commons=do_commons, polyhaven_hdri=do_hdri, depth=do_depth, cutout=do_cutout)

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
