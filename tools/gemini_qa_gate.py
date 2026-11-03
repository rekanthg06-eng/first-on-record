#!/usr/bin/env python3
"""Module A: multimodal QA gate for First on Record Shorts.

Uploads a rendered .mp4 to the Gemini File API, asks gemini-4-argon to judge it,
validates the JSON verdict, and (optionally) drives a re-render retry loop.

Needs: pip install "google-genai>=2.30.1"; env GEMINI_API_KEY (billing-enabled key,
gemini-4-argon has no free tier). Set QA_MODEL to override the model id
(e.g. a cheaper fallback). Fail-closed: any error or unparsable verdict means NOT approved.

CLI:  python gemini_qa_gate.py video.mp4 [--attempt N] [--out verdict.json]
Exit codes: 0 approved, 1 rejected (verdict written), 2 gate error (treat as not approved).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Callable

MODEL = os.environ.get("QA_MODEL", "gemini-4-argon")
MIN_SCORE = 8.0
MAX_OUTPUT_TOKENS = 65536  # thinking tokens count toward this; never below 32768
UPLOAD_POLL_S = 3
UPLOAD_TIMEOUT_S = 300

PROMPT = """You are the Multimodal QA Gate for an automated YouTube channel targeting fast YouTube Partner Program (YPP) monetization. Inspect the attached .mp4 video and audio track against these 4 criteria:
1. 0:00-0:02 Kinetic Hook: Immediate visual motion and pattern interrupt in frame 1 (no static title cards or slow black fade-ins).
2. Mobile UI Safe Zones & Legibility: No critical text or visual focal points clipped or covered by YouTube Shorts/watch-page UI overlays (bottom 20% and right-side action bar).
3. Audio-Visual Sync & Pacing: Clean audio transitions, zero dead air >0.4s, and visual state changes matching audio beats/narration.
4. YPP Anti-Repetitive Compliance: Sufficient dynamic visual variation (camera motion, layout, pacing, color palette) so it does not look like a static mass-produced template.

Return ONLY valid JSON matching the required schema. If approved is false or overall_score < 8.0, populate parameter_overrides_for_retry and code_patch_instructions with exact coordinate, timing, or CSS/Canvas/FFmpeg fixes.

Schema:
{"approved": bool, "overall_score": number 0-10, "hook_strength_0_to_3s": number 0-10,
 "visual_bugs": [string], "audio_issues": [string],
 "parameter_overrides_for_retry": {"pacing_multiplier": number, "text_y_offset_px": number, "visual_theme_seed": string},
 "code_patch_instructions": string}
