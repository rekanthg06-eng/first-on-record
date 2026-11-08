#!/usr/bin/env python3
"""Remote narration for First on Record, run by the tts_voice GitHub Action (or locally with keys in the env).

  python tools/tts_remote.py tts/requests/<slug>.json --out build/tts

Request JSON:
  {"slug": "20261109-clay-seal",
   "provider": "google" | "elevenlabs" | "mock",
   "voice": "en-US-Chirp3-HD-Fenrir"            (google voice name)  |  "<voice_id>" (elevenlabs),
   "model": "eleven_multilingual_v2",           (elevenlabs only, optional)
   "speaking_rate": 1.0,                        (google only, 0.25-2.0)
   "voice_settings": {"stability": 0.4, ...},   (elevenlabs only, optional)
   "text": "The whole narration, exactly as it should be spoken."}

Outputs in <out>/<slug>/: voice.wav (24 kHz mono), words.json ([{word,start,end}] using the SCRIPT's words), meta.json.
Keys come from env: GOOGLE_TTS_API_KEY, ELEVENLABS_API_KEY. "mock" needs no key (tone + evenly spread timings) and only
proves the plumbing.
"""
import argparse, base64, difflib, json, math, os, re, struct, subprocess, sys, urllib.request, wave
from pathlib import Path

SR = 24000


def http_json(url, body, headers):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json', **headers}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit(f'{url.split("?")[0]} -> HTTP {e.code}: {e.read().decode()[:400]}')


def to_wav(src, dst):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(src), '-ac', '1', '-ar', str(SR), '-c:a', 'pcm_s16le', str(dst)], check=True)


def wav_duration(p):
    with wave.open(str(p), 'rb') as w:
        return w.getnframes() / w.getframerate()


def script_words(text):
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9'’-]*|[^\sA-Za-z0-9]+", text)  # keeps punctuation tokens separate


def norm(w):
    return re.sub(r"[^a-z0-9]", '', w.lower())


def spread(words, duration, lead=0.1, tail=0.15):
    """even timing fallback"""
    real = [w for w in words if norm(w)]
    span = max(0.1, duration - lead - tail); step = span / max(1, len(real)); t = lead; out = []
    for w in real:
        out.append({'word': w, 'start': round(t, 3), 'end': round(t + step * 0.92, 3)}); t += step
    return out


def align_to_script(words, asr):
    """carry ASR word times onto the script's own words (numbers, names and spellings come from the script)."""
    real = [w for w in words if norm(w)]
    a = [norm(w) for w in real]; b = [norm(x['word']) for x in asr]
    out = [None] * len(real)
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == 'equal':
            for k in range(i2 - i1): out[i1 + k] = (asr[j1 + k]['start'], asr[j1 + k]['end'])
        elif tag == 'replace' and (i2 - i1) == (j2 - j1):
            for k in range(i2 - i1): out[i1 + k] = (asr[j1 + k]['start'], asr[j1 + k]['end'])
    # interpolate gaps between known anchors
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


def eleven_words(words, alignment):
    """exact word times from ElevenLabs character alignment"""
    chars = alignment['characters']; st = alignment['character_start_times_seconds']; en = alignment['character_end_times_seconds']
    out, cur, s0, e0 = [], '', None, None
    for c, s, e in zip(chars, st, en):
        if c.isspace():
            if cur: out.append({'word': cur, 'start': round(s0, 3), 'end': round(e0, 3)}); cur = ''
        else:
            if not cur: s0 = s
            cur += c; e0 = e
    if cur: out.append({'word': cur, 'start': round(s0, 3), 'end': round(e0, 3)})
    return [w for w in out if norm(w['word'])]


def whisper_words(wav):
    from faster_whisper import WhisperModel
    m = WhisperModel('small.en', device='cpu', compute_type='int8')
    segs, _ = m.transcribe(str(wav), language='en', word_timestamps=True, vad_filter=False)
    return [{'word': w.word.strip(), 'start': w.start, 'end': w.end} for s in segs for w in (s.words or [])]


