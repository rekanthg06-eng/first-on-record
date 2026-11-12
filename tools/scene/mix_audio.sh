#!/usr/bin/env bash
# Scene-route audio (runbook v4, no model): voice (mastered) + optional music bed ducked under speech,
# final -14 LUFS and true peak <= -1.5 dBTP measured AFTER the AAC encode.
# Usage: mix_audio.sh <voice.wav> <out.m4a> [music.wav] [tail_seconds=0.6]
set -euo pipefail
voice="$1"; out="$2"; music="${3:-}"; tail="${4:-0.6}"
here="$(cd "$(dirname "$0")" && pwd)"; tmp="$(mktemp -d)"
master=$(python3 -c "import json;print(json.load(open('$here/../../tts/voice_profile.json'))['master'])")
ffmpeg -v error -y -i "$voice" -af "$master" -ar 48000 "$tmp/v.wav"
dur=$(python3 -c "import subprocess;print(float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0','$tmp/v.wav']))+$tail)")
if [ -n "$music" ]; then
  fo=$(python3 -c "print($dur-1.0)")
  ffmpeg -v error -y -i "$tmp/v.wav" -i "$music" -filter_complex "[0:a]aformat=channel_layouts=stereo,apad=pad_dur=$tail,asplit=2[v1][v2];[1:a]afade=t=in:d=0.4,afade=t=out:st=$fo:d=0.8,volume=0.5[m];[m][v1]sidechaincompress=threshold=0.03:ratio=6:attack=15:release=350[md];[v2][md]amix=inputs=2:duration=first:weights='1 0.45':normalize=0" -ar 48000 -t "$dur" "$tmp/pre.wav"
else
  ffmpeg -v error -y -i "$tmp/v.wav" -af "aformat=channel_layouts=stereo,apad=pad_dur=$tail" -ar 48000 -t "$dur" "$tmp/pre.wav"
fi
I=$(ffmpeg -nostats -i "$tmp/pre.wav" -filter_complex ebur128 -f null - 2>&1 | grep " I:" | tail -1 | awk '{print $2}')
G=$(python3 -c "print(round(-14.0-($I),2))")
ffmpeg -v error -y -i "$tmp/pre.wav" -af "volume=${G}dB,alimiter=limit=0.75:level=false:attack=3:release=60" -ar 48000 -c:a aac -b:a 192k "$out"
ffmpeg -nostats -i "$out" -filter_complex ebur128=peak=true -f null - 2>&1 | grep -E " I:|Peak:" | tail -2
rm -rf "$tmp"
