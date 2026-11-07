// Epic Frame kit: flat-vector epic storytelling. Scenes (sky, sun, hills, arch hall), puppet figures with
// period dress, props (tablet, ingot, scroll), counters, ribbons and weather. Everything is a pure function of time.
import { ctx, C, W, H, clamp, lerp, seg, eo, eio, eob, rnd, TAU, skyFill, glow, hexA, mix, vgrad, circle, ell, rr } from './lib.js';

// ───────────────────────── scenes ─────────────────────────
export const SKY = {
  dawn: [[0, '#C9622F'], [0.38, '#EA9A45'], [0.7, '#F6C26A'], [1, '#F0A94E']],
  noon: [[0, '#E39A4A'], [0.5, '#F4C06C'], [1, '#F8D890']],
  dusk: [[0, '#4A1C33'], [0.45, '#B4552F'], [1, '#E9923F']],
  night: [[0, '#14122A'], [0.6, '#2B2A5E'], [1, '#4B3A7A']],
  storm: [[0, '#1B1A33'], [0.6, '#3A3A66'], [1, '#6A6A94']],
  hall: [[0, '#3E1626'], [1, '#6B2433']],
};
export function sky(kind = 'dawn') { skyFill(SKY[kind]); }

export function sunDisc(x, y, r, { hot = false, glowA = 0.6, color = C.sun } = {}) {
  glow(x, y, r * 3.2, hot ? '#FFD27A' : 'rgba(255,205,120,0.9)', glowA);
  circle(x, y, r, hot ? C.sunHot : color);
}
export function moon(x, y, r) { glow(x, y, r * 3, 'rgba(230,225,255,0.55)', 0.6); circle(x, y, r, '#F1EDE2'); circle(x - r * 0.25, y - r * 0.1, r * 0.2, 'rgba(160,150,180,0.35)'); circle(x + r * 0.3, y + r * 0.3, r * 0.14, 'rgba(160,150,180,0.3)'); }
export function stars(t, n = 40, alpha = 1) {
  for (let i = 0; i < n; i++) { const tw = 0.5 + 0.5 * Math.sin(t * 2 + i * 3.1); ctx.globalAlpha = alpha * (0.35 + 0.65 * tw); circle(rnd(i) * W, 80 + rnd(i + 99) * 900, 2 + rnd(i + 5) * 3, '#FFF6D8'); }
  ctx.globalAlpha = 1;
}
/** layered silhouette hills; drift = slow parallax */
export function hills(y0, amp, color, t, speed = 10, seed = 0, freq = 0.004, bottom = H + 300) {
  ctx.beginPath(); ctx.moveTo(-300, bottom);
  for (let x = -300; x <= W + 300; x += 20) {
    const u = x + t * speed;
    ctx.lineTo(x, y0 - amp * (0.55 * Math.sin(u * freq + seed) + 0.3 * Math.sin(u * freq * 2.3 + seed * 2) + 0.15 * Math.sin(u * freq * 5.1 + seed * 3)));
  }
  ctx.lineTo(W + 300, bottom); ctx.closePath(); ctx.fillStyle = color; ctx.fill();
}
export function haze(y, h, color, a = 0.35) { const g = ctx.createLinearGradient(0, y - h, 0, y + h); g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(0.5, hexA(color, a)); g.addColorStop(1, 'rgba(0,0,0,0)'); ctx.fillStyle = g; ctx.fillRect(-300, y - h, W + 600, h * 2); }
export function clouds(t, y, color = 'rgba(255,235,200,0.35)', n = 4) {
  ctx.fillStyle = color;
  for (let i = 0; i < n; i++) { const x = ((rnd(i) * 1400 + t * (14 + i * 4)) % 1500) - 200, yy = y + rnd(i + 7) * 160, s = 0.7 + rnd(i + 3) * 0.8;
    ctx.beginPath(); for (const [dx, dy, r] of [[0, 0, 60], [70, -20, 80], [150, 0, 62], [75, 20, 70]]) { ctx.moveTo(x + (dx + r) * s, yy + dy * s); ctx.arc(x + dx * s, yy + dy * s, r * s, 0, TAU); } ctx.fill(); }
}
export function ziggurat(x, y, s, color = '#5A2A2E', lit = '#7A3A33') {
  ctx.save(); ctx.translate(x, y); ctx.scale(s, s);
  const tiers = [[-300, 300, 0, -120], [-220, 220, -120, -230], [-140, 140, -230, -320]];
  tiers.forEach(([a, b, y0, y1], i) => { ctx.beginPath(); ctx.moveTo(a, y0); ctx.lineTo(a + 40, y1); ctx.lineTo(b - 40, y1); ctx.lineTo(b, y0); ctx.closePath(); ctx.fillStyle = i % 2 ? lit : color; ctx.fill(); });
  ctx.fillStyle = color; ctx.fillRect(-52, -400, 104, 80); ctx.beginPath(); ctx.moveTo(-60, -400); ctx.lineTo(0, -450); ctx.lineTo(60, -400); ctx.fill();
  ctx.beginPath(); ctx.moveTo(-26, 0); ctx.lineTo(-18, -320); ctx.lineTo(18, -320); ctx.lineTo(26, 0); ctx.fillStyle = hexA('#000000', 0.18); ctx.fill();
  ctx.restore();
}
export function pyramid(x, y, s, color = '#6A3028', side = '#4A2020') {
  ctx.save(); ctx.translate(x, y); ctx.scale(s, s);
  ctx.beginPath(); ctx.moveTo(-320, 0); ctx.lineTo(0, -330); ctx.lineTo(320, 0); ctx.closePath(); ctx.fillStyle = color; ctx.fill();
  ctx.beginPath(); ctx.moveTo(0, -330); ctx.lineTo(320, 0); ctx.lineTo(60, 0); ctx.closePath(); ctx.fillStyle = side; ctx.fill(); ctx.restore();
}
export function palm(x, y, s, color = '#3A1E22', t = 0, lean = 0.1) {
  ctx.save(); ctx.translate(x, y); ctx.scale(s, s); ctx.strokeStyle = color; ctx.lineCap = 'round'; ctx.lineWidth = 16;
  ctx.beginPath(); ctx.moveTo(0, 0); ctx.quadraticCurveTo(40 * lean * 10, -170, 20 * lean * 10, -340); ctx.stroke();
  for (let i = 0; i < 7; i++) { const a = -Math.PI / 2 + (i - 3) * 0.5 + Math.sin(t * 1.2 + i) * 0.04; ctx.lineWidth = 12; ctx.beginPath(); ctx.moveTo(20 * lean * 10, -340);
    ctx.quadraticCurveTo(20 * lean * 10 + Math.cos(a) * 90, -340 + Math.sin(a) * 60 - 20, 20 * lean * 10 + Math.cos(a) * 170, -340 + Math.sin(a) * 120 + 70); ctx.stroke(); }
  ctx.restore();
}
/** a tall arched window with a gold ring: the signature frame */
export function arch(x, y, w, h, kind = 'sunset', t = 0) {
  ctx.save(); ctx.translate(x, y);
  const r = w / 2, path = () => { ctx.beginPath(); ctx.moveTo(-r, h); ctx.lineTo(-r, r); ctx.arc(0, r, r, Math.PI, 0); ctx.lineTo(r, h); ctx.closePath(); };
  path(); ctx.fillStyle = C.goldDark; ctx.fill();
  ctx.save(); ctx.translate(0, 0); ctx.scale(1 - 24 / w, 1 - 12 / h); ctx.translate(0, 8);
  path(); ctx.clip();
  const g = ctx.createLinearGradient(0, 0, 0, h);
  if (kind === 'sunset') { g.addColorStop(0, '#D9803A'); g.addColorStop(1, '#F6C26A'); } else if (kind === 'night') { g.addColorStop(0, '#2B2A5E'); g.addColorStop(1, '#6A5A9A'); } else { g.addColorStop(0, '#8A2E3C'); g.addColorStop(1, '#E9923F'); }
  ctx.fillStyle = g; ctx.fillRect(-r, 0, w, h + 20);
  glow(0, h * 0.62, r * 1.5, 'rgba(255,215,140,0.8)', kind === 'night' ? 0.3 : 0.7);
  ctx.restore(); ctx.lineWidth = 8; ctx.strokeStyle = C.gold; ctx.save(); ctx.scale(1 - 12 / w, 1 - 6 / h); ctx.translate(0, 4); path(); ctx.stroke(); ctx.restore();
  ctx.restore();
}
export function pillar(x, y, w, h, color = '#7A2E3A', cap = C.gold) {
  ctx.fillStyle = color; ctx.fillRect(x - w / 2, y, w, h); ctx.fillStyle = hexA('#000000', 0.18); ctx.fillRect(x + w * 0.1, y, w * 0.4, h);
  ctx.fillStyle = cap; ctx.fillRect(x - w * 0.7, y, w * 1.4, 26); ctx.fillRect(x - w * 0.7, y + h - 22, w * 1.4, 22);
}
/** the hall: wine wall, gold-ringed arch, floor, pilasters, warm light */
export function hall(t, { kind = 'sunset', tone = 0 } = {}) {
  sky('hall'); const sway = Math.sin(t * 0.4) * 6;
  arch(540 + sway * 0.3, 400, 600, 1020, kind, t);
  pillar(80, 150, 90, 1250); pillar(1000, 150, 90, 1250);
  ctx.fillStyle = '#2A0F1C'; ctx.fillRect(-300, 1300, W + 600, 700); ctx.fillStyle = hexA(C.gold, 0.25); ctx.fillRect(-300, 1300, W + 600, 6);
  glow(540, 1000, 700, 'rgba(255,190,100,0.25)', 0.8);
}
export function vignette(a = 0.5) {
  const g = ctx.createRadialGradient(540, 960, 520, 540, 960, 1250); g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, `rgba(10,0,10,${a})`);
  ctx.fillStyle = g; ctx.fillRect(-300, -300, W + 600, H + 600);
}
export function lightning(t, at, dur = 0.5) {
  const lt = t - at; if (lt < 0 || lt > dur) return;
  const f = (lt < 0.08 ? 1 : lt < 0.16 ? 0.2 : lt < 0.24 ? 0.8 : Math.max(0, 1 - lt / dur)) ;
  ctx.fillStyle = `rgba(220,225,255,${0.55 * f})`; ctx.fillRect(-300, -300, W + 600, H + 600);
  ctx.save(); ctx.globalAlpha = Math.min(1, f * 1.6); ctx.strokeStyle = '#FFFFFF'; ctx.lineWidth = 12; ctx.lineJoin = 'round'; ctx.shadowColor = '#BFC8FF'; ctx.shadowBlur = 40;
  ctx.beginPath(); let x = 640, y = -50; ctx.moveTo(x, y); for (let i = 0; i < 9; i++) { x += (rnd(i + at * 7) - 0.5) * 170; y += 150; ctx.lineTo(x, y); } ctx.stroke(); ctx.restore();
}
export function dust(t, n = 26, color = 'rgba(255,225,170,0.7)') {
  for (let i = 0; i < n; i++) { const x = (rnd(i) * 1300 + t * (8 + rnd(i + 1) * 14)) % 1300 - 110, y = 300 + rnd(i + 4) * 1200 + Math.sin(t * 0.6 + i) * 24;
    ctx.globalAlpha = 0.25 + 0.5 * rnd(i + 8); circle(x, y, 2 + rnd(i + 3) * 4, color); } ctx.globalAlpha = 1;
}

