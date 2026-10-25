// Soxta Telegram API: botni haqiqiy tokensiz to'liq sinash uchun
const http = require('http');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const OUT = path.join(__dirname, 'mock_out'); fs.rmSync(OUT, { recursive: true, force: true }); fs.mkdirSync(OUT);
const DATA = path.join(__dirname, 'data'); fs.rmSync(DATA, { recursive: true, force: true });
const USER = { id: 111, first_name: 'Ali', username: 'ali_test' };
const NEW = { id: 222, first_name: 'Vali' };
const ADMIN = { id: 999, first_name: 'Usta' };
let uid = 0, mid = 100;
const msg = (from, extra) => ({ update_id: ++uid, message: { message_id: ++mid, from, chat: { id: from.id, type: 'private' }, date: 0, ...extra } });
const cb = (from, data) => ({ update_id: ++uid, callback_query: { id: 'q' + uid, from, data, message: { message_id: 50, chat: { id: from.id } } } });
const script = [
  msg(NEW, { text: "🎨 O'z dizaynim" }),
  msg(USER, { text: '/start klub' }), cb(USER, 'lang:uz'),
  cb(USER, 'p:barselona-soat'), cb(USER, 'buy:barselona-soat'), cb(USER, 'col:qora'), cb(USER, 'qty:2'),
  msg(USER, { text: 'Ali' }), msg(USER, { contact: { phone_number: '998901234567' } }), cb(USER, 'dlv:tash'),
  msg(USER, { text: 'Chilonzor 5-kvartal' }), cb(USER, 'ok'),
  msg(ADMIN, { text: '/start' }), cb(ADMIN, 'lang:uz'), msg(ADMIN, { text: '/admin 0000' }), msg(ADMIN, { text: '/admin 12345678' }),
  msg(USER, { text: "🎨 O'z dizaynim" }), msg(USER, { photo: [{ file_id: 'logo1', width: 600, height: 600 }] }),
  cb(USER, 'sz:50'), cb(USER, 'col:oltin'), cb(USER, 'cnext'), cb(USER, 'qty:1'),
  msg(USER, { text: 'Ali Valiyev' }), msg(USER, { text: '90 123 45 67' }), cb(USER, 'dlv:reg'), msg(USER, { text: 'Samarqand, Registon 1' }), cb(USER, 'ok'),
  cb(ADMIN, 'st:M-0002:accepted'), msg(ADMIN, { text: '/statistika' }), msg(ADMIN, { text: '/buyurtmalar' }),
  msg(USER, { photo: [{ file_id: 'hard', width: 600, height: 600 }] }), msg(USER, { text: '90 777 66 55' }),
  msg(USER, { text: '📦 Buyurtmalarim' }), msg(USER, { text: '🌐 Til' }), cb(USER, 'lang:ru'), msg(USER, { text: '🛍 Каталог' }), cb(USER, 'cat:soat'),
];
const log = [];
let pending = null, step = 0, nfile = 0;

