import json, re, sys
SC=json.load(open('script.json'))   # run inside the project dir; script.json may carry: tag, note, pills[{text,line,off,end_off}], source{line,off,text}
W=json.load(open('data/words.json')); L=json.load(open('data/lines.json'))['lines']
def t(s):
    h=int(s//3600); m=int(s%3600//60); x=s%60
    return f"{h}:{m:02d}:{x:05.2f}"
hdr='''[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Cap,DejaVu Sans,92,&H00FFFFFF,&H000000FF,&H00101010,&H80000000,-1,0,0,0,100,100,0,0,1,7,2,2,40,40,380,1
Style: Tag,DejaVu Sans,34,&H00E6E6E6,&H000000FF,&H00101010,&H80000000,-1,0,0,0,100,100,4,0,1,3,1,8,40,40,70,1
Style: Pill,DejaVu Sans,46,&H00101010,&H000000FF,&H0050C8FF,&H0050C8FF,-1,0,0,0,100,100,1,0,3,14,0,8,40,40,260,1
Style: Src,DejaVu Sans,30,&H00D8D8D8,&H000000FF,&H00101010,&H80000000,0,0,0,0,100,100,1,0,1,3,1,2,40,40,150,1
Style: Note,DejaVu Sans,26,&H00B8B8B8,&H000000FF,&H00101010,&H80000000,0,0,0,0,100,100,2,0,1,2,1,2,40,40,70,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
'''
def fit(text, size, bold=True, maxw=1000, spacing=0):
    """percent scale so the text fits maxw px (1080 wide frame): stops captions/source running off the edge (QA 2026-11-10)"""
    plain = re.sub(r'\{[^}]*\}', '', text)
    try:
        from PIL import ImageFont
        f = ImageFont.truetype('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf', size); w = f.getlength(plain)
    except Exception:
        w = len(plain) * size * (0.72 if bold else 0.62)
    w += spacing * len(plain)
    return min(100, int(100 * maxw / max(w, 1)))
GOLD=r'{\c&H3CC8FF&}'; WHITE=r'{\c&HFFFFFF&}'
STOP=set('a the of to in it is and on at for with how do you that this they so but now one an'.split())
ev=[]
dur=json.load(open('data/lines.json'))['duration']
ev.append(f"Dialogue: 0,{t(0)},{t(dur)},Tag,,0,0,0,,{SC.get("series","FIRST ON RECORD")}  ·  {SC.get("tag","")}")
ev.append(f"Dialogue: 0,{t(0)},{t(dur)},Note,,0,0,0,,{SC.get("note","RECONSTRUCTION  ·  NOT TO SCALE")}")
# caption groups: <=3 words, never across lines
for li,l in enumerate(L):
    ws=[w for w in W if w['line']==li]
    groups=[];cur=[]
    for w in ws:
        cur.append(w)
        if len(cur)==3 or re.search(r'[,.?!]$',w['w']): groups.append(cur);cur=[]
    if cur:
        if groups and len(cur)==1 and len(groups[-1])<3: groups[-1]+=cur
        else: groups.append(cur)
    for gi,g in enumerate(groups):
        s=g[0]['s']; e=groups[gi+1][0]['s'] if gi+1<len(groups) else min(l['end']+0.25,g[-1]['e']+0.4)
        words=[re.sub(r'[^A-Za-z0-9\'\-]','',x['w']) for x in g]
        # accent word: longest non-stopword
        cand=[(len(w),i) for i,w in enumerate(words) if w.lower() not in STOP]
        ai=max(cand)[1] if cand else len(words)-1
        txt=' '.join((GOLD+w.upper()+WHITE) if i==ai else w.upper() for i,w in enumerate(words))
        k=fit(txt,92,True,1000)
        ev.append(f"Dialogue: 1,{t(s)},{t(e)},Cap,,0,0,0,,{{\\fad(60,60)\\fscx{int(k*.92)}\\fscy{int(k*.92)}\\t(0,120,\\fscx{k}\\fscy{k})}}{txt}")
def pill(text, s, e):
    k=fit(text,46,True,960,1); ev.append(f"Dialogue: 2,{t(s)},{t(e)},Pill,,0,0,0,,{{\\fad(120,120)\\fscx{k}\\fscy{k}}} {text} ")
T=lambda i:L[i]['start']; E=lambda i:L[i]['end']
for p in SC.get("pills",[]): pill(p["text"], T(p["line"])+p.get("off",0.3), E(p.get("end_line",p["line"]))+p.get("end_off",0.4))
src=SC.get("source")
if src: ev.append(f"Dialogue: 2,{t(T(src['line'])+src.get('off',0.2))},{t(dur)},Src,,0,0,0,,{{\\fad(150,200)\\fscx{fit(src['text'],30,False,1000,1)}\\fscy{fit(src['text'],30,False,1000,1)}}}{src['text']}")
open('cap.ass','w').write(hdr+'\n'.join(ev)+'\n')
print(len(ev),'events')