// ───────────────────────── figures (flat puppets) ─────────────────────────
const SKIN = { L: [C.skinL, '#C9926A'], M: [C.skinM, '#A66E46'], D: [C.skinD, '#6E4630'] };
export const ARM = { down: [0.12, 0.1], rest: [0.18, 0.5], hip: [0.5, -0.9], raise: [2.5, 0.2], point: [1.6, 0.05], present: [1.2, 0.5], pull: [1.45, -1.2], guard: [0.35, 1.5], fist: [0.3, 1.9], wave: [2.7, 0.4] };
export const armPose = (a, b, t) => [lerp(a[0], b[0], t), lerp(a[1], b[1], t)];

function limb(x0, y0, x1, y1, w0, w1, color) {
  const a = Math.atan2(y1 - y0, x1 - x0), nx = Math.cos(a + Math.PI / 2), ny = Math.sin(a + Math.PI / 2);
  ctx.beginPath(); ctx.moveTo(x0 + nx * w0, y0 + ny * w0); ctx.lineTo(x1 + nx * w1, y1 + ny * w1); ctx.arc(x1, y1, w1, a + Math.PI / 2, a - Math.PI / 2, true);
  ctx.lineTo(x0 - nx * w0, y0 - ny * w0); ctx.arc(x0, y0, w0, a - Math.PI / 2, a + Math.PI / 2, true); ctx.closePath(); ctx.fillStyle = color; ctx.fill();
}