const server = http.createServer((req, res) => {
  const chunks = []; req.on('data', c => chunks.push(c)); req.on('end', () => {
    const body = Buffer.concat(chunks);
    if (req.url.startsWith('/file/')) { res.end(fs.readFileSync(path.join(__dirname, req.url.includes('hard') ? 'photo_hard.jpg' : 'logo_white.jpg'))); return; }
    const method = req.url.split('/').pop();
    let params = {};
    const ct = req.headers['content-type'] || '';
    if (ct.includes('json')) params = JSON.parse(body.toString() || '{}');
    else if (ct.includes('multipart')) {
      const b = '--' + ct.split('boundary=')[1];
      for (const part of body.toString('latin1').split(b)) {
        const nm = part.match(/name="([^"]+)"(; filename="([^"]+)")?/); if (!nm) continue;
        const val = part.slice(part.indexOf('\r\n\r\n') + 4, -2);
        if (nm[3]) { const f = path.join(OUT, (++nfile) + '_' + nm[3]); fs.writeFileSync(f, Buffer.from(val, 'latin1')); params[nm[1]] = '[fayl ' + path.basename(f) + ']'; }
        else params[nm[1]] = Buffer.from(val, 'latin1').toString('utf8');
      }
    }
    const reply = r => res.end(JSON.stringify({ ok: true, result: r }));
    if (method === 'getUpdates') {
      if (step >= script.length) { if (!global.fin) { global.fin = 1; setTimeout(finish, 800); } return setTimeout(() => reply([]), 500); }
      const u = script[step++];
      log.push('\n>>> ' + (u.message ? 'MSG ' + u.message.from.id + ': ' + (u.message.text || (u.message.photo ? '[rasm]' : '[kontakt]')) : 'TUGMA ' + u.callback_query.from.id + ': ' + u.callback_query.data));
      return setTimeout(() => reply([u]), 30);
    }
    if (method === 'getMe') return reply({ id: 1, username: 'metartshop_test_bot' });
    if (method === 'getFile') return reply({ file_path: 'photos/' + (params.file_id === 'hard' ? 'hard' : 'x') + '.jpg' });
    if (/^send|^edit/.test(method)) {
      const kb = params.reply_markup ? (typeof params.reply_markup === 'string' ? JSON.parse(params.reply_markup) : params.reply_markup) : null;
      const btns = kb && kb.inline_keyboard ? ' [' + kb.inline_keyboard.flat().map(b => b.text).join(' | ') + ']' : kb && kb.keyboard ? ' {' + kb.keyboard.flat().map(b => b.text || b).join(' | ') + '}' : '';
      log.push(`<<< ${method} → ${params.chat_id}: ${String(params.text || params.caption || params.photo || params.document || '').replace(/\n/g, ' ¶ ').slice(0, 260)}${btns}`);
      return reply({ message_id: ++mid, chat: { id: params.chat_id } });
    }
    reply(true);
  });
});
let bot;
let done = false;
function finish(err) {
  if (done) return; done = true;
  fs.writeFileSync(path.join(__dirname, 'mock_log.txt'), log.join('\n'));
  try { bot.kill(); } catch {}
  server.close(); console.log(log.join('\n'));
  const all = log.join('\n'), fails = [];
  const must = [
    ['1-buyurtma tasdiqlandi', /M-0001/],
    ['noto\'g\'ri admin kodi rad etildi', /→ 999: ⛔/],
    ['adminga M-0002 matni bordi', /sendMessage → 999: 🆕 <b>Yangi buyurtma M-0002/],
    ['adminga DXF bordi', /sendDocument → 999: DXF:/],
    ['mijozga holat xabari bordi', /→ 111: 📦 Buyurtma <b>M-0002<\/b>: ✅/],
    ['ruscha katalog', /Металлические часы/],
    ['murakkab rasm adminga qo\'lda chizish uchun bordi', /sendPhoto → 999: 🖼 <b>Qo'lda dizayn so'rovi/],
    ['mijozdan telefon olindi', /→ 999: 📞 <b>Qo'lda dizayn<\/b>.*\+998907776655/],
    ['mijozga qo\'lda chizish xabari', /→ 111: 🖼 Rasmingiz qabul qilindi/],
    ['til tanlamagan mijoz menyu tugmasidan davom etdi', /→ 222: (?!Tilni)/],
  ];
  for (const [name, re] of must) if (!re.test(all)) fails.push(name);
  if (!fs.readdirSync(OUT).some(f => f.endsWith('.dxf'))) fails.push('DXF fayl yaratilmadi');
  if (err) fails.push(err);
  console.log(fails.length ? '\n❌ XATO: ' + fails.join('; ') : '\n✅ Barcha tekshiruvlar o\'tdi');
  process.exit(fails.length ? 1 : 0);
}
setTimeout(() => finish('vaqt tugadi (90 s)'), 90000);
server.listen(18080, () => {
  bot = spawn('node', [path.join(__dirname, '..', 'src', 'bot.js')], {
    env: { ...process.env, BOT_TOKEN: 'TEST:TOKEN', ADMIN_CODE: '12345678', TG_API: 'http://127.0.0.1:18080', DATA_DIR: DATA }, stdio: 'inherit',
  });
  bot.on('exit', code => { if (!done) setTimeout(() => finish('bot kutilmaganda to\'xtadi (kod ' + code + ')'), 300); });
});
