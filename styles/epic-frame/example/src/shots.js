// THE OLDEST CUSTOMER COMPLAINT ON RECORD (Epic Frame style test): the shot list.
// A shot: { id, at, cam: [cx, cy], zoom, hard?, note, draw(lt, d, t) } · lt = time in shot, d = shot length, t = film time.
// Shots crossfade into each other (0.32 s); `hard: true` makes a flash cut. Cut = L(i) - 0.08 (picture changes just before its line).
// Keep faces and key objects between y 330 and 1250: header sits at y 250-310, captions at y 1330.
import { ctx, C, W, H, clamp, lerp, seg, eo, eio, eob, rnd } from './core/lib.js';
import { L, Le, Wd, T } from './core/timing.js';
import * as K from './core/kit.js';

const NANNI = { dress: 'mesop', cloth: C.lapis, trim: C.gold, beard: 'long', beardCol: C.hair, hat: 'cap', hatCol: C.cream, skin: 'M' };

export function buildShots() {
  const S = [], CUES = [];
  const add = (o) => (S.push(o), o);
  const cue = (t, type, o = {}) => CUES.push({ t: +t.toFixed(3), type, ...o });
  const cut = (i) => (i === 0 ? 0 : L(i) - 0.08);

  // ── 1 · HOOK: dawn over Ur, the number counts up ────────────────────────
  const s2 = Wd('man', 0) - 0.12;
  add({ id: 'S01', at: 0, cam: [540, 800], zoom: 0.1, note: 'dawn, ziggurat, counter 0 → 3,700 YEARS AGO',
    draw(lt, d, t) {
      K.sky('dawn'); K.sunDisc(540, 640 + Math.max(0, 40 - lt * 30), 150, { glowA: 0.7 }); K.clouds(t, 480);
      K.hills(1250, 120, '#C47038', t, 12, 1); K.ziggurat(300, 1230, 0.85, '#7A3A2C', '#9A4A34'); K.hills(1380, 110, '#8F3F2E', t, 22, 2.4); K.palm(840, 1440, 1.1, '#4A1E26', t); K.palm(930, 1470, 0.8, '#4A1E26', t + 1);
      K.hills(1560, 90, '#5A2230', t, 36, 4.1); K.haze(1250, 160, '#FFD79A', 0.25);
      K.counter(540, 720, eo(seg(lt, 0.05, 1.5)) * 3700, 210, clamp(lt / 0.15), '');
      const a = eob(seg(lt, 1.5, 1.8)); if (a > 0) K.ribbon('YEARS AGO', 540, 900, 64, a, a);
    } });
  cue(0, 'whoosh', { gain: 0.5 }); cue(1.5, 'thud'); cue(1.6, 'pop', { gain: 0.5 });

  // ── 2 · a man in Ur pays with silver ────────────────────────────────────
  {
    add({ id: 'S02', at: s2, cam: [440, 900], zoom: 0.08, note: 'hall, Nanni offers silver',
      draw(lt, d, t) {
        K.hall(t); K.dust(t, 18);
        const slide = eo(seg(lt, 0, 0.5)), o = { x: lerp(260, 400, slide), y: 1060, s: 1.02, ...NANNI, armR: K.armPose(K.ARM.rest, K.ARM.present, eio(seg(lt, 0.2, 0.7))), mouth: 'smile', t };
        const [hx, hy] = K.handPos(o, 'R'); K.figure({ ...o, holdR: (x, y) => K.silver(x + 10, y - 20, 0.9, 0.3) });
        const k = eob(seg(lt, 0.9, 1.3)); if (k > 0) { K.ingot(820, 820 + (1 - k) * 200, 1.0 * k, -0.12, 'fine'); }
      } });
    cue(s2, 'whoosh', { gain: 0.5 }); cue(s2 + 0.9, 'pop', { gain: 0.6 });
  }

  // ── 3 · and got bad copper instead ──────────────────────────────────────
  {
    const st = cut(1), bad = Wd('bad', 1) - st;
    add({ id: 'S03', at: st, cam: [600, 900], zoom: 0.1, note: 'copper turns green and cracked, Nanni shocked',
      draw(lt, d, t) {
        K.hall(t, {}); K.dust(t, 14);
        const shocked = lt > bad, sh = shocked ? Math.sin(lt * 60) * 5 * Math.max(0, 1 - (lt - bad) * 2.2) : 0;
        K.figure({ x: 330 + sh, y: 1060, s: 1.0, ...NANNI, armR: K.ARM.rest, armL: shocked ? K.ARM.guard : K.ARM.down, eyes: shocked ? 'wide' : 'n', mouth: shocked ? 'o' : 'smile', brow: shocked ? 1 : 0, look: 1, t });
        const flip = clamp((lt - bad) / 0.18), sc = 1.25 * (1 + 0.12 * Math.sin(flip * Math.PI));
        K.ingot(790, 860, sc, -0.12 + sh * 0.01, lt > bad + 0.05 ? 'bad' : 'fine');
        if (shocked) K.speedLines(790, 860, clamp(1 - (lt - bad) * 1.6));
      } });
    cue(st, 'whoosh', { gain: 0.5 }); cue(st + bad, 'boing', { gain: 0.5 }); cue(st + bad + 0.05, 'thud', { gain: 0.6 });
  }

  // ── 4 · so he did what anyone would do ──────────────────────────────────
  {
    const st = cut(2), any = Wd('anyone', 2) - st;
    add({ id: 'S04', at: st, cam: [540, 800], zoom: 0.12, note: 'Nanni furious, anger marks',
      draw(lt, d, t) {
        K.sky('dusk'); K.sunDisc(820, 560, 120, { glowA: 0.5, color: '#F4A24E' }); K.hills(1300, 110, '#7A2E36', t, 14, 3); K.hills(1480, 90, '#4A1C2C', t, 26, 5);
        const k = eio(seg(lt, 0, 0.4)), shake = lt > any ? Math.sin(lt * 46) * 4 : 0;
        K.figure({ x: 540 + shake, y: 1090, s: 1.1, ...NANNI, armL: K.armPose(K.ARM.down, K.ARM.fist, k), armR: K.armPose(K.ARM.down, K.ARM.fist, k), eyes: lt > 0.3 ? 'angry' : 'n', mouth: lt > 0.3 ? 'frown' : 'flat', brow: 0, look: 0, t });
        if (lt > 0.35) K.angerMarks(430, 560, t, clamp((lt - 0.35) * 6));
      } });
    cue(st, 'whoosh', { gain: 0.5 }); cue(st + 0.35, 'thud', { gain: 0.5 });
  }

  // ── 5 · he wrote the angriest letter he could ───────────────────────────
  {
    const st = cut(3), dur = Le(3) - st;
    add({ id: 'S05', at: st, cam: [540, 900], zoom: 0.14, note: 'clay tablet fills with wedge writing',
      draw(lt, d, t) {
        K.sky('night'); K.stars(t, 36); K.moon(820, 520, 70); K.hills(1500, 90, '#1A1030', t, 8, 6);
        const p = eio(seg(lt, 0.15, dur - 0.15)), shake = Math.sin(lt * 40) * 3 * (1 - p * 0.3);
        K.tablet(540 + shake, 880, 1.45, -0.04, p, { rows: 6, glowA: 0.5 });
        ctx.save(); ctx.translate(560 + Math.sin(lt * 14) * 30, 700 + p * 330); ctx.rotate(-0.8); ctx.fillStyle = C.stoneDark; ctx.fillRect(-10, -150, 20, 150); ctx.beginPath(); ctx.moveTo(-10, 0); ctx.lineTo(10, 0); ctx.lineTo(0, 30); ctx.fill(); ctx.restore();
        K.dust(t, 18, 'rgba(255,215,150,0.5)');
      } });
    cue(st, 'whoosh', { gain: 0.5 }); cue(st + 0.2, 'slide', { dur: dur - 0.3, gain: 0.35 });
  }

  // ── 6 · it survives in the British Museum ───────────────────────────────
  {
    const st = cut(4), mus = Wd('museum', 4) - st;
    add({ id: 'S06', at: st, cam: [540, 900], zoom: 0.08, note: 'museum hall, spotlight, tablet on a pedestal',
      draw(lt, d, t) {
        K.hall(t, { kind: 'night' }); K.spotlight(540, 280, clamp(lt / 0.5)); K.pedestal(540, 1150, 440, 600);
        K.tablet(540, 960 + Math.sin(t * 1.4) * 8, 0.8, 0, 1, { rows: 6, glowA: 0.35 + 0.1 * Math.sin(t * 2) }); K.dust(t, 22);
        const a = eob(seg(lt, mus - 0.2, mus + 0.1)); if (a > 0) K.tag('BRITISH MUSEUM · 1953,0411.71', 540, 560, 36, clamp(a));
      } });
    cue(st, 'whoosh', { gain: 0.5 }); cue(st + mus - 0.1, 'sparkle', { dur: 0.8, gain: 0.35 });
  }

  // ── 7 · the oldest customer complaint on record ─────────────────────────
  {
    const st = cut(5), rec = Wd('record', 5) - st;
    add({ id: 'S07', at: st, cam: [540, 800], zoom: 0.1, note: 'gold glow, stamp slams on "customer complaint"',
      draw(lt, d, t) {
        K.sky('dawn'); K.sunDisc(540, 720, 260, { hot: true, glowA: 0.9 }); K.speedLines(540, 720, 0.45); K.dust(t, 30);
        K.tablet(540, 760, 1.0, -0.05 + Math.sin(t * 1.5) * 0.01, 1, { rows: 6, glowA: 0.8 });
        const p = seg(lt, Wd('customer', 5) - st, Wd('customer', 5) - st + 0.22); K.stamp('OLDEST CUSTOMER\nCOMPLAINT ON RECORD', 540, 1060, 70, p);
      } });
    cue(st, 'whoosh', { gain: 0.5 }); cue(Wd('customer', 5), 'slam', { gain: 0.8 });
  }

  // ── 8 · some things never change (loops to the dawn) ────────────────────
  {
    const st = cut(6), nvr = Wd('never', 6) - st;
    add({ id: 'S08', at: st, cam: [540, 900], zoom: 0.08, note: 'Nanni to camera, shrug, dawn returns (loop)',
      draw(lt, d, t) {
        K.sky('dawn'); K.sunDisc(540, 640, 150, { glowA: 0.7 }); K.clouds(t, 480); K.hills(1250, 120, '#C47038', t, 12, 1); K.ziggurat(300, 1230, 0.85, '#7A3A2C', '#9A4A34');
        K.hills(1380, 110, '#8F3F2E', t, 22, 2.4); K.hills(1560, 90, '#5A2230', t, 36, 4.1);
        const sh = eio(seg(lt, nvr, nvr + 0.4));
        K.figure({ x: 540, y: 1130, s: 1.05, ...NANNI, armL: K.armPose(K.ARM.rest, [0.6, 1.2], sh), armR: K.armPose(K.ARM.rest, [0.6, 1.2], sh), eyes: 'n', mouth: lt > nvr ? 'smile' : 'flat', brow: sh * 0.8, look: 0, tilt: sh * 0.5, t });
      } });
    cue(st, 'whoosh', { gain: 0.4 }); cue(st + nvr + 0.3, 'pop', { gain: 0.5 });
  }

  return { shots: S, cues: CUES };
}