/** upper-body puppet. origin = chest centre; s = 1 → crown-to-waist ≈ 900 px.
 *  o: { x, y, s, skin 'L|M|D', dress 'mesop|egypt|plain', cloth, trim, beard 'none|short|long', beardCol, hat 'cap|nemes|turban|crown|none', hatCol,
 *       armL, armR ([upper, bend] see ARM), eyes 'n|wide|closed|angry|sad', mouth 'flat|open|frown|smile|o', brow, look (-1..1), t, face (mirror -1/1), holdR(x,y), holdL(x,y), tilt } */
export function figure(o) {
  const { x = 540, y = 1000, s = 1, skin = 'M', dress = 'plain', cloth = C.lapis, trim = C.gold, beard = 'none', beardCol = C.hair, hat = 'none', hatCol = C.cream,
    armL = ARM.down, armR = ARM.down, eyes = 'n', mouth = 'flat', brow = 0, look = 0, t = 0, face = 1, holdR = null, holdL = null, tilt = 0, shadow = true, fade = 1, hair = 'none', hairCol = '#1C1210', glasses = false, circlet = false } = o;
  const [sk, skS] = SKIN[skin] || SKIN.M, clothD = mix(cloth, '#000000', 0.28);
  ctx.save(); ctx.globalAlpha *= fade; ctx.translate(x, y); ctx.scale(s * face, s);
  if (shadow) { glow(0, 120, 380, 'rgba(0,0,0,0.38)', 0.55); }
  // arms behind torso? keep arms in front; torso first
  const torso = () => { ctx.beginPath(); ctx.moveTo(-150, -95); ctx.quadraticCurveTo(-170, -105, -176, -60); ctx.lineTo(-150, 420); ctx.lineTo(150, 420); ctx.lineTo(176, -60); ctx.quadraticCurveTo(170, -105, 150, -95); ctx.quadraticCurveTo(0, -130, -150, -95); ctx.closePath(); };
  torso(); ctx.fillStyle = dress === 'egypt' ? sk : cloth; ctx.fill();
  if (dress === 'mesop') {                      // kaunakes: scalloped fringe bands, diagonal sash
    ctx.save(); torso(); ctx.clip();
    for (let r = 0; r < 5; r++) { const yy = 60 + r * 78; ctx.fillStyle = r % 2 ? clothD : cloth; for (let i = -4; i <= 4; i++) { ctx.beginPath(); ctx.arc(i * 46, yy, 26, 0, Math.PI); ctx.fill(); } ctx.fillRect(-190, yy - 26, 380, 26); }
    ctx.fillStyle = hexA(C.cream, 0.9); ctx.beginPath(); ctx.moveTo(-170, -80); ctx.lineTo(-110, -90); ctx.lineTo(176, 330); ctx.lineTo(120, 380); ctx.closePath(); ctx.fill();
    ctx.restore();
    ctx.fillStyle = trim; ctx.fillRect(-170, 5, 340, 12);
  } else if (dress === 'egypt') {               // usekh collar
    ctx.fillStyle = C.cream; ctx.fillRect(-150, 250, 300, 180);
    ctx.save(); ctx.beginPath(); ctx.arc(0, -110, 190, 0, Math.PI); ctx.clip();
    [[190, C.turq], [160, C.gold], [130, C.crimson], [100, C.gold], [72, C.lapis]].forEach(([r, c]) => { ctx.beginPath(); ctx.arc(0, -110, r, 0, Math.PI); ctx.fillStyle = c; ctx.fill(); });
    ctx.restore();
  } else { ctx.fillStyle = clothD; ctx.fillRect(-176, 250, 352, 12); ctx.fillStyle = trim; ctx.fillRect(-176, -10, 352, 10); }
  ctx.fillStyle = 'rgba(0,0,0,0.12)'; ctx.beginPath(); ctx.moveTo(40, -100); ctx.lineTo(176, -60); ctx.lineTo(150, 420); ctx.lineTo(60, 420); ctx.closePath(); ctx.fill();   // shade on the far side
  // arms
  const arm = (pose, dir, hold) => {
    const [a, b] = pose, sx = dir * 150, sy = -70, L1 = 200, L2 = 190;
    const ex = sx + dir * Math.sin(a) * L1, ey = sy + Math.cos(a) * L1, ang = a + b * 1, hx = ex + dir * Math.sin(ang) * L2, hy = ey + Math.cos(ang) * L2;
    const sleeve = dress === 'egypt' ? sk : cloth;
    limb(sx, sy, ex, ey, 44, 38, dress === 'egypt' ? sk : sleeve);
    limb(ex, ey, hx, hy, 36, 28, sk);
    circle(ex, ey, 38, dress === 'egypt' ? sk : sleeve);
    ctx.fillStyle = trim; limb(ex + (hx - ex) * 0.12, ey + (hy - ey) * 0.12, ex + (hx - ex) * 0.2, ey + (hy - ey) * 0.2, 36, 36, trim);
    circle(hx, hy, 34, sk);
    if (hold) hold(hx, hy, dir);
    return [hx, hy];
  };
  // far arm first so the near one overlaps
  arm(armL, -1, holdL); arm(armR, 1, holdR);
  // neck + head
  ctx.save(); ctx.translate(0, 0); ctx.rotate(tilt * 0.12);
  ctx.fillStyle = skS; ctx.fillRect(-42, -170, 84, 110);
  const hy = -285;
  if (hat === 'nemes') {                          // striped headcloth behind the head
    ctx.beginPath(); ctx.moveTo(-150, hy - 40); ctx.lineTo(-195, hy + 210); ctx.lineTo(-95, hy + 215); ctx.lineTo(-70, hy + 40); ctx.closePath(); ctx.fillStyle = C.lapis; ctx.fill();
    ctx.beginPath(); ctx.moveTo(150, hy - 40); ctx.lineTo(195, hy + 210); ctx.lineTo(95, hy + 215); ctx.lineTo(70, hy + 40); ctx.closePath(); ctx.fill();
    ctx.strokeStyle = C.gold; ctx.lineWidth = 10; for (let i = 0; i < 4; i++) { ctx.beginPath(); ctx.moveTo(-170 + i * 8, hy + 20 + i * 50); ctx.lineTo(-90 + i * 3, hy + 22 + i * 50); ctx.moveTo(170 - i * 8, hy + 20 + i * 50); ctx.lineTo(90 - i * 3, hy + 22 + i * 50); ctx.stroke(); }
  }
  if (beard === 'long') { ctx.beginPath(); ctx.moveTo(-92, hy + 30); ctx.quadraticCurveTo(-110, hy + 250, -40, hy + 330); ctx.quadraticCurveTo(0, hy + 360, 40, hy + 330); ctx.quadraticCurveTo(110, hy + 250, 92, hy + 30); ctx.closePath(); ctx.fillStyle = beardCol; ctx.fill();
    ctx.strokeStyle = mix(beardCol, '#000000', 0.35); ctx.lineWidth = 5; for (let i = 0; i < 4; i++) { ctx.beginPath(); ctx.moveTo(-70 + i * 6, hy + 120 + i * 48); ctx.quadraticCurveTo(0, hy + 150 + i * 48, 70 - i * 6, hy + 120 + i * 48); ctx.stroke(); } }
  if (hair === 'long') { ctx.beginPath(); ctx.moveTo(-112, hy - 40); ctx.bezierCurveTo(-150, hy + 120, -140, hy + 300, -120, hy + 330); ctx.lineTo(120, hy + 330); ctx.bezierCurveTo(140, hy + 300, 150, hy + 120, 112, hy - 40); ctx.closePath(); ctx.fillStyle = hairCol; ctx.fill(); }
  // head
  ctx.beginPath(); ctx.moveTo(-96, hy - 10); ctx.bezierCurveTo(-100, hy - 130, 100, hy - 130, 96, hy - 10); ctx.bezierCurveTo(98, hy + 70, 50, hy + 118, 0, hy + 120); ctx.bezierCurveTo(-50, hy + 118, -98, hy + 70, -96, hy - 10); ctx.closePath();
  ctx.fillStyle = sk; ctx.fill();
  ctx.save(); ctx.clip(); ctx.fillStyle = skS; ctx.fillRect(38, hy - 140, 80, 280); ctx.restore();            // flat shade on one side
  circle(-98, hy + 10, 22, sk); circle(98, hy + 10, 22, skS);                                                    // ears
  if (beard === 'short') { ctx.beginPath(); ctx.moveTo(-90, hy + 20); ctx.quadraticCurveTo(-92, hy + 118, 0, hy + 126); ctx.quadraticCurveTo(92, hy + 118, 90, hy + 20); ctx.quadraticCurveTo(60, hy + 62, 0, hy + 56); ctx.quadraticCurveTo(-60, hy + 62, -90, hy + 20); ctx.fillStyle = beardCol; ctx.fill(); }
  if (beard === 'long') { ctx.beginPath(); ctx.moveTo(-94, hy + 10); ctx.quadraticCurveTo(-60, hy + 66, 0, hy + 58); ctx.quadraticCurveTo(60, hy + 66, 94, hy + 10); ctx.quadraticCurveTo(70, hy + 52, 0, hy + 44); ctx.quadraticCurveTo(-70, hy + 52, -94, hy + 10); ctx.fillStyle = beardCol; ctx.fill(); }
  // face
  const blink = (t % 3.4) > 3.28, eyeClosed = eyes === 'closed' || blink, lx = look * 8, ey = hy - 10;
  for (const sd of [-1, 1]) {
    const ex = sd * 42;
    if (eyeClosed) { ctx.strokeStyle = C.ink; ctx.lineWidth = 6; ctx.beginPath(); ctx.moveTo(ex - 20, ey + 2); ctx.quadraticCurveTo(ex, ey + 12, ex + 20, ey + 2); ctx.stroke(); }
    else { const h = eyes === 'wide' ? 17 : eyes === 'angry' ? 9 : 12; ell(ex, ey, 21, h, '#F6EEDC'); circle(ex + lx, ey + 1, eyes === 'wide' ? 9 : 10, C.ink); circle(ex + lx + 3, ey - 3, 3, '#FFFFFF');
      if (dress === 'egypt') { ctx.strokeStyle = C.ink; ctx.lineWidth = 6; ctx.beginPath(); ctx.moveTo(ex - 26, ey + 4); ctx.lineTo(ex + 30, ey - 2); ctx.stroke(); } }
    // brows: raise 0..1 lifts, angry tilts inward, sad tilts outward
    const tl = eyes === 'angry' ? 0.45 : eyes === 'sad' ? -0.4 : 0, by = ey - 30 - brow * 14;
    ctx.strokeStyle = beard !== 'none' || skin === 'D' ? C.hair : '#3A2418'; ctx.lineWidth = 11; ctx.lineCap = 'round'; ctx.beginPath();
    ctx.moveTo(ex - 24, by + (sd === -1 ? -1 : 1) * tl * 22); ctx.lineTo(ex + 24, by + (sd === -1 ? 1 : -1) * tl * 22); ctx.stroke();   // angry: inner ends lower
  }
  ctx.strokeStyle = skS; ctx.lineWidth = 7; ctx.beginPath(); ctx.moveTo(lx * 0.6, hy + 2); ctx.quadraticCurveTo(14 + lx * 0.6, hy + 36, -2, hy + 44); ctx.stroke();   // nose
  const my = hy + 78; ctx.lineCap = 'round';
  if (mouth === 'open') { ell(0, my + 6, 24, 20, '#4A1A1A'); ell(0, my + 16, 14, 8, '#C25A5A'); }
  else if (mouth === 'o') ell(0, my + 8, 14, 18, '#4A1A1A');
  else { ctx.strokeStyle = beard === 'none' ? '#7A3A30' : '#2A1410'; ctx.lineWidth = 8; ctx.beginPath();
    if (mouth === 'frown') { ctx.moveTo(-26, my + 12); ctx.quadraticCurveTo(0, my - 8, 26, my + 12); } else if (mouth === 'smile') { ctx.moveTo(-28, my - 2); ctx.quadraticCurveTo(0, my + 22, 28, my - 2); } else { ctx.moveTo(-24, my + 4); ctx.lineTo(24, my + 4); } ctx.stroke(); }
  // headwear
  if (hair !== 'none') { ctx.beginPath(); ctx.moveTo(-102, hy - 24); ctx.bezierCurveTo(-116, hy - 180, 116, hy - 180, 102, hy - 24); ctx.quadraticCurveTo(64, hy - 100, 0, hy - 92); ctx.quadraticCurveTo(-64, hy - 100, -102, hy - 24); ctx.closePath(); ctx.fillStyle = hairCol; ctx.fill(); }
  if (circlet) { ctx.fillStyle = C.gold; ctx.fillRect(-100, hy - 78, 200, 14); circle(0, hy - 71, 13, C.crimson); }
  if (glasses) { ctx.strokeStyle = C.ink; ctx.lineWidth = 6; for (const sd of [-1, 1]) { ctx.beginPath(); ctx.arc(sd * 42, hy - 10, 30, 0, TAU); ctx.stroke(); } ctx.beginPath(); ctx.moveTo(-12, hy - 12); ctx.lineTo(12, hy - 12); ctx.stroke(); }
  if (hat === 'cap') { ctx.beginPath(); ctx.moveTo(-100, hy - 60); ctx.bezierCurveTo(-110, hy - 170, 110, hy - 170, 100, hy - 60); ctx.closePath(); ctx.fillStyle = hatCol; ctx.fill(); ctx.fillStyle = C.gold; ctx.fillRect(-102, hy - 70, 204, 20); circle(0, hy - 60, 12, C.crimson); }
  if (hat === 'turban') { ell(0, hy - 90, 118, 70, hatCol); for (let i = 0; i < 3; i++) { ctx.strokeStyle = mix(hatCol, '#000000', 0.2); ctx.lineWidth = 6; ctx.beginPath(); ctx.moveTo(-100 + i * 10, hy - 80 + i * 18); ctx.quadraticCurveTo(0, hy - 120 + i * 26, 100 - i * 10, hy - 80 + i * 18); ctx.stroke(); } }
  if (hat === 'crown') { ctx.beginPath(); ctx.moveTo(-78, hy - 78); ctx.lineTo(-42, hy - 290); ctx.lineTo(42, hy - 290); ctx.lineTo(78, hy - 78); ctx.closePath(); ctx.fillStyle = C.gold; ctx.fill(); ctx.fillStyle = C.goldHi; ctx.fillRect(-60, hy - 90, 120, 14); circle(0, hy - 150, 14, C.crimson); }
  if (hat === 'nemes') { ctx.beginPath(); ctx.moveTo(-104, hy - 4); ctx.bezierCurveTo(-110, hy - 140, 110, hy - 140, 104, hy - 4); ctx.lineTo(80, hy - 54); ctx.quadraticCurveTo(0, hy - 80, -80, hy - 54); ctx.closePath(); ctx.fillStyle = C.lapis; ctx.fill(); ctx.fillStyle = C.gold; ctx.fillRect(-98, hy - 66, 196, 12); }
  ctx.restore(); ctx.restore();
}
export function handPos(o, side = 'R') { // where a hand ends up (local scale applied): lets props sit at the hand
  const { x = 540, y = 1000, s = 1, armL = ARM.down, armR = ARM.down, face = 1 } = o, [a, b] = side === 'R' ? armR : armL, dir = side === 'R' ? 1 : -1;
  const sx = dir * 150, sy = -70, ex = sx + dir * Math.sin(a) * 200, ey = sy + Math.cos(a) * 200, ang = a + b;
  return [x + face * s * (ex + dir * Math.sin(ang) * 190), y + s * (ey + Math.cos(ang) * 190)];
}

