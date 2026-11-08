# blender-3d-seal (test style, 2026-11-08)
Blender model (built through the Blender MCP connector, exported as `seal.glb`) rendered headless in Three.js + Chromium (software GL, ~0.9 s per 1080x1920 frame).
Pipeline: script.json -> voice_tools.py request/import -> `python3 mkcfg.py <project>/data` -> `npm i three@0.170.0` -> `node shoot.js <frames dir> 30` -> ffmpeg (narration + original ambient bed, loudnorm -14 LUFS).
The model is a stylised illustration of a Mesopotamian cylinder seal (not a copy of any museum piece); the page labels it "Illustration".
Roll direction, clip planes (impression revealed behind the roll) and the loop pose are in index.html.
