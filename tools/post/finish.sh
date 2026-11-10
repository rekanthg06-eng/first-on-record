# usage: bash finish.sh   (run inside the project dir that has script.json, data/, render.mp4; optional music.wav)
set -e
V=render.mp4; D=$(python3 -c "import json;print(json.load(open('data/lines.json'))['duration'])")
python3 "$(dirname "$0")/gen_ass.py"
# loop blend: last 0.5s crossfades to the first frame, grain + vignette, burn captions
ffmpeg -loglevel error -y -i $V -vf "select=eq(n\,0),loop=loop=15:size=1,setpts=N/24/TB,fps=24" -frames:v 12 first.mp4
ffmpeg -loglevel error -y -i $V -i first.mp4 -filter_complex "[0][1]xfade=transition=fade:duration=0.5:offset=$(python3 -c "print(round($D-0.5-0.01,3))"),vignette=PI/5,noise=alls=7:allf=t,subtitles=cap.ass,format=yuv420p[v]" -map "[v]" -r 24 -t $D -c:v libx264 -crf 23 -maxrate 9M -bufsize 18M -preset veryfast vid.mp4
FO=$(python3 -c "print(max(0.1,$D-2.0))")
if [ -s music.wav ]; then
  # generated bed (ACE-Step, music_bed.yml): trim, fade, sit low; sidechain ducking under the voice below
  ffmpeg -loglevel error -y -i music.wav -af "atrim=0:$D,asetpts=N/SR/TB,highpass=f=60,afade=t=in:d=1.0,afade=t=out:st=$FO:d=2.0,volume=0.55" -ar 48000 -ac 2 bed.wav
else
  # fallback bed: soft drone + noise (self-synthesized)
  ffmpeg -loglevel error -y -f lavfi -i "sine=f=98:d=$D" -f lavfi -i "sine=f=147:d=$D" -f lavfi -i "anoisesrc=c=pink:a=0.5:d=$D" -filter_complex "[0]volume=0.5[a];[1]volume=0.3,tremolo=f=0.25:d=0.5[b];[2]lowpass=f=700,volume=0.5[c];[a][b][c]amix=inputs=3:normalize=0,lowpass=f=900,afade=t=in:d=1.5,afade=t=out:st=$(python3 -c "print($D-1.5)"):d=1.5,volume=0.12[bed]" -map "[bed]" -ar 48000 -ac 2 bed.wav
fi
# SFX: a short self-synthesized whoosh + low thump on every pill (cue times from gen_ass.py -> hits.txt)
ffmpeg -loglevel error -y -f lavfi -i "anoisesrc=c=pink:a=0.9:d=0.45" -f lavfi -i "sine=f=62:d=0.35" -filter_complex "[0]highpass=f=500,lowpass=f=5000,afade=t=in:d=0.25,afade=t=out:st=0.25:d=0.2,volume=0.30[w];[1]afade=t=in:d=0.01,afade=t=out:st=0.05:d=0.3,volume=0.55[t];[w][t]amix=inputs=2:normalize=0" -ar 48000 -ac 2 hit.wav
python3 - "$D" <<'PY'
import sys, subprocess
D=float(sys.argv[1]); hits=[float(x) for x in open('hits.txt').read().split()] if __import__('os').path.exists('hits.txt') else []
hits=[h for h in hits if 0 <= h-0.25 < D-0.5]
if not hits:
    subprocess.run(['ffmpeg','-loglevel','error','-y','-f','lavfi','-i',f'anullsrc=r=48000:cl=stereo','-t',str(D),'sfx.wav'],check=True); raise SystemExit
args=['ffmpeg','-loglevel','error','-y']; f=[]
for i,h in enumerate(hits):
    args+=['-i','hit.wav']; ms=int(max(0,h-0.25)*1000); f.append(f'[{i}]adelay={ms}|{ms}[h{i}]')
f.append(''.join(f'[h{i}]' for i in range(len(hits)))+f'amix=inputs={len(hits)}:normalize=0,apad=whole_dur={D}[o]')
subprocess.run(args+['-filter_complex',';'.join(f),'-map','[o]','-t',str(D),'sfx.wav'],check=True)
PY
# mix: voice on top; the bed is ducked by the voice (sidechain); SFX under the voice; loudness -14 LUFS
ffmpeg -loglevel error -y -i data/narration.wav -i bed.wav -i sfx.wav -filter_complex "[0]aresample=48000,apad=whole_dur=$D,pan=stereo|c0=c0|c1=c0,asplit=2[v][sc];[1][sc]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=400[bd];[v][bd][2]amix=inputs=3:normalize=0:weights=1 0.9 0.8,loudnorm=I=-14:TP=-1.5:LRA=7[a]" -map "[a]" -t $D mix.wav
ffmpeg -loglevel error -y -i vid.mp4 -i mix.wav -c:v copy -c:a aac -b:a 192k -shortest final.mp4
ffprobe -v error -show_entries format=duration -of csv=p=0 final.mp4
ffmpeg -i final.mp4 -af loudnorm=I=-14:TP=-1.5:print_format=summary -f null - 2>&1 | grep -E "Input (Integrated|True)"