// ───────────────────────── props ─────────────────────────
/** clay tablet: rows of wedge marks that fill in with `progress` (0..1) */
export function tablet(x, y, s = 1, rot = 0, progress = 1, { rows = 6, glowA = 0, hl = 0 } = {}) {
  ctx.save(); ctx.translate(x, y); ctx.rotate(rot); ctx.scale(s, s);
  if (glowA) glow(0, 0, 420, 'rgba(255,215,140,0.9)', glowA);
  ctx.beginPath(); ctx.roundRect(-190, -250, 380, 500, 60); ctx.fillStyle = C.clay; ctx.fill();
  ctx.beginPath(); ctx.roundRect(-190, -250, 380, 500, 60); ctx.save(); ctx.clip(); ctx.fillStyle = C.clayDark; ctx.fillRect(100, -260, 100, 520); ctx.fillStyle = hexA(C.clayHi, 0.5); ctx.fillRect(-200, -260, 60, 520); ctx.restore();
  const total = rows * 7; let n = 0;
  for (let r = 0; r < rows; r++) for (let c = 0; c < 7; c++) { n++; if (n / total > progress) continue; const px = -140 + c * 46 + rnd(r * 9 + c) * 8, py = -190 + r * 68;
    ctx.fillStyle = C.clayDark; for (let k = 0; k < 1 + (rnd(r * 3 + c * 7) > 0.5); k++) { ctx.beginPath(); ctx.moveTo(px + k * 14, py); ctx.lineTo(px + k * 14 + 22, py - 4); ctx.lineTo(px + k * 14 + 8, py + 26); ctx.closePath(); ctx.fill(); ctx.fillRect(px + k * 14 + 6, py + 14, 3, 18); } }
  if (hl) { ctx.fillStyle = `rgba(255,220,120,${hl * 0.35})`; ctx.fillRect(-190, -250, 380, 500); }
  ctx.restore();
}
export function ingot(x, y, s = 1, rot = 0, kind = 'fine') {
  ctx.save(); ctx.translate(x, y); ctx.rotate(rot); ctx.scale(s, s);
  const base = kind === 'fine' ? C.copper : C.verdigris, hi = kind === 'fine' ? C.copperHi : '#9CC9B0', dk = kind === 'fine' ? '#A2501F' : C.verdigrisDark;
  ctx.beginPath(); ctx.moveTo(-150, 40); ctx.lineTo(-110, -60); ctx.lineTo(110, -60); ctx.lineTo(150, 40); ctx.lineTo(120, 70); ctx.lineTo(-120, 70); ctx.closePath(); ctx.fillStyle = base; ctx.fill();
  ctx.beginPath(); ctx.moveTo(-110, -60); ctx.lineTo(110, -60); ctx.lineTo(90, -30); ctx.lineTo(-90, -30); ctx.closePath(); ctx.fillStyle = hi; ctx.fill();
  ctx.fillStyle = dk; ctx.fillRect(-120, 44, 240, 26);
  if (kind === 'fine') { ctx.fillStyle = 'rgba(255,255,255,0.55)'; ctx.beginPath(); ctx.ellipse(-50, -42, 40, 6, 0, 0, TAU); ctx.fill(); }
  else { ctx.strokeStyle = C.ink; ctx.lineWidth = 6; ctx.beginPath(); ctx.moveTo(-40, -50); ctx.lineTo(-10, -10); ctx.lineTo(-50, 30); ctx.moveTo(60, -40); ctx.lineTo(40, 0); ctx.lineTo(80, 40); ctx.stroke(); for (let i = 0; i < 6; i++) circle(-90 + i * 36, 0 + (i % 2) * 20, 9, mix(C.verdigrisDark, '#2A4A3C', 0.5)); }
  ctx.restore();
}
export function silver(x, y, s = 1, rot = 0) { ctx.save(); ctx.translate(x, y); ctx.rotate(rot); ctx.scale(s, s); for (let i = 0; i < 5; i++) { circle(-40 + i * 22, (i % 2) * 14, 28, '#D8DCE4'); circle(-44 + i * 22, -6 + (i % 2) * 14, 10, '#FFFFFF'); } ctx.restore(); }
export function pedestal(x, y, w = 420, h = 520) { ctx.fillStyle = '#3A1E26'; ctx.fillRect(x - w / 2, y, w, h); ctx.fillStyle = '#5A3038'; ctx.fillRect(x - w / 2 - 20, y, w + 40, 34); ctx.fillStyle = hexA('#000000', 0.25); ctx.fillRect(x + w * 0.2, y + 34, w * 0.3, h); }
export function spotlight(x, y, a = 1) { ctx.save(); const g = ctx.createLinearGradient(0, y, 0, y + 1200); g.addColorStop(0, `rgba(255,230,170,${0.5 * a})`); g.addColorStop(1, 'rgba(255,230,170,0)'); ctx.fillStyle = g; ctx.beginPath(); ctx.moveTo(x - 60, y); ctx.lineTo(x + 60, y); ctx.lineTo(x + 380, y + 1200); ctx.lineTo(x - 380, y + 1200); ctx.closePath(); ctx.fill(); ctx.restore(); }
export function crowd(x, y, n, s, color, t = 0, spread = 70) { for (let i = 0; i < n; i++) { const px = x + (i - (n - 1) / 2) * spread, bob = Math.sin(t * 3 + i * 1.7) * 6 * (rnd(i) > 0.5 ? 1 : 0.3), hh = s * (1 + rnd(i + 11) * 0.25);
  ctx.fillStyle = color; circle(px, y - 130 * hh + bob, 28 * s, color); ctx.beginPath(); ctx.roundRect(px - 38 * s, y - 100 * hh + bob, 76 * s, 120 * hh, 22); ctx.fill(); } }

