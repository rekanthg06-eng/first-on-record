# Remote narration (tts_voice workflow)

Why: local Kokoro narration sounds synthetic. A premium voice API fixes that, but the Claude sandbox cannot reach those APIs or hold keys, so the call runs in GitHub Actions.

Flow: the daily run pushes `tts/requests/<slug>.json` to `main` -> Action `tts_voice` -> branch `tts-out` gets `tts/<slug>/voice.wav` (24 kHz mono), `words.json` (word times on the SCRIPT's words) and `meta.json`. The run then fetches it:

    git fetch origin tts-out && git show origin/tts-out:tts/<slug>/voice.wav > voice.wav   # likewise words.json, meta.json

Wait for the run (usually 1-3 min; poll `git fetch origin tts-out` until the slug appears). Only the 6 newest slugs are kept. Slugs start with yyyymmdd.

## Request contract
See `tools/tts_remote.py` and `tts/examples/`. `provider`: `google` (Chirp 3 HD, voices named like `en-US-Chirp3-HD-Fenrir`, `speaking_rate` 0.25-2.0), `elevenlabs` (voice_id, `model`, `voice_settings`; word times come from ElevenLabs' own alignment), or `mock` (tone, no key; proves the plumbing only).

## Secrets (Settings -> Secrets and variables -> Actions)
- `GOOGLE_TTS_API_KEY`: in the same Google Cloud project as SETUP.md, enable **Cloud Text-to-Speech API**, create an API key, restrict it to that API. Billing must be on (it already is if Gemini is set up); Chirp 3 HD has a free tier of 1M characters a month, a Short is about 700.
- `ELEVENLABS_API_KEY`: only if you choose ElevenLabs. A monetized channel needs a plan that includes commercial use.

## Timing method
ElevenLabs: exact, from its character alignment. Google: `faster-whisper small.en` on the runner, then matched to the script's words (names and numbers keep the script's spelling; gaps are interpolated). `meta.json` records which was used.

## Smoke test without keys
Push a request with `"provider": "mock"` (see `tts/requests/20261108-mock-smoke.json`) or run the workflow manually.
