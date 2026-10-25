// Avtomatik takliflarni sinash: tayyor holatdagi foydalanuvchilar bilan
const http = require('http'), fs = require('fs'), path = require('path'), { spawn } = require('child_process');
const DATA = path.join(__dirname, 'data_offers'); fs.rmSync(DATA, { recursive: true, force: true }); fs.mkdirSync(DATA);
const now = Date.now(), H = 3600e3, D = 24 * H, iso = t => new Date(t).toISOString();
const base = (id, extra) => ({ id, lang: 'uz', name: 'U' + id, joined: iso(now - 10 * D), lastSeen: now - 5 * H, s: {}, ...extra });
const users = {
  1: base(1, { s: { flow: 'product', step: 'phone', pid: 'barselona-soat', title: 'Barselona devor soati', price: 150000, qty: 1, name: 'A' }, sAt: now - 3 * H }),
  2: base(2, { viewed: { pid: 'barselona-soat', at: now - 21 * H, offered: false } }),
  3: base(3, {}),
  4: base(4, { ordered: now - 40 * D, orderedPids: ['barselona-soat'], lang: 'ru' }),
  5: base(5, { optOut: true }),
  6: base(6, { lastSeen: now - 5 * 60e3 }), // hozir botda
  7: base(7, { joined: iso(now - 1 * D) }),   // yangi
};
fs.writeFileSync(path.join(DATA, 'users.json'), JSON.stringify(users));
fs.writeFileSync(path.join(DATA, 'state.json'), JSON.stringify({ offset: 0, admins: [999], orderSeq: 0 }));
const log = [];
const srv = http.createServer((req, res) => { let b = ''; req.on('data', c => b += c); req.on('end', () => {
  const m = req.url.split('/').pop(); const p = b && req.headers['content-type'].includes('json') ? JSON.parse(b) : {};
  if (m === 'getUpdates') return setTimeout(() => res.end('{"ok":true,"result":[]}'), 400);
  if (m === 'getMe') return res.end('{"ok":true,"result":{"username":"t"}}');
  if (/^send/.test(m)) { const kb = p.reply_markup ? p.reply_markup.inline_keyboard.flat().map(x => x.text).join(' | ') : ''; log.push(`${m} → ${p.chat_id}: ${String(p.text || p.caption).replace(/\n/g, ' ¶ ').slice(0, 170)} [${kb}]`); }
  res.end('{"ok":true,"result":{"message_id":1}}');
}); });
srv.listen(18081, () => {
  const bot = spawn('node', [path.join(__dirname, '..', 'src', 'bot.js')], { env: { ...process.env, BOT_TOKEN: 'T:T', TG_API: 'http://127.0.0.1:18081', DATA_DIR: DATA, OFFERS_NOW: '1', HOLIDAY_TODAY: process.env.HOLIDAY_TODAY || '06-15' }, stdio: 'inherit' });
  setTimeout(() => { bot.kill(); srv.close(); console.log(log.join('\n')); const ids = log.map(l => +l.split('→ ')[1].split(':')[0]).sort().join(','); console.log('Kimga yuborildi:', ids); if (process.env.HOLIDAY_TODAY) { const h = log.filter(l => /yaqinlashmoqda|Скоро/.test(l)).length; console.log('Bayram xabarlari:', h); process.exit(ids === '1,2,3,4,7,999' && h === 4 && /Bayram aksiyasi boshlandi/.test(log.join()) ? 0 : 1); }
    process.exit(ids === '1,2,3,4' ? 0 : 1); }, 5000);
});