// ───────────────────────── graphics ─────────────────────────
export function counter(x, y, val, size = 190, a = 1, label = '') {
  ctx.save(); ctx.globalAlpha *= a; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; const txt = Math.round(val).toLocaleString('en-US');
  ctx.font = `700 ${size}px Caladea`; ctx.lineJoin = 'round'; ctx.lineWidth = size * 0.1; ctx.strokeStyle = hexA('#3A1208', 0.85); ctx.strokeText(txt, x, y);
  const g = ctx.createLinearGradient(0, y - size / 2, 0, y + size / 2); g.addColorStop(0, C.goldHi); g.addColorStop(1, C.gold); ctx.fillStyle = g; ctx.fillText(txt, x, y);
  if (label) { ctx.font = `700 ${size * 0.26}px Caladea`; ctx.letterSpacing = `${size * 0.05}px`; ctx.fillStyle = C.cream; ctx.fillText(label, x, y + size * 0.62); ctx.letterSpacing = '0px'; }
  ctx.restore();
}
export function ribbon(text, x, y, size = 64, sc = 1, a = 1) {
  ctx.save(); ctx.translate(x, y); ctx.scale(sc, sc); ctx.globalAlpha *= a; ctx.font = `700 ${size}px Caladea`; ctx.letterSpacing = `${size * 0.08}px`;
  const w = ctx.measureText(text).width + size * 1.6, h = size * 1.7;
  ctx.fillStyle = C.crimson; ctx.beginPath(); ctx.moveTo(-w / 2 - 60, -h / 2 + 18); ctx.lineTo(-w / 2, -h / 2 + 18); ctx.lineTo(-w / 2, h / 2 + 18); ctx.lineTo(-w / 2 - 60, h / 2 + 18); ctx.lineTo(-w / 2 - 28, 18); ctx.closePath(); ctx.fill();
  ctx.beginPath(); ctx.moveTo(w / 2 + 60, -h / 2 + 18); ctx.lineTo(w / 2, -h / 2 + 18); ctx.lineTo(w / 2, h / 2 + 18); ctx.lineTo(w / 2 + 60, h / 2 + 18); ctx.lineTo(w / 2 + 28, 18); ctx.closePath(); ctx.fill();
  ctx.fillStyle = C.crimson; ctx.fillRect(-w / 2, -h / 2, w, h); ctx.strokeStyle = C.gold; ctx.lineWidth = 6; ctx.strokeRect(-w / 2 + 10, -h / 2 + 10, w - 20, h - 20);
  ctx.fillStyle = C.goldHi; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(text, 0, 4); ctx.letterSpacing = '0px'; ctx.restore();
}
export function tag(text, x, y, size = 40, a = 1) {
  ctx.save(); ctx.globalAlpha *= a; ctx.font = `700 ${size}px Caladea`; ctx.letterSpacing = `${size * 0.1}px`; const w = ctx.measureText(text).width + size * 1.4;
  ctx.fillStyle = 'rgba(30,8,20,0.72)'; ctx.beginPath(); ctx.roundRect(x - w / 2, y - size * 0.95, w, size * 1.9, size * 0.95); ctx.fill(); ctx.strokeStyle = C.gold; ctx.lineWidth = 3; ctx.stroke();
  ctx.fillStyle = C.goldHi; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(text, x, y + 2); ctx.letterSpacing = '0px'; ctx.restore();
}
export function stamp(text, x, y, size = 80, p = 1, rot = -0.08) {
  if (p <= 0) return; const sc = lerp(2.2, 1, eo(p)); ctx.save(); ctx.translate(x, y); ctx.rotate(rot); ctx.scale(sc, sc); ctx.globalAlpha *= clamp(p * 3);
  ctx.font = `700 ${size}px Caladea`; ctx.letterSpacing = `${size * 0.06}px`; const lines = text.split('\n'), w = Math.max(...lines.map((l) => ctx.measureText(l).width)) + size, h = lines.length * size * 1.1 + size * 0.7;
  ctx.strokeStyle = C.crimson; ctx.lineWidth = 12; ctx.strokeRect(-w / 2, -h / 2, w, h); ctx.lineWidth = 4; ctx.strokeRect(-w / 2 + 16, -h / 2 + 16, w - 32, h - 32);
  ctx.fillStyle = C.crimson; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; lines.forEach((l, i) => ctx.fillText(l, 0, (i - (lines.length - 1) / 2) * size * 1.1)); ctx.letterSpacing = '0px'; ctx.restore();
}
export function angerMarks(x, y, t, a = 1) { ctx.save(); ctx.globalAlpha *= a; ctx.strokeStyle = C.red; ctx.lineWidth = 12; ctx.lineCap = 'round'; const k = 1 + 0.12 * Math.sin(t * 16);
  for (const [dx, dy, r] of [[-60, -20, 0], [40, 10, 0.4]]) { ctx.save(); ctx.translate(x + dx, y + dy); ctx.scale(k, k); ctx.rotate(r); ctx.beginPath(); ctx.moveTo(-30, -10); ctx.quadraticCurveTo(-10, -10, -10, -30); ctx.moveTo(30, -10); ctx.quadraticCurveTo(10, -10, 10, -30); ctx.moveTo(-30, 10); ctx.quadraticCurveTo(-10, 10, -10, 30); ctx.moveTo(30, 10); ctx.quadraticCurveTo(10, 10, 10, 30); ctx.stroke(); ctx.restore(); } ctx.restore(); }
