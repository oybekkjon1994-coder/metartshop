// DXF fayldan lazer kesish uzunligini (metr) va o'lchamlarini hisoblaydi.
// Qo'llab-quvvatlanadi: LINE, LWPOLYLINE (bulge bilan), POLYLINE/VERTEX, CIRCLE, ARC, ELLIPSE, SPLINE (taxminiy), INSERT (bloklar).
'use strict';

function pairs(text) {
  const lines = text.split(/\r?\n/);
  const out = [];
  for (let i = 0; i + 1 < lines.length; i += 2) out.push([parseInt(lines[i].trim(), 10), lines[i + 1].trim()]);
  return out;
}

// Bo'limlarga va obyektlarga ajratish
function parse(text) {
  const p = pairs(text);
  const blocks = {}; const entities = []; let units = 0;
  let section = null, cur = null, curBlock = null, inBlockList = false;
  const flush = () => { if (cur) { (curBlock ? curBlock.ents : entities).push(cur); cur = null; } };
  for (let i = 0; i < p.length; i++) {
    const [c, v] = p[i];
    if (c === 0) {
      if (v === 'SECTION') { flush(); const n = p[i + 1]; section = n && n[0] === 2 ? n[1] : null; i++; continue; }
      if (v === 'ENDSEC') { flush(); section = null; curBlock = null; continue; }
      if (section === 'BLOCKS') {
        if (v === 'BLOCK') { flush(); curBlock = { name: '', ents: [], bx: 0, by: 0 }; inBlockList = true; continue; }
        if (v === 'ENDBLK') { flush(); if (curBlock && curBlock.name) blocks[curBlock.name] = curBlock; curBlock = null; inBlockList = false; continue; }
      }
      if (section === 'ENTITIES' || (section === 'BLOCKS' && curBlock)) {
        flush(); inBlockList = false;
        cur = { type: v, g: [] };
        continue;
      }
      continue;
    }
    if (section === 'HEADER' && c === 9 && v === '$INSUNITS') { const n = p[i + 1]; if (n && n[0] === 70) units = parseInt(n[1], 10) || 0; }
    if (inBlockList && curBlock && !cur) {
      if (c === 2) curBlock.name = v; else if (c === 10) curBlock.bx = +v; else if (c === 20) curBlock.by = +v;
      continue;
    }
    if (cur) cur.g.push([c, v]);
  }
  flush();
  return { entities, blocks, units };
}

const num = (g, code, def = 0) => { const x = g.find(e => e[0] === code); return x ? +x[1] : def; };
const all = (g, code) => g.filter(e => e[0] === code).map(e => +e[1]);

// Har bir obyektni nuqtalar ketma-ketligiga (poliliniyaga) aylantiramiz
function arcPts(cx, cy, r, a0, a1, segs) {
  let da = a1 - a0; if (da <= 0) da += Math.PI * 2;
  const n = Math.max(4, Math.ceil(segs * da / (Math.PI * 2)));
  const pts = []; for (let i = 0; i <= n; i++) { const a = a0 + da * i / n; pts.push([cx + r * Math.cos(a), cy + r * Math.sin(a)]); }
  return pts;
}
function bulgePts(x0, y0, x1, y1, b) {
  if (!b) return [[x1, y1]];
  const th = 4 * Math.atan(b), d = Math.hypot(x1 - x0, y1 - y0); if (!d) return [[x1, y1]];
  const r = d / (2 * Math.sin(th / 2));
  const mx = (x0 + x1) / 2, my = (y0 + y1) / 2;
  const h = r * Math.cos(th / 2);
  const ux = -(y1 - y0) / d, uy = (x1 - x0) / d;
  const cx = mx + ux * h * Math.sign(b), cy = my + uy * h * Math.sign(b);
  const a0 = Math.atan2(y0 - cy, x0 - cx);
  const n = Math.max(4, Math.ceil(Math.abs(th) / (Math.PI / 24)));
  const pts = []; for (let i = 1; i <= n; i++) { const a = a0 + th * i / n; pts.push([cx + Math.abs(r) * Math.cos(a), cy + Math.abs(r) * Math.sin(a)]); }
  return pts;
}

