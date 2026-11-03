// Epic Frame engine: canvas, palette, math and drawing primitives.
// Every drawing function in the kit uses the shared `ctx` exported here (set once by main.js).
export const W = 1080, H = 1920, FPS = 30;
export let ctx = null;
export function setCtx(c) { ctx = c; }

// Epic Frame palette: warm saffron / amber / maroon world, gold trim, lapis and crimson cloth. Gradients are allowed
// (soft sky + glow), characters stay flat with one darker shade and one highlight.
export const C = {
  saffron: '#F0A94E', amber: '#D9803A', sun: '#F8CD78', sunHot: '#FFE9B0', dusk: '#B4552F', maroon: '#6B2433', wine: '#3E1626',
  night: '#1A1730', indigo: '#2B2A5E', violet: '#4B3A7A', gold: '#EBBC4E', goldDark: '#B5832A', goldHi: '#FFE08A',
  skinL: '#E0A97C', skinM: '#C58A5C', skinD: '#8E5C3E', skinShade: 'rgba(60,25,10,0.22)',
  hair: '#1F1512', beardW: '#F0EBE0', lapis: '#2F58A8', lapisDark: '#22418A', turq: '#36A8A0', crimson: '#B3263A', cream: '#EFE3C8', creamDark: '#CDBE9C',
  clay: '#C99A5B', clayDark: '#9E7240', clayHi: '#E2BC80', copper: '#D9733A', copperHi: '#F0A064', verdigris: '#6FA58C', verdigrisDark: '#4A7E69',
  ink: '#1A1014', white: '#FFFFFF', red: '#D62839', stone: '#8A7660', stoneDark: '#5E4F40',
};

// ---------- math ----------
export const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
export const lerp = (a, b, t) => a + (b - a) * t;
export const seg = (t, a, b) => clamp((t - a) / ((b - a) || 1e-6));
export const eo = (t) => 1 - Math.pow(1 - t, 3);
export const eio = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
export const eob = (t) => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2); };
export const rnd = (i) => { const x = Math.sin(i * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };
export const TAU = Math.PI * 2;

// ---------- primitives ----------
export function rr(x, y, w, h, r) { ctx.beginPath(); ctx.roundRect(x, y, w, h, r); }
export function circle(x, y, r, fill) { ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.fillStyle = fill; ctx.fill(); }
export function ell(x, y, rx, ry, fill, rot = 0) { ctx.beginPath(); ctx.ellipse(x, y, rx, ry, rot, 0, TAU); ctx.fillStyle = fill; ctx.fill(); }
export function line(pts, color, w) {
  ctx.beginPath(); ctx.moveTo(pts[0][0], pts[0][1]);
  for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
  ctx.strokeStyle = color; ctx.lineWidth = w; ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.stroke();
}
export function fillAll(color) { ctx.fillStyle = color; ctx.fillRect(-300, -300, W + 600, H + 600); }
/** outlined bold text (the caption look), centred at x, y */
export function bigText(text, x, y, size, fill = C.white, rot = 0, sc = 1) {
  ctx.save(); ctx.translate(x, y); ctx.rotate(rot); ctx.scale(sc, sc);
  ctx.font = `900 ${size}px Inter`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.lineJoin = 'round';
  ctx.lineWidth = size * 0.2; ctx.strokeStyle = C.ink; ctx.strokeText(text, 0, 0); ctx.fillStyle = fill; ctx.fillText(text, 0, 0);
  ctx.restore();
}

// ---------- gradients / glow ----------
export function vgrad(stops, y0 = -300, y1 = H + 300) {
  const g = ctx.createLinearGradient(0, y0, 0, y1); stops.forEach(([p, c]) => g.addColorStop(p, c)); return g;
}
export function skyFill(stops) { ctx.fillStyle = vgrad(stops); ctx.fillRect(-300, -300, W + 600, H + 600); }
export function glow(x, y, r, color, alpha = 1) {
  const g = ctx.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, color); g.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.save(); ctx.globalAlpha *= alpha; ctx.fillStyle = g; ctx.fillRect(x - r, y - r, r * 2, r * 2); ctx.restore();
}
export function hexA(hex, a) { const n = parseInt(hex.slice(1), 16); return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${a})`; }
export function mix(c1, c2, t) {
  const a = parseInt(c1.slice(1), 16), b = parseInt(c2.slice(1), 16), f = (s) => Math.round(((a >> s) & 255) * (1 - t) + ((b >> s) & 255) * t);
  return `rgb(${f(16)},${f(8)},${f(0)})`;
}