Use empty lists when there are no bugs/issues. Be strict and specific; cite timestamps."""

REQUIRED = {
    "approved": bool,
    "overall_score": (int, float),
    "hook_strength_0_to_3s": (int, float),
    "visual_bugs": list,
    "audio_issues": list,
    "parameter_overrides_for_retry": dict,
    "code_patch_instructions": str,
}
# Overrides a re-render is allowed to receive (anything else is dropped).
OVERRIDE_LIMITS = {"pacing_multiplier": (0.7, 1.5), "text_y_offset_px": (-400, 400)}


class GateError(RuntimeError):
    pass


@dataclass
class Verdict:
    approved: bool
    overall_score: float
    hook_strength_0_to_3s: float
    visual_bugs: list = field(default_factory=list)
    audio_issues: list = field(default_factory=list)
    parameter_overrides_for_retry: dict = field(default_factory=dict)
    code_patch_instructions: str = ""
    raw: dict = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        # Our rule, enforced here regardless of what the model claims.
        return self.approved and self.overall_score >= MIN_SCORE

    def to_json(self) -> dict:
        d = dict(self.raw)
        d["passed"] = self.passed
        return d


def parse_verdict(text: str) -> Verdict:
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        t = t[t.find("{"):]
    start, end = t.find("{"), t.rfind("}")
    if start < 0 or end < start:
        raise GateError("no JSON object in model reply")
    try:
        d = json.loads(t[start:end + 1])
    except json.JSONDecodeError as e:
        raise GateError(f"bad JSON: {e}") from e
    for k, typ in REQUIRED.items():
        if k not in d:
            raise GateError(f"missing key {k}")
        if isinstance(d[k], bool) and typ is not bool:
            raise GateError(f"wrong type for {k}")
        if not isinstance(d[k], typ):
            raise GateError(f"wrong type for {k}")
    for k in ("overall_score", "hook_strength_0_to_3s"):
        if not 0 <= d[k] <= 10:
            raise GateError(f"{k} out of range")
    return Verdict(
        approved=d["approved"], overall_score=float(d["overall_score"]),
        hook_strength_0_to_3s=float(d["hook_strength_0_to_3s"]),
        visual_bugs=[str(x) for x in d["visual_bugs"] if str(x).lower() != "none"],
        audio_issues=[str(x) for x in d["audio_issues"] if str(x).lower() != "none"],
        parameter_overrides_for_retry=d["parameter_overrides_for_retry"],
        code_patch_instructions=d["code_patch_instructions"], raw=d,
    )


def safe_overrides(ov: dict) -> dict:
    """Clamp model-suggested overrides; drop unknown keys. Model output is untrusted."""
    out: dict[str, Any] = {}
    for k, (lo, hi) in OVERRIDE_LIMITS.items():
        v = ov.get(k)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            out[k] = min(hi, max(lo, float(v)))
    seed = ov.get("visual_theme_seed")
    if isinstance(seed, str) and seed.replace("-", "").replace("_", "").isalnum() and len(seed) <= 40:
        out["visual_theme_seed"] = seed
    return out


def _client():
    from google import genai
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise GateError("GEMINI_API_KEY not set")
    return genai.Client(api_key=key)


def evaluate(video_path: str, attempt: int = 1, client=None) -> Verdict:
    """One QA pass. attempt 1 = thinking medium; attempt >= 2 escalates to high."""
    from google.genai import types
    if not os.path.isfile(video_path) or os.path.getsize(video_path) == 0:
        raise GateError(f"missing or empty video: {video_path}")
    client = client or _client()
    level = "medium" if attempt <= 1 else "high"
    f = client.files.upload(file=video_path)
    try:
        deadline = time.time() + UPLOAD_TIMEOUT_S
        while True:
            state = getattr(f.state, "name", str(f.state))
            if state == "ACTIVE":
                break
            if state == "FAILED" or time.time() > deadline:
                raise GateError(f"file upload state {state}")
            time.sleep(UPLOAD_POLL_S)
            f = client.files.get(name=f.name)
        # NOTE: no temperature/top_p/top_k: ignored by Gemini 4 models.
        cfg = types.GenerateContentConfig(
            max_output_tokens=MAX_OUTPUT_TOKENS,
            thinking_config=types.ThinkingConfig(thinking_level=level),
            response_mime_type="application/json",
        )
        resp = client.models.generate_content(
            model=MODEL,
            contents=[types.Part.from_uri(file_uri=f.uri, mime_type=f.mime_type or "video/mp4"), PROMPT],
            config=cfg,
        )
        text = resp.text or ""
        return parse_verdict(text)
    finally:
        try:
            client.files.delete(name=f.name)  # keep File API storage clean
        except Exception:
            pass


def gate_with_retries(render: Callable[[dict], str], max_attempts: int = 3, client=None) -> tuple[str, Verdict, list]:
    """render(overrides)->mp4 path. Re-renders with clamped overrides until passed.

    Returns (final_path, last_verdict, history). If never passed, caller must upload
    PRIVATE (or hold) and alert. code_patch_instructions are logged in history for the
    Claude run to apply; they are never executed automatically.
    """
    overrides: dict = {}
    history: list = []
    path = render(overrides)
    verdict = None
    for attempt in range(1, max_attempts + 1):
        verdict = evaluate(path, attempt=attempt, client=client)
        history.append({"attempt": attempt, "overrides": overrides, **verdict.to_json()})
        if verdict.passed:
            return path, verdict, history
        if attempt == max_attempts:
            break
        overrides = {**overrides, **safe_overrides(verdict.parameter_overrides_for_retry)}
        path = render(overrides)
    return path, verdict, history


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--attempt", type=int, default=1)
    ap.add_argument("--out", default="qa_verdict.json")
    a = ap.parse_args()
    try:
        v = evaluate(a.video, attempt=a.attempt)
    except Exception as e:  # fail closed
        json.dump({"passed": False, "error": str(e)}, open(a.out, "w"), indent=2)
        print(f"GATE ERROR: {e}", file=sys.stderr)
        return 2
    json.dump(v.to_json(), open(a.out, "w"), indent=2)
    print(("APPROVED" if v.passed else "REJECTED"), v.overall_score, v.visual_bugs, v.audio_issues)
    return 0 if v.passed else 1


if __name__ == "__main__":
    sys.exit(main())
