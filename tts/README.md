# Open-source narration (tts_voice workflow)

Why: local Kokoro narration sounds synthetic and no paid voice API is used. The Action runs **Chatterbox** (MIT license, CPU) on a free GitHub runner, so the Claude sandbox needs no model or key.

Flow: the daily run pushes `tts/requests/<slug>.json` to `main` -> Action `tts_voice` -> branch `tts-out` gets `tts/<slug>/voice.wav` (24 kHz mono), `words.json` (word times on the SCRIPT's words) and `meta.json`. The run then fetches them:

    git fetch origin tts-out && git show origin/tts-out:tts/<slug>/voice.wav > voice.wav   # likewise words.json, meta.json

Poll `git fetch origin tts-out` until the slug appears. Only the 8 newest slugs are kept; slugs start with yyyymmdd. Several request files in one push are all processed in one run.

## Request contract
See the docstring in `tools/tts_remote.py` and `tts/examples/`. Knobs: `exaggeration` (more drama and speed), `cfg_weight` (lower = slower, more deliberate), optional `ref_audio` (a ~10 s clip whose timbre to follow; use only your own or generated audio, e.g. `tts/voices/ref_fenrir.wav`), `seed`, per-sentence overrides in `sentences`.

## Timing
`faster-whisper small.en` on the runner, then matched to the script's words (names and numbers keep the script's spelling). `meta.json` records the method.

## Notes
- Every Chatterbox output carries Resemble's imperceptible Perth watermark (stated in its README).
- Provider `mock` (tone, no model) proves the plumbing only.
