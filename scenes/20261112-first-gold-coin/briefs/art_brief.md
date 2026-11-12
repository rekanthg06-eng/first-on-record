# Art director brief: First on Record Short "20261112-first-gold-coin"
Read: /home/claude/work/v4run/script.json (locked script; each line has a rough "see" note you may overrule) and /home/claude/work/v4run/dossier.md (facts about the object and the setting).

## What the video is
1080x1920 Short, about 33 s. Illustrated story scenes (flat 2D storybook illustration, bold simplified shapes, soft cel shading, paper grain) generated one still per shot by an AI image model, each still animated by the compositor with push/pull, pan and depth parallax. Plus PROOF BEATS that show a real museum photograph: The Met 26.59.2, a Lydian gold stater (oval lump of gold about 1.6 cm long, with the foreparts of a lion, left, facing a bull, right), on a plain dark background. Captions (2-3 big words, upper case, at about 66% of frame height) are added automatically; never design text into the pictures.

## Format rules (hard)
1. 13-18 shots; a visual change at least every 2.5 s; a line longer than 2.5 s gets two shots.
2. Frame 0 is an action already in motion, readable in half a second with the sound off.
3. The picture shows what the line says, line by line.
4. The real coin photo is the PROOF, not the whole video: 3-4 beats of 1-2.5 s each. One must fall inside the first 6 seconds (line 2). The last proof beat carries the chip "THE MET · 26.59.2"; the others "THE REAL COIN". The LAST image of the video should not be a cartoon version of the coin presented as the real thing.
5. One recurring cast so faces do not change between shots: define at most 3 characters (a trader, a refiner, a minter or king) with a fixed, simple, distinctive look each (age, build, hair/beard, clothing colour) that can be repeated word for word in every prompt.
6. Setting must be correct for Lydia (western Anatolia), city of Sardis, about 550 BCE: Iron Age Anatolian/East Greek world. Tunics (chiton-like, knee or ankle length), cloaks, leather sandals or bare feet, beards common, terracotta pots, mudbrick-and-stone houses with tiled or flat roofs, a river (the Pactolus) below a steep acropolis hill. No modern objects, no glasses, no paper money, no books, no written signs or letters anywhere, no machines. Coins are small irregular oval lumps, never perfect modern discs with rims.
7. Known failure modes of the image model to design around: hands with wrong fingers (prefer hands partly closed, holding something, or cropped); crowds of identical people; props drawn as clip-art; duplicate tools; empty filler shots (every shot needs a clear subject filling the upper two thirds); boots/modern shoes.
8. Must differ from the previous Short's look (warm ochre/terracotta Sumerian mudbrick with teal shadows): choose a different palette and light.
9. No shot may reuse the previous shot's framing; alternate close / medium / wide and change angle.

## Output: write /home/claude/work/v4run/shots_plan.json
{"palette": "...", "light": "...", "style_string": "one paragraph of look/palette/medium only (NO people, NO clothing), ending with: No text, no letters, no watermark, no border.",
 "cast": [{"id":"trader","look":"exact reusable description"}, ...],
 "shots": [{"id":"s01_palm","line":1,"type":"illustration"|"real_coin","framing":"extreme close-up|close|medium|wide|top-down","see":"exactly what is in the frame, concrete and drawable, which cast members","motion":"push-in|pull-back|pan-left|pan-right|tilt-up|tilt-down","chip":"only for real_coin shots","crop":"for real_coin shots: which part of the photo (whole coin | lion | bull | whole coin slow pull-back)","share":0.5}]}
"share" = the fraction of that line's spoken duration this shot takes when a line has several shots (shares within one line sum to 1). Shots must be in order and cover every line.