def synth_google(req, raw):
    key = os.environ.get('GOOGLE_TTS_API_KEY') or sys.exit('GOOGLE_TTS_API_KEY is not set')
    name = req['voice']; lang = '-'.join(name.split('-')[:2])  # en-US-Chirp3-HD-Fenrir -> en-US
    assert len(req['text'].encode()) < 4500, 'text too long for one request'
    body = {'input': {'text': req['text']}, 'voice': {'languageCode': lang, 'name': name},
            'audioConfig': {'audioEncoding': 'LINEAR16', 'speakingRate': float(req.get('speaking_rate', 1.0))}}
    r = http_json('https://texttospeech.googleapis.com/v1/text:synthesize', body, {'X-Goog-Api-Key': key})
    Path(raw).write_bytes(base64.b64decode(r['audioContent'])); return None


def synth_eleven(req, raw):
    key = os.environ.get('ELEVENLABS_API_KEY') or sys.exit('ELEVENLABS_API_KEY is not set')
    body = {'text': req['text'], 'model_id': req.get('model', 'eleven_multilingual_v2')}
    if req.get('voice_settings'): body['voice_settings'] = req['voice_settings']
    r = http_json(f"https://api.elevenlabs.io/v1/text-to-speech/{req['voice']}/with-timestamps?output_format=mp3_44100_128", body, {'xi-api-key': key})
    Path(raw).write_bytes(base64.b64decode(r['audio_base64'])); return r.get('alignment')


def synth_mock(req, raw):
    n = max(8, len(req['text'].split())); dur = n * 0.33
    with wave.open(str(raw), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(b''.join(struct.pack('<h', int(3000 * math.sin(2 * math.pi * 220 * i / SR))) for i in range(int(dur * SR))))
    return None


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('request'); ap.add_argument('--out', default='build/tts'); a = ap.parse_args()
    req = json.load(open(a.request)); slug = re.sub(r'[^a-zA-Z0-9_-]', '', req['slug'])
    assert slug and req.get('text', '').strip(), 'request needs slug and text'
    prov = req.get('provider', 'google'); outdir = Path(a.out) / slug; outdir.mkdir(parents=True, exist_ok=True)
    raw = outdir / ('raw.mp3' if prov == 'elevenlabs' else 'raw.wav')
    alignment = {'google': synth_google, 'elevenlabs': synth_eleven, 'mock': synth_mock}[prov](req, raw)
    wav = outdir / 'voice.wav'; to_wav(raw, wav); raw.unlink()
    dur = wav_duration(wav); words = script_words(req['text']); method = 'spread'
    if prov == 'mock':
        timed = spread(words, dur)
    else:
        timed = None
        if prov == 'elevenlabs' and alignment:
            ew = eleven_words(words, alignment)
            if len(ew) == len([w for w in words if norm(w)]):
                timed = [{'word': w, 'start': x['start'], 'end': x['end']} for w, x in zip([w for w in words if norm(w)], ew)]; method = 'elevenlabs-alignment'
        if timed is None:
            try:
                timed = align_to_script(words, whisper_words(wav)); method = 'whisper'
            except Exception as e:
                print('whisper alignment failed, spreading evenly:', e, file=sys.stderr); timed = None
        if timed is None: timed = spread(words, dur); method = 'spread'
    json.dump(timed, open(outdir / 'words.json', 'w'), indent=1)
    json.dump({'slug': slug, 'provider': prov, 'voice': req.get('voice'), 'duration_s': round(dur, 3), 'words': len(timed), 'timing': method,
               'chars': len(req['text'])}, open(outdir / 'meta.json', 'w'), indent=1)
    print(f'{slug}: {prov} {dur:.1f}s, {len(timed)} words, timing={method}')


if __name__ == '__main__':
    main()
