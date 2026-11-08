#!/usr/bin/env python3
"""Channel voice, step 1 and step 2. Needs only python3 + numpy/scipy + ffmpeg (the faceless-shorts venv has them).

  python tools/voice_tools.py request <project> --slug 20261109-clay-seal [--seed 21] [--out tts/requests]
      script.json lines -> tts/requests/<slug>.json (one sentence per Chatterbox pass, emphasis from tts/voice_profile.json).
      Tag a line with "kind": "P" problem | "H" punch | "F" fix (default) | "L1" lead-in | "L2" finish.
      Lines are grouped into sentences the way voice.py does (a line ending . ? ! closes one; "break": true forces a close).
      Push the request to main; the tts_voice Action writes tts/<slug>/{voice.wav,words.json,meta.json} to branch tts-out.

  python tools/voice_tools.py import <project> voice.wav words.json
      Action output -> <project>/data/narration.wav (lead + master chain + outro), data/lines.json, data/words.json
      [{w,line,s,e}], data/words.txt: the same files voice.py + words.py write, so shots, captions and mix.py work unchanged.
"""
import argparse, json, re, subprocess, sys, wave
from pathlib import Path
import numpy as np
from scipy.io import wavfile

SR = 24000
PROFILE = Path(__file__).resolve().parent.parent / 'tts' / 'voice_profile.json'


def norm(w):
    return re.sub(r'[^a-z0-9]', '', w.lower())


def script_words(text):                      # must match tools/tts_remote.py
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9'’-]*|[^\sA-Za-z0-9]+", text)


def real_words(text):
    return [w for w in script_words(text) if norm(w)]


def groups(lines):
    out, cur = [], []
    for i, ln in enumerate(lines):
        cur.append(i)
        if re.search(r'[.?!]["\')]*$', ln['text'].strip()) or ln.get('break') or i == len(lines) - 1:
            out.append(cur); cur = []
    return out


def cmd_request(a):
    prof = json.load(open(PROFILE)); S = json.load(open(Path(a.project) / 'script.json'))
    sents = []
    for g in groups(S['lines']):
        kind = next((S['lines'][i]['kind'] for i in g if S['lines'][i].get('kind')), 'F')
        if kind not in prof['kinds']: sys.exit(f'unknown kind {kind!r} (use {list(prof["kinds"])})')
        k = prof['kinds'][kind]; gap = S['lines'][g[-1]].get('gap')
        sents.append({'text': ' '.join(S['lines'][i]['text'].strip() for i in g), 'exaggeration': k['exaggeration'],
                      'cfg_weight': k['cfg_weight'], 'pause': float(gap) if gap is not None else k['pause'], 'kind': kind})
    sents[-1]['pause'] = 0.0
    req = {'slug': a.slug, 'provider': prof['provider'], 'seed': a.seed if a.seed is not None else prof['seed'], 'sentences': sents}
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True); p = out / f'{a.slug}.json'
    p.write_text(json.dumps(req, indent=1)); print(f'{p}: {len(sents)} sentences, kinds {"".join(s["kind"][0] for s in sents)}, seed {req["seed"]}')


def cmd_import(a):
    P = Path(a.project); S = json.load(open(P / 'script.json')); prof = json.load(open(PROFILE))
    timed = json.load(open(a.words)); lead = float(S.get('lead', 0.4)); outro = float(S.get('outro', 0.9))
    lines = S['lines']; counts = [len(real_words(ln['text'])) for ln in lines]
    if sum(counts) != len(timed):
        sys.exit(f'word count mismatch: script has {sum(counts)}, words.json has {len(timed)}. The request must come from this script.json.')
    (P / 'data').mkdir(exist_ok=True)
    # narration: lead silence + voice (master chain) + outro silence, peak-normalised like voice.py
    tmp = P / 'data' / '_voice_master.wav'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', a.voice, '-af', prof['master'], '-ac', '1', '-ar', str(SR), '-c:a', 'pcm_s16le', str(tmp)], check=True)
    sr, v = wavfile.read(tmp); tmp.unlink(); v = v.astype(np.float64) / 32768
    y = np.concatenate([np.zeros(int(lead * SR)), v, np.zeros(int(outro * SR))]); y = y / (np.abs(y).max() + 1e-9) * 0.9
    wavfile.write(P / 'data/narration.wav', SR, (y * 32767).astype(np.int16)); dur = len(y) / SR
    # words.json [{w,line,s,e}]: script tokens (split on spaces, punctuation kept) timed from the aligned words of the same line
    words, lns, pos = [], [], 0
    for i, ln in enumerate(lines):
        seg = timed[pos:pos + counts[i]]; pos += counts[i]
        toks = [w for w in ln['text'].split() if norm(w)]
        if not seg: sys.exit(f'line {i} has no words')
        t0, t1 = seg[0]['start'], seg[-1]['end']
        for k, w in enumerate(toks):
            if len(toks) == len(seg): s, e = seg[k]['start'], seg[k]['end']
            else: step = (t1 - t0) / len(toks); s, e = t0 + k * step, t0 + (k + 0.92) * step   # tokenisation differs (e.g. 3,700): spread inside the line
            words.append({'w': w, 'line': i, 's': round(s + lead, 3), 'e': round(e + lead, 3)})
        lns.append({'i': i, 'text': ln['text'], 'start': round(t0 + lead, 3), 'end': round(t1 + lead, 3)})
    for g in groups(lines):                      # inside a sentence a line holds until the next one starts
        for i, j in zip(g, g[1:]): lns[i]['end'] = lns[j]['start']
    (P / 'data/words.json').write_text(json.dumps(words, indent=1))
    (P / 'data/words.txt').write_text('\n'.join(f"{w['s']:7.2f} {w['e']:7.2f}  L{w['line']:<2d} {w['w']}" for w in words))
    (P / 'data/lines.json').write_text(json.dumps({'duration': round(dur, 3), 'voice': prof['name'], 'speed': 1.0, 'lines': lns}, indent=1))
    print(f'data/narration.wav {dur:.2f}s, {len(words)} words, {len(lns)} lines ({prof["name"]})')


def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest='cmd', required=True)
    r = sp.add_parser('request'); r.add_argument('project'); r.add_argument('--slug', required=True); r.add_argument('--seed', type=int); r.add_argument('--out', default='tts/requests')
    i = sp.add_parser('import'); i.add_argument('project'); i.add_argument('voice'); i.add_argument('words')
    a = ap.parse_args(); {'request': cmd_request, 'import': cmd_import}[a.cmd](a)


if __name__ == '__main__':
    main()
