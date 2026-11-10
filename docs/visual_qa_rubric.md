# Visual QA gate (added 2026-11-10 after the user judged the Antikythera Short "looks like shit")

Every Short passes TWO stages, twice: on the preview frames in session A (before the render is dispatched, where fixing is cheap) and on the finished mp4 in session B (before upload).

## Stage 1: numbers (`tools/visual_qa.py`)
- Session A: `python3 tools/visual_qa.py frames /tmp/pv` on the blender_preview pngs (first frame + one per beat + finish, at least 6).
- Session B: `python3 tools/visual_qa.py video final.mp4 --out /tmp/qa` (12 frames + contact sheet).
- Catches: flat untextured CG, washed-out grade, empty frames, no shadows/depth, a non-striking first frame, a bright bed behind the white captions, text running off the frame.
- Calibration: the Antikythera (pWnOfSEXl70) and Ziggurat (FvVr01t9leA) Shorts fail it on every frame. Do not loosen a threshold to get a pass; a threshold changes only with a reason logged in `learnings.md`.

## Stage 2: independent reviewer (a fresh subagent)
The builder never grades its own work. Spawn a NEW agent (Agent tool, subagent_type general-purpose) with ONLY: the contact sheet, 3 full-size frames (first frame, the macro moment, the finish), the one-line topic, and this rubric. Do not send it the script, your reasoning or what you think is good. Prompt it to be a harsh YouTube Shorts viewer and art director and to return JSON only:

```
{"scores": {"first_frame": n, "materials": n, "lighting_depth": n, "composition": n, "legibility": n, "clarity": n, "polish": n},
 "worst_problems": ["..."], "fixes": ["concrete change in scene.py/kit terms"], "would_you_scroll_past": true/false, "verdict": "PASS"|"FAIL"}
```

Tell the reviewer the channel's fixed limits so its fixes stay usable: no fake inscriptions or invented text on objects (blank cartouches only), no real-photo textures, one continuous camera move with no cuts, reconstructions are labelled.

Scores are 1-10:
- first_frame: would this frame stop a thumb in the Shorts feed? An empty box, a blank plain or a tiny subject is 3 or less.
- materials: do surfaces read as real stuff (bronze, wood, stone, clay) with grain, wear, edge highlights? Flat beige "cardboard / clay placeholder" is 3 or less.
- lighting_depth: a clear key light, deep shadows, separation from the background, no haze wash.
- composition: the subject fills the 9:16 frame; nothing important is clipped at the edges; no big dead areas of sky/ground.
- legibility: captions, pills and the source line are readable on a phone, never run off the frame, never sit on a bright area.
- clarity: a viewer can tell what each beat shows without the narration (the gear, the slot, the dial...).
- polish: no visible artefacts (black corner nubs, z-fighting, intersecting parts, floating objects, popping).

PASS needs every score at 6 or more, average 7 or more, would_you_scroll_past false, AND stage 1 PASS.

## What to do with the result
- Session A: on FAIL apply the reviewer's fixes and re-preview; up to 4 rounds (each round = preview, stage 1, a NEW reviewer agent). If still FAIL after round 4, dispatch the best version anyway and put the reviewer verdict in `pending.json` under `qa`.
- Session B: run both stages on the final mp4. On FAIL, if there is time before about 06:00 IST, fix and re-dispatch once; otherwise (user decision 2026-11-10) PUBLISH ANYWAY and start the final message with `ALERT: visual QA failed` plus the 3 worst problems and scores, so the user sees it.
- Log every verdict (scores, pass/fail, round) in the episode log line and in `qa_log.csv` in private-for-learning, so the bar can be tracked.
