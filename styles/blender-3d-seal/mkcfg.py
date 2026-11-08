import json,sys,re
# usage: mkcfg.py [data_dir]  (data_dir has lines.json + words.json from voice_tools import); else synthetic timings
S=json.load(open('../script.json'))
if len(sys.argv)>1:
    d=sys.argv[1]; L=json.load(open(d+'/lines.json')); W=json.load(open(d+'/words.json'))
    cfg={'duration':L['duration'],'tag':S['tag'],'lines':[{'start':l['start'],'end':l['end']} for l in L['lines']],'words':W}
else:
    t=0.4; lines=[]; words=[]
    for i,l in enumerate(S['lines']):
        toks=l['text'].split(); st=t
        for w in toks: words.append({'w':w,'line':i,'s':round(t,3),'e':round(t+0.3,3)}); t+=0.36
        lines.append({'start':st,'end':t}); t+=0.35
    cfg={'duration':round(t+0.9,2),'tag':S['tag'],'lines':lines,'words':words}
json.dump(cfg,open('cfg.json','w'),indent=1); print(cfg['duration'],len(cfg['words']))