function entityPaths(e, blocks, depth = 0) {
  const g = e.g;
  switch (e.type) {
    case 'LINE': return [[[num(g, 10), num(g, 20)], [num(g, 11), num(g, 21)]]];
    case 'CIRCLE': { const r = num(g, 40); return r > 0 ? [arcPts(num(g, 10), num(g, 20), r, 0, Math.PI * 2, 96)] : []; }
    case 'ARC': { const r = num(g, 40); return r > 0 ? [arcPts(num(g, 10), num(g, 20), r, num(g, 50) * Math.PI / 180, num(g, 51) * Math.PI / 180, 96)] : []; }
    case 'ELLIPSE': {
      const cx = num(g, 10), cy = num(g, 20), mx = num(g, 11), my = num(g, 21), ratio = num(g, 40, 1);
      let t0 = num(g, 41, 0), t1 = num(g, 42, Math.PI * 2); if (t1 <= t0) t1 += Math.PI * 2;
      const a = Math.hypot(mx, my), rot = Math.atan2(my, mx), b = a * ratio, n = 96;
      const pts = []; for (let i = 0; i <= n; i++) { const t = t0 + (t1 - t0) * i / n; const x = a * Math.cos(t), y = b * Math.sin(t); pts.push([cx + x * Math.cos(rot) - y * Math.sin(rot), cy + x * Math.sin(rot) + y * Math.cos(rot)]); }
      return [pts];
    }
    case 'LWPOLYLINE': {
      const closed = (num(g, 70) & 1) === 1; const verts = []; let v = null;
      for (const [c, val] of g) { if (c === 10) { v = { x: +val, y: 0, b: 0 }; verts.push(v); } else if (v && c === 20) v.y = +val; else if (v && c === 42) v.b = +val; }
      if (verts.length < 2) return [];
      const pts = [[verts[0].x, verts[0].y]];
      const last = closed ? verts.length : verts.length - 1;
      for (let i = 0; i < last; i++) { const a = verts[i], b = verts[(i + 1) % verts.length]; pts.push(...bulgePts(a.x, a.y, b.x, b.y, a.b)); }
      return [pts];
    }
    case 'SPLINE': {
      // Taxminiy: fit nuqtalari bo'lsa ular, aks holda nazorat nuqtalari bo'yicha (biroz uzunroq chiqadi)
      const fx = all(g, 11), fy = all(g, 21), cx = all(g, 10), cy = all(g, 20);
      const xs = fx.length > 1 ? fx : cx, ys = fx.length > 1 ? fy : cy;
      const pts = xs.map((x, i) => [x, ys[i] || 0]);
      if ((num(g, 70) & 1) && pts.length) pts.push(pts[0]);
      return pts.length > 1 ? [pts] : [];
    }
    case 'INSERT': {
      if (depth > 4) return [];
      const name = (g.find(x => x[0] === 2) || [])[1]; const blk = blocks[name]; if (!blk) return [];
      const ix = num(g, 10), iy = num(g, 20), sx = num(g, 41, 1), sy = num(g, 42, 1), rot = num(g, 50) * Math.PI / 180;
      const cs = Math.cos(rot), sn = Math.sin(rot);
      const out = [];
      for (const be of blk.ents) for (const path of entityPaths(be, blocks, depth + 1)) {
        out.push(path.map(([x, y]) => { const X = (x - blk.bx) * sx, Y = (y - blk.by) * sy; return [ix + X * cs - Y * sn, iy + X * sn + Y * cs]; }));
      }
      return out;
    }
    default: return [];
  }
}

// POLYLINE + VERTEX ... SEQEND ketma-ketligini yig'ish
function joinOldPolylines(ents) {
  const out = []; let pl = null;
  for (const e of ents) {
    if (e.type === 'POLYLINE') { pl = { type: 'LWPOLYLINE', g: [[70, String(num(e.g, 70))]] }; continue; }
    if (pl && e.type === 'VERTEX') { pl.g.push([10, String(num(e.g, 10))], [20, String(num(e.g, 20))], [42, String(num(e.g, 42))]); continue; }
    if (pl && e.type === 'SEQEND') { out.push(pl); pl = null; continue; }
    out.push(e);
  }
  if (pl) out.push(pl);
  return out;
}

const UNIT_MM = { 1: 25.4, 2: 304.8, 4: 1, 5: 10, 6: 1000 };

function analyze(text) {
  const { entities, blocks, units } = parse(text);
  for (const b of Object.values(blocks)) b.ents = joinOldPolylines(b.ents);
  const ents = joinOldPolylines(entities);
  const k = UNIT_MM[units] || 1;
  let len = 0, x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity, paths = 0;
  for (const e of ents) for (const p of entityPaths(e, blocks)) {
    paths++;
    for (let i = 0; i < p.length; i++) {
      const [x, y] = p[i];
      if (x < x0) x0 = x; if (y < y0) y0 = y; if (x > x1) x1 = x; if (y > y1) y1 = y;
      if (i) len += Math.hypot(x - p[i - 1][0], y - p[i - 1][1]);
    }
  }
  if (!paths || !isFinite(x0)) throw new Error('EMPTY_DXF');
  return { meters: len * k / 1000, widthMm: Math.round((x1 - x0) * k), heightMm: Math.round((y1 - y0) * k), paths };
}

module.exports = { analyze };
