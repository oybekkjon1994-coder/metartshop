const fs = require('fs'); const { analyze } = require('../src/dxfcalc'); const d = require('../src/design');
let bad = 0; const ok = (name, cond, info) => { console.log((cond ? '✅ ' : '❌ ') + name, info || ''); if (!cond) bad++; };
// 1) LWPOLYLINE kvadrat 100x100 + doira r=50 + yoy (bulge) — mm
const lw = ['0','SECTION','2','HEADER','9','$INSUNITS','70','4','0','ENDSEC','0','SECTION','2','ENTITIES',
 '0','LWPOLYLINE','90','4','70','1','10','0','20','0','10','100','20','0','10','100','20','100','10','0','20','100',
 '0','CIRCLE','10','50','20','50','40','10',
 '0','LWPOLYLINE','90','2','70','0','10','200','20','0','42','1','10','300','20','0',
 '0','ENDSEC','0','EOF'].join('\n');
const a = analyze(lw);
const expect = 0.4 + 2 * Math.PI * 10 / 1000 + Math.PI * 50 / 1000;
ok('kvadrat+doira+yarim doira', Math.abs(a.meters - expect) < 0.002, a.meters.toFixed(4) + ' ~ ' + expect.toFixed(4));
ok("o'lcham", a.widthMm === 300, a.widthMm + 'x' + a.heightMm);
// 2) Blok (INSERT) 2x masshtab
const blk = ['0','SECTION','2','BLOCKS','0','BLOCK','2','KV','10','0','20','0','0','LINE','10','0','20','0','11','10','21','0','0','ENDBLK','0','ENDSEC',
 '0','SECTION','2','ENTITIES','0','INSERT','2','KV','10','5','20','5','41','2','42','2','0','ENDSEC','0','EOF'].join('\n');
ok('blok INSERT', Math.abs(analyze(blk).meters - 0.02) < 1e-6, analyze(blk).meters);
// 3) Botning o'z DXF chizmasi (R12 POLYLINE/VERTEX)
(async () => {
  const s = await d.makeShape(fs.readFileSync(__dirname + '/logo_white.jpg'));
  const x = await d.makeDxf(s, 400);
  const r = analyze(x.dxf), ref = d.cutLength(x.dxf);
  ok('R12 POLYLINE (bot chizmasi)', Math.abs(r.meters - ref) / ref < 0.02, r.meters.toFixed(3) + ' vs ' + ref.toFixed(3));
  try { analyze('salom'); ok("bo'sh fayl xato beradi", false); } catch { ok("bo'sh fayl xato beradi", true); }
  process.exit(bad ? 1 : 0);
})();
