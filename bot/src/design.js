// Mijoz yuborgan logotip/rasmdan: (1) lazer uchun bir butun siluet,
// (2) devordagi soat ko'rinishi (PNG), (3) DXF chizma yasaydi.
'use strict';
const sharp = require('sharp');

const WORK = 760;           // ishlov berish o'lchami (px)
const PREVIEW = 1080;       // ko'rinish rasmi o'lchami (px)

// ---------- yordamchi funksiyalar ----------
function otsu(data) {
  const hist = new Array(256).fill(0);
  for (const v of data) hist[v]++;
  const total = data.length;
  let sum = 0;
  for (let i = 0; i < 256; i++) sum += i * hist[i];
  let sumB = 0, wB = 0, best = 0, thr = 128;
  for (let t = 0; t < 256; t++) {
    wB += hist[t]; if (!wB) continue;
    const wF = total - wB; if (!wF) break;
    sumB += t * hist[t];
    const mB = sumB / wB, mF = (sum - sumB) / wF;
    const between = wB * wF * (mB - mF) * (mB - mF);
    if (between > best) { best = between; thr = t; }
  }
  return thr;
}

// 4-qo'shnili komponentlar
function label(mask, w, h, val = 1) {
  const lab = new Int32Array(w * h).fill(-1);
  const sizes = [];
  const q = new Int32Array(w * h);
  for (let i = 0; i < w * h; i++) {
    if (mask[i] !== val || lab[i] !== -1) continue;
    const id = sizes.length; let qh = 0, qt = 0, n = 0;
    q[qt++] = i; lab[i] = id;
    while (qh < qt) {
      const p = q[qh++]; n++;
      const x = p % w, y = (p - x) / w;
      if (x > 0 && mask[p - 1] === val && lab[p - 1] === -1) { lab[p - 1] = id; q[qt++] = p - 1; }
      if (x < w - 1 && mask[p + 1] === val && lab[p + 1] === -1) { lab[p + 1] = id; q[qt++] = p + 1; }
      if (y > 0 && mask[p - w] === val && lab[p - w] === -1) { lab[p - w] = id; q[qt++] = p - w; }
      if (y < h - 1 && mask[p + w] === val && lab[p + w] === -1) { lab[p + w] = id; q[qt++] = p + w; }
    }
    sizes.push(n);
  }
  return { lab, sizes };
}

function disc(mask, w, h, cx, cy, r, val = 1) {
  const r2 = r * r;
  for (let y = Math.max(0, Math.floor(cy - r)); y <= Math.min(h - 1, Math.ceil(cy + r)); y++)
    for (let x = Math.max(0, Math.floor(cx - r)); x <= Math.min(w - 1, Math.ceil(cx + r)); x++)
      if ((x - cx) ** 2 + (y - cy) ** 2 <= r2) mask[y * w + x] = val;
}

function thickLine(mask, w, h, x0, y0, x1, y1, r) {
  const n = Math.max(1, Math.ceil(Math.hypot(x1 - x0, y1 - y0)));
  for (let i = 0; i <= n; i++) disc(mask, w, h, x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n, r);
}

// Hamma bo'laklarni eng katta bo'lakka ko'prik bilan ulaydi (lazerda tushib qolmasligi uchun)
function bridge(mask, w, h, bridgeR) {
  for (let pass = 0; pass < 4; pass++) {
    const { lab, sizes } = label(mask, w, h, 1);
    if (sizes.length <= 1) return;
    let big = 0; sizes.forEach((s, i) => { if (s > sizes[big]) big = i; });
    // eng katta bo'lakdan BFS: har piksel uchun eng yaqin manba
    const dist = new Int32Array(w * h).fill(-1), src = new Int32Array(w * h).fill(-1);
    const q = new Int32Array(w * h); let qh = 0, qt = 0;
    for (let i = 0; i < w * h; i++) if (lab[i] === big) { dist[i] = 0; src[i] = i; q[qt++] = i; }
    while (qh < qt) {
      const p = q[qh++]; const x = p % w;
      const nb = [x > 0 ? p - 1 : -1, x < w - 1 ? p + 1 : -1, p - w >= 0 ? p - w : -1, p + w < w * h ? p + w : -1];
      for (const n of nb) if (n >= 0 && dist[n] === -1) { dist[n] = dist[p] + 1; src[n] = src[p]; q[qt++] = n; }
    }
    const best = new Map();
    for (let i = 0; i < w * h; i++) {
      const id = lab[i]; if (id < 0 || id === big) continue;
      const b = best.get(id); if (!b || dist[i] < dist[b]) best.set(id, i);
    }
    for (const p of best.values()) {
      const s = src[p];
      thickLine(mask, w, h, p % w, Math.floor(p / w), s % w, Math.floor(s / w), bridgeR);
    }
  }
}

