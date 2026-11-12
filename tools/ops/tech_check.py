#!/usr/bin/env python3
"""No-model technical gate for a finished Short (runbook v4): tech_check.py <video.mp4> [--json out.json]
Checks: 1080x1920, duration <= 60 s, integrated loudness -14 LUFS (+-1), true peak <= -1.5 dBTP, no black frames.
Exit 0 = pass, 1 = fail. Needs ffmpeg/ffprobe."""
import json, re, subprocess, sys

def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)

def main():
    path = sys.argv[1]
    pr = json.loads(run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height,r_frame_rate",
                         "-of", "json", path]).stdout)
    v = next(s for s in pr["streams"] if s["codec_type"] == "video")
    has_audio = any(s["codec_type"] == "audio" for s in pr["streams"])
    dur = float(pr["format"]["duration"])
    r = {"width": v["width"], "height": v["height"], "duration": round(dur, 2), "audio": has_audio}
    fails = []
    if (v["width"], v["height"]) != (1080, 1920): fails.append("resolution is not 1080x1920")
    if dur > 60: fails.append("longer than 60 s")
    if not has_audio: fails.append("no audio stream")
    else:
        e = run(["ffmpeg", "-nostats", "-i", path, "-filter_complex", "ebur128=peak=true", "-f", "null", "-"]).stderr
        tail = e[e.rfind("Summary:"):]
        i = re.search(r"I:\s+(-?[\d.]+) LUFS", tail); p = re.search(r"Peak:\s+(-?[\d.]+) dBFS", tail)
        r["lufs"] = float(i.group(1)) if i else None; r["true_peak"] = float(p.group(1)) if p else None
        if r["lufs"] is None or abs(r["lufs"] + 14) > 1.0: fails.append(f"loudness {r['lufs']} LUFS (target -14 +-1)")
        if r["true_peak"] is None or r["true_peak"] > -1.5: fails.append(f"true peak {r['true_peak']} dBTP (limit -1.5)")
    b = run(["ffmpeg", "-nostats", "-i", path, "-vf", "blackdetect=d=0.2:pix_th=0.08", "-an", "-f", "null", "-"]).stderr
    r["black"] = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", b)
    if r["black"]: fails.append(f"black frames at {r['black'][:3]}")
    r["fails"] = fails; r["verdict"] = "fail" if fails else "pass"
    if "--json" in sys.argv: json.dump(r, open(sys.argv[sys.argv.index("--json") + 1], "w"), indent=1)
    print(json.dumps(r))
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    main()
