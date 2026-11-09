set -e
V=render.mp4; D=27.36
# loop blend: last 0.5s crossfades to the first frame, grain + vignette, burn captions
ffmpeg -loglevel error -y -i $V -vf "select=eq(n\,0),loop=loop=15:size=1,setpts=N/24/TB,fps=24" -frames:v 12 first.mp4
ffmpeg -loglevel error -y -i $V -i first.mp4 -filter_complex "[0][1]xfade=transition=fade:duration=0.5:offset=$(python3 -c "print(round($D-0.5-0.01,3))"),vignette=PI/5,noise=alls=7:allf=t,subtitles=cap.ass,format=yuv420p[v]" -map "[v]" -r 24 -t $D -c:v libx264 -crf 17 -preset veryfast vid.mp4
# bed: soft drone + noise
ffmpeg -loglevel error -y -f lavfi -i "sine=f=98:d=$D" -f lavfi -i "sine=f=147:d=$D" -f lavfi -i "anoisesrc=c=pink:a=0.5:d=$D" -filter_complex "[0]volume=0.5[a];[1]volume=0.3,tremolo=f=0.25:d=0.5[b];[2]lowpass=f=700,volume=0.5[c];[a][b][c]amix=inputs=3:normalize=0,lowpass=f=900,afade=t=in:d=1.5,afade=t=out:st=$(python3 -c "print($D-1.5)"):d=1.5,volume=0.12[bed]" -map "[bed]" -ar 48000 -ac 2 bed.wav
ffmpeg -loglevel error -y -i data/narration.wav -i bed.wav -filter_complex "[0]aresample=48000,apad=whole_dur=$D,pan=stereo|c0=c0|c1=c0[v];[v][1]amix=inputs=2:normalize=0:weights=1 0.9,loudnorm=I=-14:TP=-1.5:LRA=7[a]" -map "[a]" -t $D mix.wav
ffmpeg -loglevel error -y -i vid.mp4 -i mix.wav -c:v copy -c:a aac -b:a 192k -shortest final.mp4
ffprobe -v error -show_entries format=duration -of csv=p=0 final.mp4
ffmpeg -i final.mp4 -af loudnorm=I=-14:TP=-1.5:print_format=summary -f null - 2>&1 | grep -E "Input (Integrated|True)"
