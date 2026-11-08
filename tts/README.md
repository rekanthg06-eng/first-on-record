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

## Channel voice (locked 2026-11-08)
`tts/voice_profile.json` = the approved Chatterbox take: default voice, a lift on problem lines, a moderate finish, seed 21. Tag script lines with `"kind"` (`P` problem, `H` punch, `F` fix = default, `L1` lead-in, `L2` finish) and use `tools/voice_tools.py`:

    python tools/voice_tools.py request <project> --slug <yyyymmdd-slug>     # -> tts/requests/<slug>.json, push to main
    python tools/voice_tools.py import  <project> voice.wav words.json       # Action output -> data/narration.wav, lines.json, words.json

`import` adds the lead and outro silence, applies the master chain (EQ, compression, limiter; final loudness is still `mix.py`'s job) and writes the same files `voice.py` + `words.py` write, so the rest of the pipeline is unchanged. Chatterbox is stochastic: a different `--seed` gives a different take.
