#!/usr/bin/env python3
"""Open-source narration for First on Record, run by the tts_voice GitHub Action (free minutes, public repo).

  python tools/tts_remote.py tts/requests/a.json [b.json ...] --out build/tts

Request JSON:
  {"slug": "20261109-clay-seal",
   "provider": "chatterbox" | "mock",
   "text": "The whole narration. Sentences are spoken one pass each.",
   "exaggeration": 0.7,  "cfg_weight": 0.3,        (chatterbox; defaults 0.5 / 0.5. Higher exaggeration = more drama and speed,
                                                     lower cfg_weight = slower, more deliberate pacing)
   "ref_audio": "tts/voices/ref_fenrir.wav",        (optional ~10 s clip whose timbre to use; ONLY your own or generated audio)
   "pause": 0.38, "seed": 7,
   "sentences": [{"text": "...", "exaggeration": 0.9, "cfg_weight": 0.3, "pause": 0.2}]   (optional per-sentence overrides; replaces text)}

Outputs in <out>/<slug>/: voice.wav (24 kHz mono), words.json ([{word,start,end}] on the SCRIPT's words), meta.json.
"mock" needs no model (tone + evenly spread timings) and only proves the plumbing. Every Chatterbox output carries Resemble's
imperceptible Perth watermark (their README).
"""
import argparse, difflib, json, math, re, struct, subprocess, sys, wave
from pathlib import Path

SR = 24000
_cache = {}


def to_wav(src, dst):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(src), '-ac', '1', '-ar', str(SR), '-c:a', 'pcm_s16le', str(dst)], check=True)


def wav_duration(p):
    with wave.open(str(p), 'rb') as w:
        return w.getnframes() / w.getframerate()


def script_words(text):
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9'’-]*|[^\sA-Za-z0-9]+", text)


def norm(w):
    return re.sub(r"[^a-z0-9]", '', w.lower())


def real_words(words):
    return [w for w in words if norm(w)]


def spread(words, duration, lead=0.1, tail=0.15):
    real = real_words(words)
    span = max(0.1, duration - lead - tail); step = span / max(1, len(real)); t = lead; out = []
    for w in real:
        out.append({'word': w, 'start': round(t, 3), 'end': round(t + step * 0.92, 3)}); t += step
    return out


def align_to_script(words, asr):
    """carry ASR word times onto the script's own words (names, numbers and spellings come from the script)."""
    real = real_words(words)
    a = [norm(w) for w in real]; b = [norm(x['word']) for x in asr]
    out = [None] * len(real)
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == 'equal' or (tag == 'replace' and (i2 - i1) == (j2 - j1)):
            for k in range(i2 - i1): out[i1 + k] = (asr[j1 + k]['start'], asr[j1 + k]['end'])
    known = [i for i, v in enumerate(out) if v]
    if not known: return None
    for i in range(len(out)):
        if out[i]: continue
        prev = max([k for k in known if k < i], default=None); nxt = min([k for k in known if k > i], default=None)
        if prev is not None and nxt is not None:      # between two anchors: spread evenly
            t0, t1 = out[prev][1], out[nxt][0]; n = nxt - prev
            out[i] = (t0 + (t1 - t0) * (i - prev) / n, t0 + (t1 - t0) * (i - prev + 0.9) / n)
        elif nxt is not None:                         # before the first anchor
            s = max(0.0, out[nxt][0] - 0.3 * (nxt - i)); out[i] = (s, s + 0.25)
        else:                                         # after the last anchor
            s = out[prev][1] + 0.3 * (i - prev - 1) + 0.05; out[i] = (s, s + 0.25)
    return [{'word': w, 'start': round(s, 3), 'end': round(e, 3)} for w, (s, e) in zip(real, out)]


def whisper_words(wav):
    if 'whisper' not in _cache:
        from faster_whisper import WhisperModel
        _cache['whisper'] = WhisperModel('small.en', device='cpu', compute_type='int8')
    segs, _ = _cache['whisper'].transcribe(str(wav), language='en', word_timestamps=True, vad_filter=False)
    return [{'word': w.word.strip(), 'start': w.start, 'end': w.end} for s in segs for w in (s.words or [])]


def split_sentences(text):
    return [s.strip() for s in re.split(r'(?<=[.!?…])\s+', text.strip()) if s.strip()]


def synth_chatterbox(req, raw):
    import torch, torchaudio
    if 'cb' not in _cache:
        from chatterbox.tts import ChatterboxTTS
        _cache['cb'] = ChatterboxTTS.from_pretrained(device='cpu')
    m = _cache['cb']
    if req.get('seed') is not None: torch.manual_seed(int(req['seed']))
    sents = req.get('sentences') or [{'text': s} for s in split_sentences(req['text'])]
    ex, cfg, gap = float(req.get('exaggeration', 0.5)), float(req.get('cfg_weight', 0.5)), float(req.get('pause', 0.38))
    kw = {'audio_prompt_path': req['ref_audio']} if req.get('ref_audio') else {}
    parts = []
    for s in sents:
        wav = m.generate(s['text'], exaggeration=float(s.get('exaggeration', ex)), cfg_weight=float(s.get('cfg_weight', cfg)), **kw)
        if wav.dim() == 1: wav = wav.unsqueeze(0)
        parts += [wav, torch.zeros(1, int(m.sr * float(s.get('pause', gap))))]
    torchaudio.save(str(raw), torch.cat(parts, dim=1), m.sr)
    return ' '.join(s['text'] for s in sents)


def synth_mock(req, raw):
    n = max(8, len(req['text'].split())); dur = n * 0.33
    with wave.open(str(raw), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(b''.join(struct.pack('<h', int(3000 * math.sin(2 * math.pi * 220 * i / SR))) for i in range(int(dur * SR))))
    return req['text']


def run(path, out):
    req = json.load(open(path)); slug = re.sub(r'[^a-zA-Z0-9_-]', '', req['slug'])
    assert slug and (req.get('text', '').strip() or req.get('sentences')), 'request needs slug and text'
    prov = req.get('provider', 'chatterbox'); outdir = Path(out) / slug; outdir.mkdir(parents=True, exist_ok=True)
    raw = outdir / 'raw.wav'
    spoken = {'chatterbox': synth_chatterbox, 'mock': synth_mock}[prov](req, raw)
    wav = outdir / 'voice.wav'; to_wav(raw, wav); raw.unlink()
    dur = wav_duration(wav); words = script_words(spoken); method = 'spread'
    if prov == 'mock':
        timed = spread(words, dur)
    else:
        try:
            timed = align_to_script(words, whisper_words(wav)); method = 'whisper'
        except Exception as e:
            print('whisper alignment failed, spreading evenly:', e, file=sys.stderr); timed = None
        if timed is None: timed = spread(words, dur); method = 'spread'
    json.dump(timed, open(outdir / 'words.json', 'w'), indent=1)
    meta = {k: req.get(k) for k in ('slug', 'provider', 'exaggeration', 'cfg_weight', 'ref_audio', 'seed')}
    meta.update({'duration_s': round(dur, 3), 'words': len(timed), 'timing': method, 'chars': len(spoken)})
    json.dump(meta, open(outdir / 'meta.json', 'w'), indent=1)
    print(f'{slug}: {prov} {dur:.1f}s, {len(timed)} words, timing={method}', flush=True)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('requests', nargs='+'); ap.add_argument('--out', default='build/tts'); a = ap.parse_args()
    for p in a.requests: run(p, a.out)


if __name__ == '__main__':
    main()
