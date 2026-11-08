#!/usr/bin/env python3
"""Find real, reusable images of a museum object on Wikimedia Commons, with the license recorded.
Runs on a GitHub runner (the sandbox cannot reach commons.wikimedia.org); see .github/workflows/object_images.yml.

  python tools/commons_images.py "Ea-nasir complaint tablet" --out build/img/ea-nasir [--limit 8] [--width 1200]

Accepts ONLY: public domain, CC0, CC BY (any version; attribution text is written to credits.txt). Everything else
(CC BY-SA, NC, ND, 'fair use', unknown) is skipped, so nothing here forces share-alike or needs a lawyer.
Caveat that stays with the human gate: a photo of a 3D object can carry the photographer's copyright, so we trust
Commons' own license field and still show the attribution line when one is required.
Output: <out>/manifest.json (kept + skipped with reasons), <out>/credits.txt, <out>/NN-<name>.jpg
"""
import argparse, html, json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

API = 'https://commons.wikimedia.org/w/api.php'
UA = 'FirstOnRecordBot/1.0 (https://github.com/rekanthg06-eng/first-on-record; educational history channel)'
OK_PD = re.compile(r'^(public domain|pd\b|pd-|cc0|cc-zero|no restrictions|pdm)', re.I)
OK_BY = re.compile(r'^cc[ -]by[ -]\d', re.I)          # "CC BY 4.0", "CC-BY-3.0" (SA/NC/ND variants fail the next test)
BAD = re.compile(r'(-sa\b| sa\b|-nc|\bnc\b|-nd|\bnd\b|fair use|non-?commercial|no derivs|share ?alike)', re.I)
IMG_MIME = {'image/jpeg', 'image/png', 'image/webp'}


def clean(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', s or ''))).strip()


def classify(meta):
    """-> (kind, license, why). kind in 'pd' | 'by' | None"""
    g = lambda k: clean((meta.get(k) or {}).get('value', ''))
    lic = g('LicenseShortName') or g('License'); terms = g('UsageTerms')
    text = f'{lic} {terms}'.strip()
    if not lic: return None, '', 'no license field'
    if BAD.search(text): return None, lic, 'share-alike / non-commercial / no-derivatives / fair use'
    if g('Restrictions') and g('Restrictions').lower() not in ('', 'personality rights'): return None, lic, f'restrictions: {g("Restrictions")}'
    if OK_PD.search(lic) or g('Copyrighted').lower() == 'false': return 'pd', lic, ''
    if OK_BY.search(lic): return 'by', lic, ''
    return None, lic, 'license not on the accepted list'


def get(url, params=None, binary=False):
    if params: url += '?' + urllib.parse.urlencode(params)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=60) as r:
                data = r.read()
            return data if binary else json.loads(data)
        except Exception as e:
            if attempt == 3: raise
            time.sleep(2 + 3 * attempt)


def search(query, limit, width):
    p = {'action': 'query', 'format': 'json', 'generator': 'search', 'gsrsearch': f'{query} filetype:bitmap', 'gsrnamespace': 6,
         'gsrlimit': limit, 'prop': 'imageinfo', 'iiprop': 'url|size|mime|extmetadata', 'iiurlwidth': width,
         'iiextmetadatafilter': 'LicenseShortName|License|UsageTerms|Copyrighted|Restrictions|Artist|Credit|ImageDescription|AttributionRequired|DateTimeOriginal|ObjectName'}
    pages = (get(API, p).get('query') or {}).get('pages') or {}
    return sorted(pages.values(), key=lambda x: x.get('index', 0))


def build(pages, min_side=700):
    kept, skipped = [], []
    for pg in pages:
        ii = (pg.get('imageinfo') or [None])[0]; title = pg.get('title', '')
        if not ii: skipped.append({'title': title, 'why': 'no imageinfo'}); continue
        kind, lic, why = classify(ii.get('extmetadata') or {})
        if ii.get('mime') not in IMG_MIME: why = why or f'mime {ii.get("mime")}'; kind = None
        if min(ii.get('width', 0), ii.get('height', 0)) < min_side: why = why or 'too small'; kind = None
        if not kind: skipped.append({'title': title, 'license': lic, 'why': why}); continue
        m = ii['extmetadata']; artist = clean((m.get('Artist') or {}).get('value')); credit = clean((m.get('Credit') or {}).get('value'))
        kept.append({'title': title, 'page': ii.get('descriptionurl'), 'url': ii.get('thumburl') or ii['url'], 'orig': ii['url'],
                     'w': ii.get('thumbwidth') or ii['width'], 'h': ii.get('thumbheight') or ii['height'], 'license': lic, 'kind': kind,
                     'artist': artist, 'credit': credit, 'desc': clean((m.get('ImageDescription') or {}).get('value'))[:300],
                     'attribution': f'{artist or "Unknown"} / Wikimedia Commons / {lic}' if kind == 'by' else f'{artist or credit or "Wikimedia Commons"} / Wikimedia Commons / {lic}'})
    return kept, skipped


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('query'); ap.add_argument('--out', required=True)
    ap.add_argument('--limit', type=int, default=8); ap.add_argument('--width', type=int, default=1200)
    ap.add_argument('--fixture', help='offline test: a saved API json instead of the network')
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    pages = (json.load(open(a.fixture)).get('query') or {}).get('pages', {}).values() if a.fixture else search(a.query, a.limit, a.width)
    kept, skipped = build(sorted(pages, key=lambda x: x.get('index', 0)))
    for n, k in enumerate(kept, 1):
        name = f'{n:02d}-' + re.sub(r'[^a-z0-9]+', '-', re.sub(r'^File:|\.\w+$', '', k['title'], flags=re.I).lower()).strip('-')[:50] + '.jpg'
        k['file'] = name
        if not a.fixture: (out / name).write_bytes(get(k['url'], binary=True))
    (out / 'manifest.json').write_text(json.dumps({'query': a.query, 'kept': kept, 'skipped': skipped}, indent=1, ensure_ascii=False))
    (out / 'credits.txt').write_text('\n'.join(f'{k["file"]}: {k["attribution"]} ({k["page"]})' for k in kept if k['kind'] == 'by') + '\n')
    print(f'{a.query!r}: kept {len(kept)} (pd {sum(k["kind"]=="pd" for k in kept)}, by {sum(k["kind"]=="by" for k in kept)}), skipped {len(skipped)}')
    for s in skipped: print('  skip', s['title'], '-', s['why'], f'[{s.get("license","")}]')


if __name__ == '__main__':
    main()
