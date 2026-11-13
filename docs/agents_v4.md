# First on Record: agent prompt library (runbook v4)

Proven in the supervised run of 2026-11-12 (Short `20261112-first-gold-coin`). The orchestrator (Opus session) spawns each agent with the Agent tool, `subagent_type: general-purpose`, the `model` shown, and the prompt below with the `<...>` parts filled in. Agents talk through files in a work folder (`W`), then the orchestrator copies the results to `scenes/<slug>/`.

Rules for every agent call
- First line of every prompt: `First line of your reply must be exactly: MODEL: <the model ID stated in your own system prompt, or "unknown">.` Log the answer in `scenes/<slug>/qa/models.json`.
- Blind agents (marked *) get only the files named in their prompt. Never paste upstream opinions or scores.
- Ask for a file as output and a short reply. Read the file, not the reply.
- Web access inside agents is unreliable (Commons, Wikipedia and the Met API were refused; metmuseum.org pages, sardisexpedition.org, university pages worked). The Scout must mark licences it could not see as "unverified"; the Greenlight critic kills those. The real licence gate is `fetch_assets.yml` (tools/assets/fetch.py refuses anything but CC0 / public domain / CC BY).

| # | Agent | Model | Reads | Writes |
|---|---|---|---|---|
| 4 | Scout | sonnet | scout_input.md (vidIQ outliers + used subjects) | slate.json (6 topics) |
| 5 | Greenlight critic * | opus | slate.json | reply: KEEP/KILL per topic, PRODUCE, CLAIM LIMIT |
| 6 | Researcher | sonnet | topic + object + claim limit | dossier.md, claims.json |
| 7 | Fact-checker * | opus | claims.json | factcheck.json (pass / pass_with_fix / fail) |
| 8 | Script writer | opus | writer_brief.md, passed_claims.json, dossier.md | script.json (lines with kind, see, claims; 5 hooks) |
| 9 | Hook panel * x3 | opus, sonnet, haiku | hooks_panel.md | hook_A/B/C.json |
| 10 | Retention editor * | opus | retention_input.md (timed lines + pictures) | retention.json (marks, verdict) |
| 11 | Art director | opus | art_brief.md, script.json, dossier.md | shots_plan.json (palette, cast, 13-18 shots, proof beats) |
| 12 | Image-prompt writer | sonnet | shots_plan.json | shots.json (image lane format) |
| 13 | Image defect screen * | haiku | the stills + reject list | defects.json |
| 14 | Builder | no model | script.json, shots_plan.json, words.json | timeline.json via tools/scene/build_timeline.py, then tools/scene/compose.py |
| 15 | Cold viewer * | haiku | frame0.jpg, first3s.jpg only | cold_viewer.json |
| 16/17 | Preview QA * / Final visual QA * | sonnet / opus | contact sheet + 6 frames + docs/visual_qa_rubric.md | final_qa.json |
| 18 | Packager | sonnet | packager_brief.md, script, passed claims, factcheck | pending.json |
| 19 | Licence / credit checker | haiku | assets manifest.json + pending.json | licence_check.json (also re-check by script) |

The full prompt texts used on 2026-11-12 are kept next to their outputs: `scenes/20261112-first-gold-coin/` (writer_brief.md, and the briefs under `briefs/`). Copy them, change the topic block, keep the rules.

## Lessons from the first run (2026-11-12)
1. Model override works: agents reported claude-opus-5-5, claude-sonnet-5-5 and claude-haiku-5-5 as assigned (interactive session; still to confirm in a scheduled run).
2. Scout (Sonnet) delivered only 1 of 6 topics that survived Greenlight, because it could not open licence pages. Give the Scout a pre-verified pool instead: Met Open Access objects only (the Met collection page shows "Public Domain"), and require the object page URL.
3. Fact-checker (Opus, blind) caught a real error the researcher passed (punch marks on silver coins) and hedged 5 more claims. Keep it on Opus.
4. Hook panel: all three models picked the same hook and ranked the five hooks in the same order (scores 78/88/84). One run is no proof, but the mixed panel did not disagree; keep logging and compare with real 3-second hold later.
5. Retention editor (Opus, fresh each round) returned "send_back" in both rounds: a fresh critic always finds one "high". The cap (2 rounds, then lock) is what ends the loop. Round 1 fixed the real problems (label tone, jargon, hook answered too late); round 2 was about one line.
6. Haiku defect screen on the 15 pilot stills: 7 flagged. Checked by eye: the two flagged with medium/high confidence were real (a hand with two thumbs; a man in boots), and both had been missed by the manual pick the day before. The 5 flagged "low" were vague or misdescribed. Rule: high/medium = re-roll; low = second look by Sonnet before spending GPU time.
7. Final visual QA (Opus, blind) failed the 11 Nov pilot: average 6.2, "not AI slop" 4/10, would scroll past. Its three fixes are now rules for the Art director: end on the real object, never a cartoon copy of it; frame 0 needs a complete thought in the caption; one fixed cast, described word for word in every prompt.
8. Cold viewer (Haiku) is cheap and useful: from 2 images it read the captions and said what was unclear in the first 3 seconds.
9. Quota: the Opus calls of ONE Short's writing chain (greenlight, fact-check, writer x3, retention x2, art director, final QA) plus the orchestrating session ran into the account's 5-hour usage limit once. Four Shorts in one Saturday session will hit it. Plan the week as resumable from the start: S1-S3 for all Shorts first (text only), checkpoint, then S4-S8.
10. Image lanes (free): Hugging Face ZeroGPU without a token gave 3 of 60 images, then "quota exceeded" (needs repo secret HF_TOKEN). Z-Image-Turbo on a Kaggle T4 with whole-model offload runs out of memory. FLUX.2 klein 4B with sequential offload works at about 144 s per image. So: one variant per shot first, re-roll only what the defect screen rejects.

## Reference-image test (2026-11-13, stills only, `scenes/reftest-cast/`)
11. Character references work on FLUX.2 klein (Kaggle T4): one reference still per cast member, passed to later shots with `"refs": ["cast_x"]`. Full-size references run out of memory; the kernel now shrinks them (`ref_max`, default 640). A referenced image takes about 165 s (141 s without).
12. Result (Sonnet check + by eye): face, hair, beard and drawing style carried over in all 4 test shots; the refiner passed in close-up and full-body. The trader's full-body shot FAILED: the reference was waist-up, so the model invented blue trousers and modern shoes.
13. Rules: cast references are FULL-BODY (head to feet, plain background). Every full-body prompt still names the lower garment and footwear ("knee-length tunic, bare legs, leather sandals"). STYLE GATE: no full render and no Opus final review until a 6-still test (2 references + a close-up and a full-body per character) passes one Sonnet consistency check.
