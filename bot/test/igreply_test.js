// Instagram izohlariga avtomatik javob: soxta Graph API bilan sinov
const http = require('http'); const ig = require('../src/igreply');
const now = new Date().toISOString(), old = new Date(Date.now() - 5 * 864e5).toISOString();
const posts = [];
const srv = http.createServer((req, res) => {
  let b = ''; req.on('data', c => b += c); req.on('end', () => {
    const u = new URL(req.url, 'http://x'); const send = j => res.end(JSON.stringify(j));
    if (u.pathname === '/me') return send({ id: 'PAGE', instagram_business_account: { id: 'IG1', username: 'metart_shop' } });
    if (u.pathname === '/IG1/media') return send({ data: [{ id: 'M1', caption: 'Barselona soati 150 000', permalink: 'https://instagram.com/p/x' }] });
    if (u.pathname === '/M1/comments') return send({ data: [
      { id: 'C1', text: 'Narxi qancha?', username: 'ali', timestamp: now },
      { id: 'C2', text: 'rahmat', username: 'metart_shop', timestamp: now },
      { id: 'C3', text: 'Follow me @spam', username: 'bot1', timestamp: now },
      { id: 'C4', text: 'Сколько стоит?', username: 'ivan', timestamp: now, replies: { data: [{ username: 'metart_shop' }] } },
      { id: 'C5', text: 'eski', username: 'old', timestamp: old },
    ] });
    if (/\/replies$/.test(u.pathname) && req.method === 'POST') { posts.push([u.pathname, new URLSearchParams(b).get('message')]); return send({ id: 'R' }); }
    res.statusCode = 404; send({ error: { message: 'nf', code: 100 } });
  });
});
srv.listen(18082, async () => {
  const db = { state: {}, save() {} }; const notes = []; const asked = [];
  const bot = ig.create({ token: 't', api: 'http://127.0.0.1:18082', db, notify: m => notes.push(m), log: { log() {}, error: console.error },
    ai: async (text) => { asked.push(text); return /spam/.test(text) ? 'SKIP' : 'Narxi 150 000 so\'m 🔥 Buyurtma: @Metart_shop_bot [[p:x]]'; } });
  const n1 = await bot.tick(), n2 = await bot.tick();
  srv.close();
  const ok = n1 === 1 && n2 === 0 && posts.length === 1 && posts[0][0] === '/C1/replies' && posts[0][1] === "@ali Narxi 150 000 so'm 🔥 Buyurtma: @Metart_shop_bot"
    && asked.length === 2 && notes.length === 1 && /Narxi qancha/.test(notes[0]);
  console.log(JSON.stringify({ n1, n2, posts, asked, notes: notes.length }));
  console.log(ok ? '✅ Instagram izohlari sinovi o\'tdi' : '❌ Instagram izohlari sinovi XATO');
  process.exit(ok ? 0 : 1);
});
