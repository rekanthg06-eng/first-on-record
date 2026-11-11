#!/usr/bin/env python3
"""Scene-route compositor: illustrated stills with 2.5D parallax + real-object proof clips + big word captions.

Usage: compose.py <timeline.json> <out.mp4> [--preview]
timeline.json:
  {"fps":30,"audio":"path","words":"words.json","duration":29.5,"img_dir":"...","clip":"clean.mp4",
   "shots":[{"t":0.0,"img":"s01_roll","zoom":[1.06,1.2],"pan":[0,0,0.04,0],"par":16},
            {"t":2.66,"clip":[17.6],"view":[0.5,0.36,0.8],"chip":"THE REAL TABLET"}], ...}
Every shot runs from its "t" to the next shot's "t" (the last one to "duration").
"""
import json, os, subprocess, sys
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "fonts", "Poppins-ExtraBold.ttf")
YEL = (255, 208, 60)


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


class Still:
    def __init__(self, path, depth_path):
        img = cv2.imread(path, cv2.IMREAD_COLOR)
        s = max(W / img.shape[1], H / img.shape[0]) * 1.0
        self.img = cv2.resize(img, (int(round(img.shape[1] * s)), int(round(img.shape[0] * s))), interpolation=cv2.INTER_LANCZOS4)
        self.ih, self.iw = self.img.shape[:2]
        if depth_path and os.path.exists(depth_path):
            d = cv2.imread(depth_path, cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255.0
            d = cv2.resize(d, (self.iw, self.ih), interpolation=cv2.INTER_CUBIC)
            self.depth = cv2.GaussianBlur(d, (0, 0), 6)
        else:
            self.depth = None
        ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
        self.xs, self.ys = xs - W / 2, ys - H / 2

    def frame(self, p, sh):
        z0, z1 = sh.get("zoom", [1.08, 1.18])
        pan = sh.get("pan", [0, 0, 0, 0])
        e = ease(p) * 0.6 + p * 0.4
        z = z0 + (z1 - z0) * e
        cx = self.iw / 2 + (pan[0] + (pan[2] - pan[0]) * e) * self.iw
        cy = self.ih / 2 + (pan[1] + (pan[3] - pan[1]) * e) * self.ih
        u = cx + self.xs / z
        v = cy + self.ys / z
        if self.depth is not None and sh.get("par", 14):
            amp = sh.get("par", 14)
            dx, dy = sh.get("par_dir", [1.0, 0.25])
            dm = cv2.remap(self.depth, u, v, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            k = (dm - 0.5) * amp * (p - 0.5) * 2.0
            u = u + k * dx
            v = v + k * dy
        return cv2.remap(self.img, u, v, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)


class Clip:
    def __init__(self, path):
        self.cap = cv2.VideoCapture(path)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.n = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.pos, self.last = -1, None

    def at(self, t):
        i = int(min(max(t * self.fps, 0), self.n - 1))
        if i != self.pos:
            if i != self.pos + 1:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ok, f = self.cap.read()
            if ok:
                self.last = f
            self.pos = i
        return self.last

    def frame(self, p, sh, dur):
        src0 = sh["clip"][0]
        speed = sh.get("speed", 1.0)
        f = self.at(src0 + p * dur * speed)
        cx, cy, hf = sh.get("view", [0.5, 0.4, 0.85])
        hf2 = sh.get("view_end", [cx, cy, hf])
        e = ease(p)
        cx, cy, hf = (a + (b - a) * e for a, b in zip((cx, cy, hf), hf2))
        hh = hf * f.shape[0]
        ww = hh * W / H
        x0 = min(max(cx * f.shape[1] - ww / 2, 0), f.shape[1] - ww)
        y0 = min(max(cy * f.shape[0] - hh / 2, 0), f.shape[0] - hh)
        M = np.float32([[ww / W, 0, x0], [0, hh / H, y0]])
        return cv2.warpAffine(f, M, (W, H), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)


# ---------- captions ----------
def chunk_words(words, max_words=3, max_chars=17):
    chunks, cur = [], []
    for w in words:
        txt = " ".join(x["w"] for x in cur + [w])
        if cur and (len(cur) >= max_words or len(txt) > max_chars or w["s"] - cur[-1]["e"] > 0.35):
            chunks.append(cur); cur = []
        cur.append(w)
        if w["w"][-1] in ".?!:,":
            chunks.append(cur); cur = []
    if cur:
        chunks.append(cur)
    return chunks


_cache = {}


def caption_img(chunk, active):
    key = (id(chunk), active)
    if key in _cache:
        return _cache[key]
    toks = [w["w"].upper().rstrip(",") for w in chunk]
    size = 104
    while True:
        font = ImageFont.truetype(FONT, size)
        sp = font.getlength(" ")
        widths = [font.getlength(t) for t in toks]
        total = sum(widths) + sp * (len(toks) - 1)
        if total <= 940 or size <= 60:
            break
        size -= 4
    stroke = max(8, size // 9)
    hh = int(size * 1.5) + stroke * 2
    im = Image.new("RGBA", (int(total) + stroke * 4 + 20, hh + 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = stroke * 2 + 10
    for i, t in enumerate(toks):
        col = YEL if i == active else (255, 255, 255)
        d.text((x + 4, stroke + 10), t, font=font, fill=(0, 0, 0, 150), stroke_width=stroke, stroke_fill=(0, 0, 0, 150))
        d.text((x, stroke + 4), t, font=font, fill=col + (255,), stroke_width=stroke, stroke_fill=(12, 10, 8, 255))
        x += widths[i] + sp
    _cache[key] = np.array(im)
    return _cache[key]


def blend(frame, rgba, cx, cy, scale=1.0, alpha=1.0):
    if scale != 1.0:
        rgba = cv2.resize(rgba, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
    h, w = rgba.shape[:2]
    x0, y0 = int(cx - w / 2), int(cy - h / 2)
    xa, ya, xb, yb = max(x0, 0), max(y0, 0), min(x0 + w, W), min(y0 + h, H)
    if xa >= xb or ya >= yb:
        return
    sub = rgba[ya - y0:yb - y0, xa - x0:xb - x0]
    a = (sub[..., 3:4].astype(np.float32) / 255.0) * alpha
    roi = frame[ya:yb, xa:xb].astype(np.float32)
    frame[ya:yb, xa:xb] = (roi * (1 - a) + sub[..., 2::-1].astype(np.float32) * a).astype(np.uint8)


def chip_img(text, size=34):
    font = ImageFont.truetype(FONT, size)
    tw = int(font.getlength(text))
    im = Image.new("RGBA", (tw + 56, size + 34), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, im.width - 1, im.height - 1), radius=(size + 34) // 2, fill=YEL + (255,))
    d.text((28, 12), text, font=font, fill=(20, 16, 10, 255))
    return np.array(im)


def main():
    tl = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    preview = "--preview" in sys.argv
    base = os.path.dirname(os.path.abspath(sys.argv[1]))
    P = lambda p: p if os.path.isabs(p) else os.path.join(base, p)
    fps = tl.get("fps", 30)
    dur = tl["duration"]
    shots = tl["shots"]
    for i, s in enumerate(shots):
        s["end"] = shots[i + 1]["t"] if i + 1 < len(shots) else dur
    words = json.load(open(P(tl["words"])))
    if words:
        words[0]["s"] = min(words[0]["s"], 0.0 + tl.get("first_caption_at", 0.0))
    chunks = chunk_words(words)
    spans = []
    for i, c in enumerate(chunks):
        end = chunks[i + 1][0]["s"] if i + 1 < len(chunks) else c[-1]["e"] + 0.6
        spans.append((c[0]["s"], min(end, c[-1]["e"] + 0.9), c))
    clip = Clip(P(tl["clip"])) if tl.get("clip") else None
    stills = {}
    # vignette + caption shade
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.75)) ** 2)
    vig = np.clip(1.08 - 0.42 * r ** 2.2, 0.55, 1.0)
    cap_y = int(H * tl.get("caption_y", 0.66))
    band = np.exp(-((yy - cap_y) / 150.0) ** 2) * 0.30
    shade = (vig * (1 - band))[..., None]
    rng = np.random.default_rng(7)
    grain = [rng.normal(0, 4.0, (H // 2, W // 2, 1)).astype(np.float32) for _ in range(8)]
    step = 3 if preview else 1
    size = f"{W // 2}x{H // 2}" if preview else f"{W}x{H}"
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", size, "-r", str(fps / step), "-i", "-"]
    if tl.get("audio"):
        cmd += ["-i", P(tl["audio"]), "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "192k"]
    cmd += ["-c:v", "libx264", "-preset", "veryfast" if preview else "slow", "-crf", "26" if preview else "18",
            "-maxrate", "10M", "-bufsize", "20M", "-pix_fmt", "yuv420p", "-r", str(fps / step), "-t", str(dur), "-movflags", "+faststart", out]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = int(round(dur * fps))
    chips = {}
    for fi in range(0, n, step):
        t = fi / fps
        si = max(i for i, s in enumerate(shots) if s["t"] <= t + 1e-6)
        sh = shots[si]
        sd = sh["end"] - sh["t"]
        p = (t - sh["t"]) / sd
        if "img" in sh:
            if sh["img"] not in stills:
                d = P(os.path.join(tl["img_dir"], sh["img"] + ".png"))
                stills[sh["img"]] = Still(d, d[:-4] + "_depth.png")
            fr = stills[sh["img"]].frame(p, sh)
        else:
            fr = clip.frame(p, sh, sd)
        # cut punch: quick settle-in on the first frames of every shot
        k = t - sh["t"]
        if k < 0.13 and si > 0:
            z = 1.0 + 0.045 * (1 - ease(k / 0.13))
            M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, z)
            fr = cv2.warpAffine(fr, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        f32 = fr.astype(np.float32) * shade
        g = cv2.resize(grain[fi % 8], (W, H), interpolation=cv2.INTER_LINEAR)
        fr = np.clip(f32 + g[..., None] if g.ndim == 2 else f32 + g, 0, 255).astype(np.uint8)
        if sh.get("chip"):
            if sh["chip"] not in chips:
                chips[sh["chip"]] = chip_img(sh["chip"])
            a = ease(k / 0.18)
            blend(fr, chips[sh["chip"]], W / 2, H * sh.get("chip_y", 0.145) + (1 - a) * 20, alpha=a)
        for (cs, ce, c) in spans:
            if cs <= t < ce:
                act = max([i for i, w in enumerate(c) if w["s"] <= t + 1e-6] or [0])
                kk = t - cs
                sc = 0.86 + 0.14 * ease(kk / 0.10) if cs > 0.05 else 1.0
                blend(fr, caption_img(c, act), W / 2, cap_y, scale=sc)
                break
        if preview:
            fr = cv2.resize(fr, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
        ff.stdin.write(fr.tobytes())
    ff.stdin.close()
    ff.wait()
    print("wrote", out)


if __name__ == "__main__":
    main()