// Shakl ichida kuchli kontrast bo'lsa (masalan oq-qizil chiziqli logotip), faqat bitta rang sinfini
// metall qilib qoldiramiz — aks holda logotip yaxlit dog' bo'lib qoladi. Qaysi sinf: shakl chetiga ko'proq tegadigani.
function refineInner(fg, lum, w, h) {
  const vals = []; for (let i = 0; i < w * h; i++) if (fg[i]) vals.push(lum[i]);
  const n = vals.length; if (n < 500) return fg;
  const t = otsu(vals);
  let nA = 0, sA = 0, sB = 0;
  for (const v of vals) { if (v < t) { nA++; sA += v; } else sB += v; }
  const nB = n - nA; if (Math.min(nA, nB) < n * 0.12) return fg;
  if (Math.abs(sA / Math.max(1, nA) - sB / Math.max(1, nB)) < 70) return fg;
  let edgeA = 0, edgeB = 0;
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const i = y * w + x; if (!fg[i]) continue;
    const edge = x === 0 || y === 0 || x === w - 1 || y === h - 1 || !fg[i - 1] || !fg[i + 1] || !fg[i - w] || !fg[i + w];
    if (edge) { if (lum[i] < t) edgeA++; else edgeB++; }
  }
  const keepDark = edgeA >= edgeB;
  const out = new Uint8Array(w * h);
  for (let i = 0; i < w * h; i++) out[i] = fg[i] && ((lum[i] < t) === keepDark) ? 1 : 0;
  return out;
}

// ---------- 1. Siluet ----------
async function makeShape(input) {
  const img = sharp(input, { failOn: 'none' }).rotate();
  const meta = await img.metadata();
  let base = img.resize(WORK, WORK, { fit: 'inside', withoutEnlargement: false });
  let fg, w, h;
  if (meta.hasAlpha) {
    const { data, info } = await base.clone().ensureAlpha().extractChannel('alpha').raw().toBuffer({ resolveWithObject: true });
    let transparent = 0; for (const v of data) if (v < 128) transparent++;
    if (transparent > data.length * 0.05) {
      w = info.width; h = info.height; fg = new Uint8Array(w * h);
      for (let i = 0; i < w * h; i++) fg[i] = data[i] >= 128 ? 1 : 0;
    }
  }
  const g = await base.clone().flatten({ background: '#ffffff' }).greyscale().blur(0.8).raw().toBuffer({ resolveWithObject: true });
  if (!fg) {
    const { data, info } = g;
    w = info.width; h = info.height;
    const t = otsu(data);
    const dark = new Uint8Array(w * h); for (let i = 0; i < w * h; i++) dark[i] = data[i] < t ? 1 : 0;
    let borderDark = 0, borderN = 0;
    for (let x = 0; x < w; x++) { borderDark += dark[x] + dark[(h - 1) * w + x]; borderN += 2; }
    for (let y = 0; y < h; y++) { borderDark += dark[y * w] + dark[y * w + w - 1]; borderN += 2; }
    const invert = borderDark / borderN > 0.5;
    fg = new Uint8Array(w * h); for (let i = 0; i < w * h; i++) fg[i] = invert ? 1 - dark[i] : dark[i];
  }
  if (g.info.width === w && g.info.height === h) fg = refineInner(fg, g.data, w, h);
  // kvadrat maydonga markazlab joylash (chekka bilan)
  const S = Math.round(Math.max(w, h) * 1.12);
  const ox = Math.floor((S - w) / 2), oy = Math.floor((S - h) / 2);
  const m = new Uint8Array(S * S);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) m[(y + oy) * S + x + ox] = fg[y * w + x];

  const area = S * S;
  // mayda dog'larni olib tashlash
  let L = label(m, S, S, 1);
  for (let i = 0; i < area; i++) if (m[i] && L.sizes[L.lab[i]] < area * 0.001) m[i] = 0;
  // juda mayda teshiklarni yopish (lazer kesa olmaydi)
  L = label(m, S, S, 0);
  for (let i = 0; i < area; i++) if (!m[i] && L.sizes[L.lab[i]] < area * 0.00025) m[i] = 1;

  // foydali qism chegarasi
  let x0 = S, y0 = S, x1 = 0, y1 = 0, cnt = 0;
  for (let y = 0; y < S; y++) for (let x = 0; x < S; x++) if (m[y * S + x]) { cnt++; if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
  if (cnt < area * 0.01) throw new Error('EMPTY');
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2, span = Math.max(x1 - x0, y1 - y0);
  // soat mexanizmi uchun markazda yaxlit doira + ko'priklar
  disc(m, S, S, cx, cy, span * 0.045, 1);
  bridge(m, S, S, Math.max(2, span * 0.008));
  return { mask: m, S, cx, cy, box: { x0, y0, x1, y1 }, span };
}

