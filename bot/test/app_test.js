// «Lazer ustaxona» APK ni yuborish: soxta Telegram va GitHub bilan sinov
const http = require('http'); const fs = require('fs'); const path = require('path'); const { spawn } = require('child_process');
const DATA = path.join(__dirname, 'data_app'); fs.rmSync(DATA, { recursive: true, force: true });
const USER = { id: 111, first_name: 'Ali' }, OLD = { id: 222, first_name: 'Vali' }, ADMIN = { id: 999, first_name: 'Usta' };
let uid = 0, mid = 100;
const msg = (from, text) => ({ update_id: ++uid, message: { message_id: ++mid, from, chat: { id: from.id, type: 'private' }, date: 0, text } });
const cb = (from, data) => ({ update_id: ++uid, callback_query: { id: 'q' + uid, from, data, message: { message_id: 50, chat: { id: from.id } } } });
const script = [msg(OLD, '/start'), cb(OLD, 'lang:uz'), msg(ADMIN, '/start'), cb(ADMIN, 'lang:uz'), msg(ADMIN, '/admin 12345678'),
  msg(USER, '/start ilova_yangilash'), cb(USER, 'lang:uz'), msg(ADMIN, '/ilova'), msg(ADMIN, '/ilova hammaga')];
const docs = [], texts = []; let apkGets = 0, step = 0, fid = 0;
const APK = Buffer.from('PK\u0003\u0004 soxta apk');
const srv = http.createServer((req, res) => {
  const ch = []; req.on('data', c => ch.push(c)); req.on('end', () => {
    const body = Buffer.concat(ch), m = req.url.split('/').pop(), ok = r => res.end(JSON.stringify({ ok: true, result: r }));
    if (req.url === '/repos/oybekkjon1994-coder/lazer-app/releases/latest') return res.end(JSON.stringify({ tag_name: 'v1.0.57', body: 'Perila naqsh', assets: [{ name: 'lazer.apk', browser_download_url: 'http://127.0.0.1:18083/dl/lazer.apk' }] }));
    if (req.url === '/dl/lazer.apk') { apkGets++; return res.end(APK); }
    if (m === 'getMe') return ok({ id: 1, username: 'test_bot' });
    if (m === 'getUpdates') { const u = script[step]; if (u) { step++; return ok([u]); } return setTimeout(() => ok([]), 300); }
    if (m === 'sendDocument') {
      const s = body.toString('latin1'), chat = (s.match(/name="chat_id"\r\n\r\n(\d+)/) || [])[1] || (/^\{/.test(s) ? String(JSON.parse(s).chat_id) : '?');
      const inline = /filename="lazer.apk"/.test(s), byId = /^\{/.test(s) ? JSON.parse(s).document : null;
      docs.push({ chat, inline, byId }); return ok({ message_id: 1, document: { file_id: 'F' + (++fid) } });
    }
    if (m === 'sendMessage') { try { const j = JSON.parse(body); texts.push([j.chat_id, j.text]); } catch (_) {} return ok({ message_id: ++mid }); }
    return ok(true);
  });
});
srv.listen(18083, () => {
  const bot = spawn('node', [path.join(__dirname, '..', 'src', 'bot.js')], { env: { ...process.env, BOT_TOKEN: 'TEST:TOKEN', ADMIN_CODE: '12345678', TG_API: 'http://127.0.0.1:18083', GH_API: 'http://127.0.0.1:18083', DATA_DIR: DATA, GROQ_API_KEY: '' }, stdio: ['ignore', 'pipe', 'pipe'] });
  let err = ''; bot.stderr.on('data', d => err += d);
  const t0 = Date.now(), iv = setInterval(() => {
    const done = step >= script.length && texts.some(([c, t]) => c === 999 && /Yuborildi: \d+\/2/.test(t));
    if (!done && Date.now() - t0 < 20000) return;
    clearInterval(iv); bot.kill(); srv.close();
    const toUser = docs.filter(d => d.chat === '111'), toOld = docs.filter(d => d.chat === '222');
    const checks = {
      'tugma bosgan mijozga APK keldi': toUser.length >= 1 && toUser[0].inline,
      'APK GitHub dan bir marta yuklandi (keyin file_id)': apkGets === 1 && docs.slice(1).every(d => d.byId),
      '/ilova faqat ilova egasiga': texts.some(([c, t]) => c === 999 && /Yuborildi: 1\/1/.test(t)),
      '/ilova hammaga eski mijozga ham': toOld.length === 1 && texts.some(([c, t]) => c === 999 && /Yuborildi: 2\/2/.test(t)),
    };
    const fails = Object.entries(checks).filter(([, v]) => !v).map(([k]) => k);
    console.log(JSON.stringify({ docs, apkGets, adminTexts: texts.filter(([c]) => c === 999).map(([, t]) => t.slice(0, 60)) }));
    if (err.trim()) console.log('stderr:', err.slice(0, 800));
    fs.rmSync(DATA, { recursive: true, force: true });
    console.log(fails.length ? '❌ Ilova yuborish sinovi XATO: ' + fails.join('; ') : '✅ Ilova yuborish sinovi o\'tdi');
    process.exit(fails.length ? 1 : 0);
  }, 300);
});
