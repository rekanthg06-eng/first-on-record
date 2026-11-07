// Boot: fonts → script + timing → captions → shots. Then draw(t) renders film time t (pure function of t).
// window.OP is the API tools/capture.mjs drives: ready, bootError, duration(), draw(t), frame(t, q), cues(), shots().
import { W, H, setCtx, ctx, clamp, eo, eio, C } from './core/lib.js';
import { vignette } from './core/kit.js';
import { T, loadTiming } from './core/timing.js';
import { buildCaptions, drawCaption, captionList } from './core/captions.js';
import { buildShots } from './shots.js';

const cv = document.getElementById('cv');
setCtx(cv.getContext('2d'));
const OP = (window.OP = { ready: false });

// A shot renders into `target` (the main ctx, or an offscreen one for the incoming half of a crossfade).
function renderShot(sh, lt, d) {
  const punch = 1 + (sh.punch ?? 0.04) * (1 - eo(clamp(lt / 0.5)));
  const drift = 1 + (sh.zoom ?? 0.07) * eio(clamp(lt / d));
  const [cx, cy] = sh.cam || [540, 900];
  ctx.save(); ctx.translate(cx, cy); ctx.scale(punch * drift, punch * drift); ctx.translate(-cx, -cy);
  sh.draw(lt, d, sh.at + lt);
  ctx.restore();
}
const XF = 0.32;           // crossfade length (s) into the next shot; a shot with `hard: true` cuts instead
let off = null, offCtx = null;

function header(t, script) {
  const text = script.series || 'FIRST ON RECORD';
  ctx.save(); ctx.font = '700 46px Caladea'; ctx.letterSpacing = '9px'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  const w = ctx.measureText(text).width, y = 250, a = 1; // header fade-in disabled so first and last frames match (loop)
  ctx.globalAlpha = a; ctx.shadowColor = 'rgba(30,8,16,0.6)'; ctx.shadowBlur = 10; ctx.fillStyle = C.gold; ctx.fillText(text, 540, y);
  ctx.shadowBlur = 0; ctx.strokeStyle = C.gold; ctx.lineWidth = 3; for (const sd of [-1, 1]) { ctx.beginPath(); ctx.moveTo(540 + sd * (w / 2 + 28), y); ctx.lineTo(540 + sd * (w / 2 + 28 + 90), y); ctx.stroke(); }
  if (script.tag) { ctx.font = '700 30px Caladea'; ctx.letterSpacing = '6px'; ctx.fillStyle = C.cream; ctx.globalAlpha = a * 0.85; ctx.fillText(script.tag, 540, y + 58); }
  ctx.letterSpacing = '0px'; ctx.restore();
}

function draw(t) {
  t = clamp(t, 0, T.dur - 1e-4);
  ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = 1; ctx.letterSpacing = '0px';
  ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H);
  const S = OP._shots; let i = S.length - 1; while (i > 0 && S[i].at > t) i--;
  const sh = S[i], nx = S[i + 1], end = nx ? nx.at : T.dur, d = end - sh.at, lt = t - sh.at;
  renderShot(sh, lt, d);
  if (nx && !nx.hard && t > nx.at - XF) {                // incoming shot fades in over the last XF seconds of this one
    const p = eio(clamp((t - (nx.at - XF)) / XF)), main = ctx;
    if (!off) { off = document.createElement('canvas'); off.width = W; off.height = H; offCtx = off.getContext('2d'); }
    offCtx.setTransform(1, 0, 0, 1, 0, 0); offCtx.clearRect(0, 0, W, H);
    setCtx(offCtx); renderShot(nx, 0, (S[i + 2] ? S[i + 2].at : T.dur) - nx.at); setCtx(main);
    main.globalAlpha = p; main.drawImage(off, 0, 0); main.globalAlpha = 1;
  }
  if (nx && nx.hard && t > nx.at - 0.001) { /* hard cut handled by index switch */ }
  if (sh.hard && lt < 0.1) { ctx.fillStyle = '#FFFFFF'; ctx.globalAlpha = 0.5 * (1 - lt / 0.1); ctx.fillRect(0, 0, W, H); ctx.globalAlpha = 1; }
  ctx.globalAlpha = 1; ctx.letterSpacing = '0px';
  vignette(0.38);
  header(t, OP.script);
  const fade = 1; // black fade in/out disabled so first and last frames match (loop)
  if (fade < 1) { ctx.fillStyle = '#000'; ctx.globalAlpha = 1 - fade; ctx.fillRect(0, 0, W, H); ctx.globalAlpha = 1; }
  drawCaption(t);
}

(async () => {
  try {
    await document.fonts.load('900 100px Inter'); await document.fonts.load('700 100px Caladea');
    const script = await (await fetch('script.json', { cache: 'no-store' })).json();
    await loadTiming();
    buildCaptions(script);
    const { shots, cues } = buildShots();
    shots.sort((a, b) => a.at - b.at);
    OP._shots = shots; OP.script = script;
    OP.duration = () => T.dur;
    OP.draw = draw;
    OP.frame = (t, q = 0.92) => { draw(t); return cv.toDataURL('image/jpeg', q); };
    OP.shots = () => shots.map((s, i) => ({ id: s.id, at: +s.at.toFixed(3), end: +(i < shots.length - 1 ? shots[i + 1].at : T.dur).toFixed(3), note: s.note || '' }));
    OP.captions = () => captionList().map((c) => ({ s: +c.s.toFixed(3), e: +c.e.toFixed(3), text: c.words.map((w) => (w.hi ? '*' : '') + w.txt).join(' ') }));
    OP.cues = () => cues.slice().sort((a, b) => a.t - b.t);
    OP.ready = true;
    // preview mode (not capture): play in real time, ?t=12.3 to hold a frame
    const q = new URLSearchParams(location.search);
    if (!q.has('capture')) {
      if (q.has('t')) draw(+q.get('t'));
      else {
        const audio = new Audio('data/mix.wav'); let t0 = null;
        const btn = document.getElementById('play'); btn.hidden = false;
        btn.onclick = () => { btn.hidden = true; t0 = performance.now(); audio.currentTime = 0; audio.play().catch(() => {}); };
        const loop = (now) => { const t = t0 == null ? 0 : (now - t0) / 1000; draw(t0 == null ? 0 : t); if (t0 != null && t > T.dur) { t0 = null; btn.hidden = false; } requestAnimationFrame(loop); };
        requestAnimationFrame(loop);
      }
    }
  } catch (e) { OP.bootError = String(e && e.stack || e); console.error(e); }
})();