// ---------- 2. Ko'rinish (mockup) ----------
const COLORS = {
  qora: '#1c1c1f', oq: '#f2f2f0', kumush: '#b9bcc2', oltin: '#c9a24a',
  bordo: '#7a1730', qizil: '#c4201f', 'ko\'k': '#1f4fa8', yashil: '#1f6b3a', jigarrang: '#6b4a2b',
};

function shade(hex, k) {
  const n = parseInt(hex.slice(1), 16);
  const f = c => Math.max(0, Math.min(255, Math.round(c * k)));
  return '#' + [n >> 16, (n >> 8) & 255, n & 255].map(c => f(c).toString(16).padStart(2, '0')).join('');
}

async function makePreview(shape, colorName = 'qora', caption = '') {
  const P = PREVIEW, color = COLORS[colorName] || COLORS.qora;
  const light = ['oq', 'kumush', 'oltin'].includes(colorName);
  // siluetni ko'rinish o'lchamiga keltirish: bounding box ~ 78%
  const { mask, S, box } = shape;
  const bw = box.x1 - box.x0 + 1, bh = box.y1 - box.y0 + 1;
  const crop = new Uint8Array(bw * bh);
  for (let y = 0; y < bh; y++) for (let x = 0; x < bw; x++) crop[y * bw + x] = mask[(y + box.y0) * S + x + box.x0] ? 255 : 0;
  const scale = (P * 0.74) / Math.max(bw, bh);
  const tw = Math.max(1, Math.round(bw * scale)), th = Math.max(1, Math.round(bh * scale));
  const alpha = await sharp(Buffer.from(crop), { raw: { width: bw, height: bh, channels: 1 } })
    .resize(tw, th, { kernel: 'lanczos3' }).blur(0.6).extractChannel(0).raw().toBuffer();
  const left = Math.round((P - tw) / 2), top = Math.round((P - th) / 2 - P * 0.02);

  const rgbaFrom = (rgb, a, opacity = 1) => {
    const out = Buffer.alloc(tw * th * 4);
    for (let i = 0; i < tw * th; i++) { out[i * 4] = rgb[0]; out[i * 4 + 1] = rgb[1]; out[i * 4 + 2] = rgb[2]; out[i * 4 + 3] = Math.round(a[i] * opacity); }
    return sharp(out, { raw: { width: tw, height: th, channels: 4 } });
  };
  const hex2 = h => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];

  // devor
  const wallTop = light ? '#4a4d55' : '#e9e4dc', wallBot = light ? '#2a2c31' : '#cfc7bb';
  const wall = Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="${P}" height="${P}">
    <defs><radialGradient id="g" cx="50%" cy="42%" r="75%"><stop offset="0" stop-color="${wallTop}"/><stop offset="1" stop-color="${wallBot}"/></radialGradient>
    <filter id="n"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="4"/><feColorMatrix type="saturate" values="0"/><feComponentTransfer><feFuncA type="linear" slope="0.10"/></feComponentTransfer></filter></defs>
    <rect width="100%" height="100%" fill="url(#g)"/><rect width="100%" height="100%" filter="url(#n)"/></svg>`);

  // soya
  const shadow = await rgbaFrom([0, 0, 0], alpha, light ? 0.75 : 0.45).png().toBuffer();
  const shadowBlur = await sharp(shadow).extend({ top: 40, bottom: 40, left: 40, right: 40, background: { r: 0, g: 0, b: 0, alpha: 0 } }).blur(9).png().toBuffer();
  // metall: gradient yaltirash
  const grad = Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="${tw}" height="${th}"><defs><linearGradient id="m" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="${shade(color, 1.35)}"/><stop offset="0.45" stop-color="${color}"/><stop offset="1" stop-color="${shade(color, 0.7)}"/></linearGradient></defs>
    <rect width="100%" height="100%" fill="url(#m)"/></svg>`);
  const rgb = await sharp(grad).resize(tw, th).removeAlpha().raw().toBuffer();
  const metalRaw = Buffer.alloc(tw * th * 4);
  for (let i = 0; i < tw * th; i++) { metalRaw[i * 4] = rgb[i * 3]; metalRaw[i * 4 + 1] = rgb[i * 3 + 1]; metalRaw[i * 4 + 2] = rgb[i * 3 + 2]; metalRaw[i * 4 + 3] = alpha[i]; }
  const metalRGBA = await sharp(metalRaw, { raw: { width: tw, height: th, channels: 4 } }).png().toBuffer();

  // soat millari (markaz = siluet markazi)
  const cxP = left + (shape.cx - box.x0) * scale, cyP = top + (shape.cy - box.y0) * scale;
  const R = shape.span * scale * 0.5;
  const handCol = light ? '#111' : (colorName === 'qora' ? '#e8e8e8' : '#111');
  const hand = (ang, len, wdt, col) => {
    const a = (ang - 90) * Math.PI / 180;
    return `<line x1="${cxP - Math.cos(a) * len * 0.15}" y1="${cyP - Math.sin(a) * len * 0.15}" x2="${cxP + Math.cos(a) * len}" y2="${cyP + Math.sin(a) * len}" stroke="${col}" stroke-width="${wdt}" stroke-linecap="round"/>`;
  };
  const hands = Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="${P}" height="${P}">
    <g filter="drop-shadow(3px 4px 3px rgba(0,0,0,.45))">
    ${hand(305, R * 0.42, R * 0.045, handCol)}${hand(60, R * 0.62, R * 0.03, handCol)}${hand(200, R * 0.66, R * 0.012, '#d61f1f')}
    <circle cx="${cxP}" cy="${cyP}" r="${R * 0.035}" fill="#c9a24a"/></g>
    <rect x="0" y="${P - 64}" width="${P}" height="64" fill="rgba(0,0,0,.55)"/>
    <text x="28" y="${P - 22}" font-family="Inter, DejaVu Sans, Arial" font-size="26" font-weight="700" fill="#FFC21A">METARTSHOP</text>
    <text x="${P - 28}" y="${P - 22}" text-anchor="end" font-family="Inter, DejaVu Sans, Arial" font-size="24" fill="#fff">${escapeXml(caption)}</text></svg>`);

  return sharp(wall).composite([
    { input: shadowBlur, left: left - 40 + 16, top: top - 40 + 22 },
    { input: metalRGBA, left, top },
    { input: hands, left: 0, top: 0 },
  ]).jpeg({ quality: 90 }).toBuffer();
}

function escapeXml(s) { return String(s).replace(/[<>&"']/g, c => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;', "'": '&apos;' }[c])); }

// ---------- 3. DXF ----------
// Marching squares (chiziqli interpolyatsiya bilan) -> yopiq konturlar
function contours(field, w, h, iso) {
  const v = (x, y) => (x < 0 || y < 0 || x >= w || y >= h) ? 0 : field[y * w + x];
  const segs = new Map(); // edgeKey -> [otherKey, point]
  const pts = new Map();
  const ek = {
    t: (x, y) => `h${x},${y}`, b: (x, y) => `h${x},${y + 1}`,
    l: (x, y) => `v${x},${y}`, r: (x, y) => `v${x + 1},${y}`,
  };
  const interp = (x0, y0, x1, y1) => {
    const a = v(x0, y0), b = v(x1, y1); const t = (iso - a) / ((b - a) || 1e-9);
    return [x0 + (x1 - x0) * t, y0 + (y1 - y0) * t];
  };
  const P = {
    t: (x, y) => interp(x, y, x + 1, y), b: (x, y) => interp(x, y + 1, x + 1, y + 1),
    l: (x, y) => interp(x, y, x, y + 1), r: (x, y) => interp(x + 1, y, x + 1, y + 1),
  };
  const add = (x, y, e1, e2) => {
    const k1 = ek[e1](x, y), k2 = ek[e2](x, y);
    pts.set(k1, P[e1](x, y)); pts.set(k2, P[e2](x, y));
    (segs.get(k1) || segs.set(k1, []).get(k1)).push(k2);
    (segs.get(k2) || segs.set(k2, []).get(k2)).push(k1);
  };
  for (let y = -1; y < h; y++) for (let x = -1; x < w; x++) {
    const tl = v(x, y) >= iso, tr = v(x + 1, y) >= iso, br = v(x + 1, y + 1) >= iso, bl = v(x, y + 1) >= iso;
    const c = (tl ? 8 : 0) | (tr ? 4 : 0) | (br ? 2 : 0) | (bl ? 1 : 0);
    switch (c) {
      case 1: case 14: add(x, y, 'l', 'b'); break;
      case 2: case 13: add(x, y, 'b', 'r'); break;
      case 3: case 12: add(x, y, 'l', 'r'); break;
      case 4: case 11: add(x, y, 't', 'r'); break;
      case 6: case 9: add(x, y, 't', 'b'); break;
      case 7: case 8: add(x, y, 'l', 't'); break;
      case 5: case 10: {
        const center = (v(x, y) + v(x + 1, y) + v(x + 1, y + 1) + v(x, y + 1)) / 4 >= iso;
        if ((c === 5) === center) { add(x, y, 'l', 't'); add(x, y, 'b', 'r'); }
        else { add(x, y, 'l', 'b'); add(x, y, 't', 'r'); }
      }
    }
  }
  const loops = [], used = new Set();
  for (const start of segs.keys()) {
    if (used.has(start)) continue;
    const loop = []; let prev = null, cur = start;
    while (cur && !used.has(cur)) {
      used.add(cur); loop.push(pts.get(cur));
      const nx = segs.get(cur).find(k => k !== prev && !used.has(k));
      prev = cur; cur = nx;
    }
    if (loop.length >= 3) loops.push(loop);
  }
  return loops;
}

function simplify(pts, eps) {
  if (pts.length < 4) return pts;
  const keep = new Uint8Array(pts.length); keep[0] = keep[pts.length - 1] = 1;
  const stack = [[0, pts.length - 1]];
  while (stack.length) {
    const [a, b] = stack.pop(); let md = 0, mi = -1;
    const [ax, ay] = pts[a], [bx, by] = pts[b]; const L = Math.hypot(bx - ax, by - ay) || 1e-9;
    for (let i = a + 1; i < b; i++) {
      const d = Math.abs((bx - ax) * (ay - pts[i][1]) - (ax - pts[i][0]) * (by - ay)) / L;
      if (d > md) { md = d; mi = i; }
    }
    if (md > eps) { keep[mi] = 1; stack.push([a, mi], [mi, b]); }
  }
  return pts.filter((_, i) => keep[i]);
}

function simplifyClosed(pts, eps) {
  let far = 0, md = -1;
  for (let i = 1; i < pts.length; i++) { const d = Math.hypot(pts[i][0] - pts[0][0], pts[i][1] - pts[0][1]); if (d > md) { md = d; far = i; } }
  const a = simplify(pts.slice(0, far + 1), eps), b = simplify(pts.slice(far).concat([pts[0]]), eps);
  return a.concat(b.slice(1, -1));
}

// Kvadrat yadroli eroziya/dilatsiya (ajraluvchi, O(n))
function morph(src, w, h, r, dilate) {
  const pass = (a, horiz) => {
    const out = new Uint8Array(w * h);
    const n = horiz ? w : h, m = horiz ? h : w;
    for (let j = 0; j < m; j++) {
      const idx = i => horiz ? j * w + i : i * w + j;
      for (let i = 0; i < n; i++) {
        let v = dilate ? 0 : 1;
        for (let k = Math.max(0, i - r); k <= Math.min(n - 1, i + r); k++) {
          const s = a[idx(k)];
          if (dilate ? s : !s) { v = dilate ? 1 : 0; break; }
        }
        if (!dilate && (i - r < 0 || i + r > n - 1)) v = 0;
        out[idx(i)] = v;
      }
    }
    return out;
  };
  return pass(pass(src, true), false);
}

// Lazer kesa oladigan eng kichik kenglik (mm). Undan ingichka joylar qalinlashtiriladi.
const MIN_WIDTH_MM = 1.5;

async function makeDxf(shape, sizeMm) {
  const { mask, S, box } = shape;
  const pad = 3, bw = box.x1 - box.x0 + 1 + pad * 2, bh = box.y1 - box.y0 + 1 + pad * 2;
  const bin = new Uint8Array(bw * bh);
  for (let y = 0; y < bh; y++) for (let x = 0; x < bw; x++) {
    const sx = x - pad + box.x0, sy = y - pad + box.y0;
    bin[y * bw + x] = (sx >= 0 && sy >= 0 && sx < S && sy < S && mask[sy * S + sx]) ? 1 : 0;
  }
  // ingichka joylarni topib qalinlashtirish: opening = eroziya+dilatsiya; mask - opening = ingichka
  const pxMm = sizeMm / Math.max(bw - pad * 2, bh - pad * 2);
  const r = Math.max(1, Math.ceil((MIN_WIDTH_MM / 2) / pxMm) - 1);
  const opened = morph(morph(bin, bw, bh, r, false), bw, bh, r, true);
  const thinMask = new Uint8Array(bw * bh); let thinCount = 0;
  for (let i = 0; i < bw * bh; i++) if (bin[i] && !opened[i]) { thinMask[i] = 1; thinCount++; }
  let thin = '';
  if (thinCount > 0) {
    const grown = morph(thinMask, bw, bh, r, true);
    for (let i = 0; i < bw * bh; i++) if (grown[i]) bin[i] = 1;
    thin = `${Math.round(thinCount * pxMm * pxMm)} mm²`;
  }
  const crop = Buffer.alloc(bw * bh);
  for (let i = 0; i < bw * bh; i++) crop[i] = bin[i] ? 255 : 0;
  const up = 2; // silliq kontur uchun 2x
  const W2 = bw * up, H2 = bh * up;
  const field = await sharp(crop, { raw: { width: bw, height: bh, channels: 1 } }).resize(W2, H2, { kernel: 'cubic' }).blur(1.1).extractChannel(0).raw().toBuffer();
  const loops = contours(field, W2, H2, 128);
  const mmPerPx = sizeMm / (Math.max(bw - pad * 2, bh - pad * 2) * up);
  const out = [];
  const add = (...a) => out.push(...a.map(String));
  add(0, 'SECTION', 2, 'HEADER', 9, '$ACADVER', 1, 'AC1009', 9, '$INSUNITS', 70, 4, 0, 'ENDSEC');
  add(0, 'SECTION', 2, 'ENTITIES');
  let n = 0;
  for (const raw of loops) {
    const lp = simplifyClosed(raw, 0.5);
    if (lp.length < 3) continue;
    n++;
    add(0, 'POLYLINE', 8, 'KESISH', 66, 1, 10, '0.0', 20, '0.0', 30, '0.0', 70, 1);
    for (const [x, y] of lp) add(0, 'VERTEX', 8, 'KESISH', 10, ((x - pad * up) * mmPerPx).toFixed(3), 20, ((H2 - y - pad * up) * mmPerPx).toFixed(3));
    add(0, 'SEQEND', 8, 'KESISH');
  }
  // soat mexanizmi teshigi (d=8 mm)
  const cxMm = (shape.cx - box.x0) * up * mmPerPx, cyMm = (bh * up - (shape.cy - box.y0 + pad) * up - pad * up) * mmPerPx;
  add(0, 'CIRCLE', 8, 'KESISH', 10, cxMm.toFixed(3), 20, cyMm.toFixed(3), 40, 4);
  add(0, 'ENDSEC', 0, 'EOF');
  const wMm = (bw - pad * 2) * up * mmPerPx, hMm = (bh - pad * 2) * up * mmPerPx;
  return { dxf: out.join('\r\n') + '\r\n', contours: n, widthMm: Math.round(wMm), heightMm: Math.round(hMm), thin };
}

// Kesish uzunligi (metr) — narxni tekshirish uchun foydali
function cutLength(dxfText) {
  const lines = dxfText.split(/\r?\n/); let len = 0, prev = null, first = null;
  for (let i = 0; i < lines.length - 1; i++) {
    const v = lines[i + 1].trim();
    if (lines[i].trim() === '0' && v === 'POLYLINE') { prev = null; first = null; }
    if (lines[i].trim() === '0' && v === 'SEQEND' && prev && first) { len += Math.hypot(first[0] - prev[0], first[1] - prev[1]); prev = null; }
    if (lines[i].trim() === '0' && v === 'VERTEX') {
      const x = parseFloat(lines[i + 5]), y = parseFloat(lines[i + 7]);
      if (prev) len += Math.hypot(x - prev[0], y - prev[1]); else first = [x, y];
      prev = [x, y];
    }
  }
  return len / 1000;
}

module.exports = { makeShape, makePreview, makeDxf, cutLength, COLORS };
