# Epic Frame: flat-vector Indian-epic look (First on Record)

Built to match the "epic story reel" family (warm saffron/maroon dusk skies, flat vector figures, gold arch frame, series header, counter hook, kinetic gold-accent captions, soft crossfades). Original art in code; no third-party assets.

## Look rules
- Palette: dusk maroon `#3A1620` -> burnt orange `#C0602F` skies, gold `#E8B84A`, lapis `#2E5AA8`, cream `#EEE2C4`, hair `#1C1210`. Danger = crimson. Flat fills, only soft gradients in sky; no outlines on figures.
- Fixed layer: header "FIRST ON RECORD" + `script.series`/`script.tag` at y 250-310. Keep faces/key objects in y 330-1250. Captions at y 1330 (124 px, max width 880, squeeze 0.84), 1-3 words, ONE gold word (`*`), white with dark maroon stroke.
- Shots crossfade (XF = 0.32 s); `hard:true` gives a flash cut. Cut = `L(i) - 0.08` so the picture changes just before its line.
- Hook shot = sky + sun + counter (`K.counter` counts up, `K.ribbon` label). Loop: last shot returns to the hook scene.

## Engine (same as faceless-shorts)
`node tools/capture.mjs check | cues | sheet | frames | video`, `tools/mix.py` (procedural score + SFX), `src/shots.js` returns `{shots, cues}`. Voice: `voice.py` then `tools/kokoro_words.py` (repo tools/) for word timing.

## Kit map (src/core/kit.js)
Scenery: sky, sunDisc, moon, stars, hills, haze, clouds, ziggurat, pyramid, palm, arch, pillar, hall, vignette, lightning, dust.
People: `figure({x,y,s,dress,cloth,trim,beard,beardCol,hat,hatCol,skin,armL,armR,eyes,mouth,brow,look,tilt,t})`, `ARM` poses + `armPose(a,b,k)`, `handPos`, `crowd`.
Props: tablet, ingot, silver, pedestal, spotlight, stamp, angerMarks, speedLines.
Text: counter, ribbon, tag, stamp.

## Shot anatomy
One idea per shot, one motion (slide-in, shake, pop), one sound cue on the key word (`Wd('word', line)`). 8 shots for ~20 s; 10-14 for 30 s.

## QA pitfalls found
- Angry brows must slope DOWN toward the nose (sign was inverted once).
- Header must not touch the arch/sun: keep arch top >= y 400.
- Clouds: draw as ONE path fill, else overlap rings show.
- Anything in y 1250-1550 collides with captions.
- Sample (Ea-nasir test): 1080x1920, 30 fps, 19.8 s, 7.5 MB, -15 LUFS, render ~31 s on cloud CPU.

## Problem-chain shot pattern (build-up reels)
For process/use stories (see runbook "PROBLEM CHAIN"): keep ONE central scene/object that accumulates a part per fix.
- Beat = problem shot (the danger/need, caption on the problem word) -> fix shot (a new part slides/pops in with a `pop` cue on the fix word) -> next problem appears (weather, animal, crowd, fire, flood: `K.speedLines`, `K.angerMarks`, rain/dust overlays).
- Reuse the same camera framing across beats (small zoom/pan only) so the viewer sees the object grow; cut every 2-3 s inside a beat with `cam` changes.
- Callouts: one bold card per video (`K.tag` / `K.stamp`), e.g. a number, a height, a name.
- Last shot: the finished object surviving the last problem, then return to the hook scene for the loop.
Reference: jungle-hut reel (bed -> scorpions -> platform -> rain -> roof -> snakes -> 10 ft + ladder -> flood -> survives).