export function speedLines(x, y, a = 1, n = 14) { ctx.save(); ctx.globalAlpha *= a; ctx.strokeStyle = 'rgba(255,240,200,0.8)'; ctx.lineWidth = 6; for (let i = 0; i < n; i++) { const an = i / n * TAU + 0.2, r0 = 360 + rnd(i) * 120, r1 = r0 + 160 + rnd(i + 2) * 160; ctx.beginPath(); ctx.moveTo(x + Math.cos(an) * r0, y + Math.sin(an) * r0); ctx.lineTo(x + Math.cos(an) * r1, y + Math.sin(an) * r1); ctx.stroke(); } ctx.restore(); }

// ───────────────────────── props added for Istanbul 2461 ─────────────────────────
export function heart(x, y, s = 1, a = 1) {
  ctx.save(); ctx.translate(x, y); ctx.scale(s, s); ctx.globalAlpha *= a; ctx.beginPath(); ctx.moveTo(0, 34); ctx.bezierCurveTo(-70, -8, -46, -66, 0, -32); ctx.bezierCurveTo(46, -66, 70, -8, 0, 34); ctx.closePath();
  ctx.fillStyle = '#E0455A'; ctx.fill(); ctx.fillStyle = 'rgba(255,255,255,0.35)'; ctx.beginPath(); ctx.ellipse(-26, -22, 12, 7, -0.6, 0, TAU); ctx.fill(); ctx.restore();
}
/** flat lion head: gold face in a ring of mane tufts */
export function lion(x, y, s = 1, a = 1, t = 0) {
  ctx.save(); ctx.translate(x, y); ctx.scale(s, s); ctx.globalAlpha *= a; glow(0, 0, 360, 'rgba(255,200,110,0.8)', 0.5);
  for (let i = 0; i < 18; i++) { const an = i / 18 * TAU + Math.sin(t * 1.4 + i) * 0.03; ctx.save(); ctx.rotate(an); ell(0, -150, 38, 78, i % 2 ? '#8A4A14' : '#B5651D'); ctx.restore(); }
  circle(0, 0, 128, '#B5651D'); circle(-92, -96, 30, '#E3A94B'); circle(92, -96, 30, '#E3A94B'); circle(-92, -96, 14, '#8A4A14'); circle(92, -96, 14, '#8A4A14');
  ell(0, 8, 104, 112, '#E3A94B'); ell(0, 52, 56, 40, '#F2CD84');
  for (const sd of [-1, 1]) { ell(sd * 42, -16, 20, 12, '#F6EEDC'); circle(sd * 42, -15, 9, C.ink); circle(sd * 45, -19, 3, '#FFFFFF'); ctx.strokeStyle = '#8A4A14'; ctx.lineWidth = 9; ctx.lineCap = 'round'; ctx.beginPath(); ctx.moveTo(sd * 20, -44); ctx.lineTo(sd * 66, -50); ctx.stroke(); }
  ctx.beginPath(); ctx.moveTo(-22, 18); ctx.lineTo(22, 18); ctx.lineTo(0, 44); ctx.closePath(); ctx.fillStyle = '#7A3A30'; ctx.fill();
  ctx.strokeStyle = '#7A3A30'; ctx.lineWidth = 7; ctx.beginPath(); ctx.moveTo(0, 44); ctx.lineTo(0, 62); ctx.moveTo(-34, 62); ctx.quadraticCurveTo(-14, 82, 0, 62); ctx.quadraticCurveTo(14, 82, 34, 62); ctx.stroke();
  ctx.restore();
}
/** museum storage: dark wood shelves of small clay tablets; returns the centre of the tablet that can glow */
export function shelves(pan = 0, hiA = 0, hiCol = 3, hiRow = 1) {
  ctx.fillStyle = '#1E1018'; ctx.fillRect(-300, -300, W + 600, H + 600);
  const rows = [560, 840, 1120, 1400]; let hit = [540, 800];
  rows.forEach((y, r) => {
    for (let c = -3; c < 14; c++) {
      const k = r * 40 + c + 7, w = 104 + rnd(k) * 26, h = 66 + rnd(k + 3) * 34, x = c * 150 - pan + 20, top = y - h;
      const isHi = r === hiRow && c === hiCol; if (isHi) { hit = [x + w / 2, top + h / 2]; continue; }
      ctx.beginPath(); ctx.roundRect(x, top, w, h, 14); ctx.fillStyle = mix(C.clay, '#000000', 0.25 + rnd(k + 5) * 0.3); ctx.fill();
      ctx.fillStyle = 'rgba(40,20,16,0.5)'; for (let m = 0; m < 3; m++) ctx.fillRect(x + 16 + m * 28, top + 18 + rnd(k + m) * 14, 16, 5);
    }
    ctx.fillStyle = '#5A3228'; ctx.fillRect(-300, y, W + 600, 30); ctx.fillStyle = 'rgba(0,0,0,0.35)'; ctx.fillRect(-300, y + 30, W + 600, 16);
  });
  if (hiA > 0) glow(hit[0], hit[1], 300, 'rgba(255,215,140,0.95)', hiA);
  return hit;
}
export function qmark(x, y, s = 1, a = 1) {
  ctx.save(); ctx.translate(x, y); ctx.scale(s, s); ctx.globalAlpha *= a; ctx.font = '900 260px Inter'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.lineWidth = 22; ctx.strokeStyle = '#2A0F1C'; ctx.lineJoin = 'round'; ctx.strokeText('?', 0, 0); ctx.fillStyle = C.gold; ctx.fillText('?', 0, 0); ctx.restore();
}
