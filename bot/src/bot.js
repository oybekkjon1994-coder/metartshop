// METARTSHOP Telegram bot — katalog, "o'z dizaynim" (logotip → soat), buyurtmalar, admin panel
'use strict';
const fs = require('fs');
const path = require('path');
const TG = require('./tg');
const Store = require('./store');
const design = require('./design');
const dxfcalc = require('./dxfcalc');
const { T, COLOR_NAMES } = require('./i18n');

const ROOT = path.join(__dirname, '..');
loadEnv(path.join(ROOT, '.env'));
const CFG = JSON.parse(fs.readFileSync(path.join(ROOT, 'config.json'), 'utf8'));
const TOKEN = (process.env.BOT_TOKEN || '').trim();
const ADMIN_CODE = (process.env.ADMIN_CODE || '').trim();
if (!TOKEN || TOKEN.includes('SHU_YERGA')) {
  console.error('\n❗ BOT_TOKEN yozilmagan. bot\\.env faylini oching va BotFather bergan tokenni yozing.\n');
  process.exit(2);
}
const tg = new TG(TOKEN, process.env.TG_API || 'https://api.telegram.org');
const db = new Store(process.env.DATA_DIR || path.join(ROOT, 'data'));
const REF = Object.assign({ enabled: true, percent: 10 }, CFG.referral || {});
const LASER = Object.assign({ enabled: true, rates: [], sheet_mm: [1250, 2500] }, CFG.laser || {});
const HOL = Object.assign({ enabled: true, days_before: 7, list: [] }, CFG.holidays || {});
const PAY = Object.assign({ prepay_percent: 50 }, CFG.payment || {});
let BOT_NAME = '';
const designs = new Map(); // userId -> { shape, original } (oxirgi 30 tasi xotirada)
function keepDesign(id, d) { designs.delete(id); designs.set(id, d); while (designs.size > 30) designs.delete(designs.keys().next().value); }

function loadEnv(p) {
  try {
    for (const line of fs.readFileSync(p, 'utf8').split(/\r?\n/)) {
      const m = line.match(/^\s*([A-Z_]+)\s*=\s*(.*)\s*$/);
      if (m && !process.env[m[1]]) process.env[m[1]] = m[2].replace(/^["']|["']$/g, '');
    }
  } catch { /* .env yo'q */ }
}

// ---------- katalog ----------
let catalog = null, catalogAt = 0;
async function getCatalog() {
  if (catalog && Date.now() - catalogAt < 5 * 60 * 1000) return catalog;
  const cacheFile = path.join(db.dir, 'catalog_cache.json');
  try {
    const res = await fetch(CFG.catalog_url + '?t=' + Date.now(), { signal: AbortSignal.timeout(10000) });
    if (!res.ok) throw new Error(res.status);
    catalog = await res.json(); catalogAt = Date.now();
    fs.writeFileSync(cacheFile, JSON.stringify(catalog));
  } catch (e) {
    if (!catalog) {
      for (const f of [cacheFile, path.join(ROOT, '..', 'data.json')]) {
        try { catalog = JSON.parse(fs.readFileSync(f, 'utf8')); break; } catch { /* keyingisi */ }
      }
    }
    if (!catalog) catalog = { shop: {}, cats: [], products: [] };
    catalogAt = Date.now() - 4 * 60 * 1000; // 1 daqiqadan keyin qayta urinadi
    console.error('Katalogni yuklab bo\'lmadi, zaxira ishlatilmoqda:', e.message);
  }
  return catalog;
}
const imgUrl = p => /^https?:/.test(p) ? p : CFG.site_url + p.replace(/^\//, '');
const money = (n, l) => String(Math.round(Number(n))).replace(/\B(?=(\d{3})+(?!\d))/g, ' ') + (l === 'ru' ? ' сум' : " so'm");
const esc = s => String(s ?? '').replace(/[<>&]/g, c => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;' }[c]));
const pname = (p, l) => (l === 'ru' && p.name_ru) || p.name_uz || p.id;
const cname = (c, l) => (l === 'ru' && c.ru) || c.uz || c.id;

// ---------- klaviaturalar ----------
const t = u => T[u.lang || 'uz'];
const mainKb = u => ({
  keyboard: [[t(u).m_catalog, t(u).m_custom], [t(u).m_clubs, t(u).m_orders], ...(REF.enabled || LASER.enabled ? [[...(LASER.enabled ? [t(u).m_laser] : []), ...(REF.enabled ? [t(u).m_invite] : [])]] : []), [t(u).m_contact, t(u).m_lang]],
  resize_keyboard: true, is_persistent: true,
});
const ik = rows => ({ inline_keyboard: rows });
const chunk = (arr, n) => arr.reduce((a, x, i) => (i % n ? a[a.length - 1].push(x) : a.push([x]), a), []);

async function send(chat, text, extra = {}) {
  return tg.call('sendMessage', { chat_id: chat, text, parse_mode: 'HTML', disable_web_page_preview: true, ...extra });
}
const isAdmin = id => db.state.admins.includes(id);
async function toAdmins(fn) {
  for (const a of db.state.admins) { try { await fn(a); } catch (e) { console.error('Adminga yuborilmadi:', e.message); } }
}

// ---------- asosiy ishlov ----------
async function onUpdate(up) {
  const from = (up.message && up.message.from) || (up.callback_query && up.callback_query.from);
  try { await handleUpdate(up); } finally {
    if (from && db.users[String(from.id)]) {
      const u = db.users[String(from.id)]; u.lastSeen = Date.now(); u.blocked = false;
      if (u.s && u.s.flow) { if (u.s._step !== u.s.step) { u.s._step = u.s.step; u.sAt = Date.now(); } } else u.sAt = 0;
      db.save();
    }
  }
}
async function handleUpdate(up) {
  if (up.callback_query) return onCallback(up.callback_query);
  const m = up.message; if (!m || !m.from || m.chat.type !== 'private') return;
  const u = db.user(m.from); db.save();
  const chat = m.chat.id, text = (m.text || '').trim();
  if (m.photo && /^\/xabar/.test(m.caption || '') && isAdmin(u.id)) { adminBroadcastPhoto(chat, m).catch(e => console.error('Xabar xatosi:', e.message)); return; }
  // Admin qo'lda dizayn so'roviga javob (reply) qildi: dizaynni mijozga yetkazamiz
  if (isAdmin(u.id) && m.reply_to_message && (db.state.mreq || {})[`${chat}:${m.reply_to_message.message_id}`]) return adminManualReply(u, chat, m);

  if (text.startsWith('/')) {
    const [cmd, ...rest] = text.split(/\s+/); const arg = rest.join(' ');
    if (cmd === '/start') return start(u, chat, arg);
    if (cmd === '/admin') return adminLogin(u, chat, arg);
    if (isAdmin(u.id)) {
      if (cmd === '/buyurtmalar') return adminOrders(chat);
      if (cmd === '/statistika') return adminStats(chat);
      if (cmd === '/xabar') { adminBroadcast(chat, text.slice(cmd.length).trim(), m).catch(e => console.error('Xabar xatosi:', e.message)); return; }
      if (cmd === '/yordam') return adminHelp(chat);
      if (cmd === '/karta') return adminCard(chat, arg);
    }
  }
  // menyu tugmalari (ikkala tilda)
  const is = k => text === T.uz[k] || text === T.ru[k];
  if (!u.lang) {
    // Til tanlanmagan, lekin menyu tugmasi bosilgan: tilni tugma matnidan aniqlaymiz (qayta so'ramaymiz)
    const MK = ['m_catalog', 'm_custom', 'm_clubs', 'm_orders', 'm_contact'];
    if (MK.some(k => text === T.uz[k])) u.lang = 'uz';
    else if (MK.some(k => text === T.ru[k])) u.lang = 'ru';
    else return askLang(chat);
    db.save();
  }
  if (is('m_catalog')) { u.s = {}; return showCats(u, chat); }
  if (is('m_custom')) { u.s = { flow: 'custom', step: 'await_image' }; return send(chat, t(u).custom_intro, { reply_markup: mainKb(u) }); }
  if (is('m_clubs')) { u.s = {}; return showClubs(u, chat); }
  if (is('m_orders')) return myOrders(u, chat);
  if (is('m_contact')) { const c = await getCatalog(); return send(chat, u.lang === 'ru' ? T.ru.contact(c.shop || {}) : T.uz.contact(c.shop || {})); }
  if (is('m_lang')) return askLang(chat);
  if (REF.enabled && is('m_invite')) return showInvite(u, chat);
  if (LASER.enabled && is('m_laser')) { u.s = { flow: 'laser', step: 'laser_file' }; return send(chat, laserIntro(u), { reply_markup: mainKb(u) }); }

  const s = u.s || (u.s = {});
  // rasm qabul qilish (o'z dizaynim)
  const photo = m.photo ? m.photo[m.photo.length - 1] : (m.document && /^image\//.test(m.document.mime_type || '') ? m.document : null);
  if (photo && s.roomWait && s.flow === 'custom') return handleRoom(u, chat, photo.file_id);
  if (photo && s.step === 'review') return reviewPhoto(u, chat, photo.file_id);
  // DXF chizma — istalgan paytda lazer kesish hisobiga
  if (LASER.enabled && m.document && /\.dxf$/i.test(m.document.file_name || '') && s.step !== 'receipt') return handleDxf(u, chat, m.document);
  if (s.step === 'receipt' && (photo || m.document)) return gotReceipt(u, chat, photo ? photo.file_id : m.document.file_id, s.oid, !photo || !!m.document);
  if (photo) {
    if (s.flow !== 'custom') u.s = { flow: 'custom', step: 'await_image' };
    return handleImage(u, chat, photo.file_id);
  }
  if (m.contact && s.step === 'manual_phone') return m.contact.user_id && m.contact.user_id !== m.from.id ? manualAsk(u, chat) : manualPhone(u, chat, m.contact.phone_number);
  if (m.contact && s.step === 'phone') return m.contact.user_id && m.contact.user_id !== m.from.id ? askPhone(u, chat) : gotPhone(u, chat, m.contact.phone_number);

  switch (s.step) {
    case 'qty_text': {
      const n = parseInt(text, 10);
      if (!(n > 0 && n < 1000)) return send(chat, t(u).ask_qty_text);
      s.qty = n; return askName(u, chat);
    }
    case 'name': if (text.length < 2) return askName(u, chat); s.name = text.slice(0, 60); return askPhone(u, chat);
    case 'phone': return gotPhone(u, chat, text);
    case 'address': if (text.length < 3) return send(chat, t(u).ask_address); s.address = text.slice(0, 200); return showSummary(u, chat);
    case 'await_image': return send(chat, t(u).custom_intro);
    case 'laser_file': return send(chat, laserIntro(u));
    case 'manual_phone': return manualPhone(u, chat, text);
    case 'manual_change': return manualChange(u, chat, text);
    case 'review': return reviewText(u, chat, text);
    case 'receipt': { const o = db.orders.find(x => x.id === s.oid); if (o) return askPayment(u, chat, o); u.s = {}; break; }
  }
  if (AI_KEY && text.length >= 2 && !text.startsWith('/')) return aiReply(u, chat, text);
  return send(chat, t(u).use_menu, { reply_markup: mainKb(u) });
}

// ---------- AI-maslahatchi (Groq, bepul) ----------
const AI_KEY = (process.env.GROQ_API_KEY || '').trim();
const AI_BASE = (process.env.GROQ_API || 'https://api.groq.com/openai/v1').replace(/\/$/, '');
const AI_MODELS = (process.env.GROQ_MODEL || 'openai/gpt-oss-120b,qwen/qwen3.8-27b').split(',').map(x => x.trim()).filter(Boolean);
async function aiSystem(u) {
  const c = await getCatalog(); const sh = c.shop || {};
  const prods = c.products.filter(p => p.stock !== false).map(p => `${p.id} | ${pname(p, u.lang)} | ${p.price > 0 ? money(p.price, u.lang) : (u.lang === 'ru' ? 'цена договорная' : 'narx kelishiladi')}${p.size ? ' | ' + p.size : ''}`).join('\n');
  const sizes = CFG.custom_sizes.map(z => `${z.cm} sm — ${money(z.price, 'uz')}`).join(', ');
  const laser = LASER.enabled ? LASER.rates.map(r => `${r.label}: ${money(r.rate, 'uz')}/m`).join(', ') : "yo'q";
  return `Sen METARTSHOP do'konining Telegram botidagi sotuvchi-maslahatchisan. Do'kon: metalldan lazer bilan kesilgan devor soatlari, dekor, panno, mangal, stellaj va buyurtma asosida lazer kesish (Toshkent).
Javob tili: ${u.lang === 'ru' ? 'rus tili' : "o'zbek tili (lotin)"}. Qisqa yoz: 1-5 gap, do'stona, ortiqcha gapsiz. Markdown ishlatma.
FAQAT quyidagi ma'lumotlarga tayan. Narx, mahsulot, muddat yoki chegirma o'ylab topma. Faqat javob ro'yxatda YO'Q bo'lsagina "Ustamiz aniq aytadi: @${sh.telegram || 'lazekametal'}" de — oddiy tavsiya va javoblarda aloqa havolasini qo'shma.
Tavsiya qilgan mahsulot nomidan keyin darhol [[p:ID]] yoz (masalan: "Barselona devor soati [[p:barselona-soat]]"); javob oxirida tugmalar chiqadi.
Mahsulot tavsiya qilsang (ko'pi bilan 3 ta), har biri uchun matn oxirida [[p:ID]] yoz (ID — ro'yxatdagi birinchi ustun). Logotip/ism/rasm bilan maxsus soat kerak bo'lsa [[dizayn]], DXF bo'yicha lazer kesish kerak bo'lsa [[lazer]] yoz.
MAHSULOTLAR (ID | nomi | narxi | o'lcham):
${prods}
O'Z DIZAYNI (logotip/ism/rasmdan soat): ${sizes}; ranglar: ${CFG.custom_colors.join(', ')}; tayyor bo'lish: ${CFG.ready_days || '2-3'} kun.
LAZER KESISH (1 metr kesish narxi, metall alohida): ${laser}; list ${LASER.sheet_mm.join('×')} mm.
YETKAZISH: Toshkent bo'ylab Yandex, viloyatlarga BTS pochta, yoki o'zi olib ketadi. To'lov: buyurtmadan keyin kartaga ${PAY.prepay_percent}% oldindan.
${REF.enabled ? `DO'ST TAKLIFI: «🎁 Chegirma olish» tugmasi — do'st va taklif qiluvchiga ${REF.percent}% chegirma.` : ''}
ALOQA: Telegram @${sh.telegram || 'lazekametal'}, tel +${sh.phone || '998770179990'}, Instagram @${sh.instagram || 'metart_shop'}.`;
}
async function aiCall(messages) {
  let lastErr;
  for (const model of AI_MODELS) {
    try {
      const body = { model, messages, temperature: 0.4, max_tokens: 700 };
      if (/gpt-oss/.test(model)) body.reasoning_effort = 'low';
      const res = await fetch(AI_BASE + '/chat/completions', { method: 'POST', headers: { 'content-type': 'application/json', authorization: 'Bearer ' + AI_KEY }, body: JSON.stringify(body), signal: AbortSignal.timeout(25000) });
      const j = await res.json().catch(() => ({}));
      const txt = j.choices && j.choices[0] && j.choices[0].message && j.choices[0].message.content;
      if (res.ok && txt) return txt.trim();
      lastErr = new Error(`${model}: ${res.status} ${(j.error && j.error.message) || ''}`);
    } catch (e) { lastErr = e; }
  }
  throw lastErr || new Error('AI');
}
async function aiReply(u, chat, text) {
  const day = new Date(Date.now() + 5 * H).toISOString().slice(0, 10);
  if (u.aiDay !== day) { u.aiDay = day; u.aiN = 0; }
  if (db.state.aiDay !== day) { db.state.aiDay = day; db.state.aiN = 0; }
  if (u.aiN >= 40 || db.state.aiN >= 1500) return send(chat, t(u).ai_limit, { reply_markup: mainKb(u) });
  u.aiN++; db.state.aiN++;
  tg.call('sendChatAction', { chat_id: chat, action: 'typing' }).catch(() => {});
  const hist = (u.ai || []).slice(-6);
  try {
    const out = await aiCall([{ role: 'system', content: await aiSystem(u) }, ...hist, { role: 'user', content: text.slice(0, 1000) }]);
    u.ai = [...hist, { role: 'user', content: text.slice(0, 500) }, { role: 'assistant', content: out.slice(0, 800) }].slice(-6);
    const c = await getCatalog(); const rows = [];
    for (const m of out.matchAll(/\[\[p:([\w-]+)\]\]/g)) {
      const p = c.products.find(x => x.id === m[1]);
      if (p && !rows.some(r => r[0].callback_data === 'p:' + p.id) && rows.length < 3) rows.push([{ text: '🛍 ' + pname(p, u.lang), callback_data: 'p:' + p.id }]);
    }
    if (/\[\[dizayn\]\]/.test(out)) rows.push([{ text: t(u).ai_custom, callback_data: 'custom' }]);
    if (/\[\[lazer\]\]/.test(out) && LASER.enabled) rows.push([{ text: t(u).ai_laser, callback_data: 'laser' }]);
    const clean = out.replace(/\[\[[^\]]*\]\]/g, '').replace(/\*\*/g, '').replace(/[ \t]+([,.;:!?)])/g, '$1').replace(/[ \t]{2,}/g, ' ').replace(/[ \t]+\n/g, '\n').trim();
    // Mahsulot tavsiya qilingan bo'lsa, "ustamiz aytadi @..." keraksiz — olib tashlaymiz
    const final = rows.length ? clean.replace(/\s*(Ustamiz aniq aytadi|Мастер (?:точно )?(?:скажет|подскажет))[^\n]*@\w+\.?/gi, '').trim() : clean;
    return send(chat, esc(final || clean || t(u).ai_fail), rows.length ? { reply_markup: ik(rows) } : {});
  } catch (e) {
    console.error('AI xatosi:', e.message);
    return send(chat, t(u).ai_fail, { reply_markup: mainKb(u) });
  }
}

async function askLang(chat) {
  return send(chat, T.uz.choose_lang, { reply_markup: ik([[{ text: "🇺🇿 O'zbekcha", callback_data: 'lang:uz' }, { text: '🇷🇺 Русский', callback_data: 'lang:ru' }]]) });
}

async function start(u, chat, payload) {
  u.s = {};
  if (payload && /^r\d+$/.test(payload)) {
    // Do'st havolasi: faqat yangi (hali buyurtma bermagan) foydalanuvchiga, o'zini o'zi taklif qila olmaydi
    const rid = +payload.slice(1);
    if (REF.enabled && !u.refBy && rid !== u.id && db.users[String(rid)] && !db.orders.some(o => o.userId === u.id)) { u.refBy = rid; u.refPending = true; }
    u.ref = u.ref || 'dost';
    payload = '';
  } else if (payload) u.ref = u.ref || payload;
  if (!u.lang) { u.pending = payload || ''; return askLang(chat); }
  await send(chat, t(u).welcome(esc(u.name || '')), { reply_markup: mainKb(u) });
  if (u.refPending) { delete u.refPending; await send(chat, t(u).ref_welcome(REF.percent)); }
  return deepLink(u, chat, payload);
}

async function deepLink(u, chat, payload) {
  if (!payload) return;
  if (payload.startsWith('p_')) return showProduct(u, chat, payload.slice(2));
  if (payload === 'dizayn') { u.s = { flow: 'custom', step: 'await_image' }; return send(chat, t(u).custom_intro); }
  if (payload === 'klub') return showClubs(u, chat);
  if (payload === 'katalog') return showCats(u, chat);
}

async function showCats(u, chat, editMsg) {
  const c = await getCatalog();
  const cats = c.cats.filter(ct => c.products.some(p => p.cat === ct.id && p.stock !== false));
  const kb = ik(chunk(cats.map(ct => ({ text: cname(ct, u.lang), callback_data: 'cat:' + ct.id })), 2));
  if (editMsg) return tg.call('editMessageText', { chat_id: chat, message_id: editMsg, text: t(u).cats, reply_markup: kb }).catch(() => send(chat, t(u).cats, { reply_markup: kb }));
  return send(chat, t(u).cats, { reply_markup: kb });
}

async function showCat(u, chat, catId, editMsg) {
  const c = await getCatalog();
  const cat = c.cats.find(x => x.id === catId);
  const list = c.products.filter(p => p.cat === catId && p.stock !== false);
  if (!list.length) return send(chat, t(u).empty);
  const rows = list.map(p => [{ text: pname(p, u.lang) + (p.price > 0 ? ' — ' + money(p.price, u.lang) : ''), callback_data: 'p:' + p.id }]);
  rows.push([{ text: t(u).back, callback_data: 'cats' }]);
  const text = t(u).products(esc(cat ? cname(cat, u.lang) : ''));
  if (editMsg) return tg.call('editMessageText', { chat_id: chat, message_id: editMsg, text, parse_mode: 'HTML', reply_markup: ik(rows) }).catch(() => send(chat, text, { reply_markup: ik(rows) }));
  return send(chat, text, { reply_markup: ik(rows) });
}

async function showClubs(u, chat) {
  const c = await getCatalog();
  const re = /(klub|fc|club|madrid|barsel|barcel|chelsea|city|united|liverpool|arsenal|nasaf|pakhtakor|paxtakor|bunyodkor|juventus|bayern|psg|milan|inter|ronaldo|messi|bo'?rilar|клуб)/i;
  const list = c.products.filter(p => p.cat === 'soat' && p.stock !== false && re.test(p.id + ' ' + p.name_uz + ' ' + (p.name_ru || '')));
  const rows = chunk(list.map(p => ({ text: pname(p, u.lang).replace(/ devor soati| soati|Настенные часы |Часы /gi, '').replace(/[«»]/g, ''), callback_data: 'p:' + p.id })), 2);
  rows.push([{ text: t(u).no_club, callback_data: 'custom' }]);
  return send(chat, t(u).clubs, { reply_markup: ik(rows) });
}

async function showProduct(u, chat, pid, imgIdx = 0) {
  const c = await getCatalog();
  const p = c.products.find(x => x.id === pid);
  if (!p) return showCats(u, chat);
  if (!u.viewed || u.viewed.pid !== pid) u.viewed = { pid, at: Date.now(), offered: false };
  const desc = (u.lang === 'ru' && p.desc_ru) || p.desc_uz || '';
  const cap = `<b>${esc(pname(p, u.lang))}</b>\n\n${esc(desc)}${p.size ? '\n📏 ' + esc(p.size) : ''}\n\n${t(u).price(p.price > 0 ? money(p.price, u.lang) : '')}`;
  const rows = [[{ text: t(u).buy, callback_data: 'buy:' + p.id }]];
  if ((p.imgs || []).length > 1) rows.push([{ text: t(u).more_photo, callback_data: `img:${p.id}:${(imgIdx + 1) % p.imgs.length}` }]);
  rows.push([{ text: t(u).back, callback_data: 'cat:' + p.cat }]);
  const img = (p.imgs || [])[imgIdx];
  if (img) {
    try { return await tg.call('sendPhoto', { chat_id: chat, photo: imgUrl(img), caption: cap, parse_mode: 'HTML', reply_markup: ik(rows) }); }
    catch (e) { console.error('Rasm yuborilmadi:', e.message); }
  }
  return send(chat, cap, { reply_markup: ik(rows) });
}

// ---------- buyurtma bosqichlari ----------
async function startBuy(u, chat, pid) {
  const c = await getCatalog();
  const p = c.products.find(x => x.id === pid); if (!p) return;
  u.s = { flow: 'product', pid, price: p.price || 0, title: p.name_uz || pname(p, 'uz'), titleL: pname(p, u.lang), img: (p.imgs || [])[0] };
  const colors = (p.colors || []).filter(Boolean);
  if (colors.length) {
    u.s.step = 'color';
    return send(chat, t(u).ask_color, { reply_markup: ik(chunk(colors.map(cl => ({ text: (COLOR_NAMES[u.lang][cl] || cl), callback_data: 'col:' + cl })), 3)) });
  }
  return askQty(u, chat);
}
function askQty(u, chat) {
  u.s.step = 'qty';
  return send(chat, t(u).ask_qty, { reply_markup: ik([[1, 2, 3, 5].map(n => ({ text: String(n), callback_data: 'qty:' + n })), [{ text: t(u).qty_other, callback_data: 'qty:x' }]]) });
}
function askName(u, chat) {
  u.s.step = 'name';
  const known = u.lastName ? { reply_markup: { keyboard: [[u.lastName]], resize_keyboard: true, one_time_keyboard: true } } : { reply_markup: { remove_keyboard: true } };
  return send(chat, t(u).ask_name, known);
}
function askPhone(u, chat) {
  u.s.step = 'phone';
  const kb = [[{ text: t(u).share_phone, request_contact: true }]]; if (u.lastPhone) kb.push([u.lastPhone]);
  return send(chat, t(u).ask_phone, { reply_markup: { keyboard: kb, resize_keyboard: true, one_time_keyboard: true } });
}
function gotPhone(u, chat, raw) {
  let digits = String(raw).replace(/\D/g, '');
  if (digits.length === 10 && digits[0] === '0') digits = digits.slice(1);
  if (digits.length < 9 || digits.length > 13) return send(chat, t(u).bad_phone);
  const ph = digits.length === 9 ? '+998' + digits : '+' + digits;
  u.s.phone = ph; u.lastPhone = ph; u.s.step = 'delivery';
  return send(chat, t(u).ask_delivery, { reply_markup: ik([[{ text: t(u).d_tash, callback_data: 'dlv:tash' }], [{ text: t(u).d_reg, callback_data: 'dlv:reg' }], [{ text: t(u).d_self, callback_data: 'dlv:self' }]]) });
}
function dlvName(l, d) { return { tash: T[l].d_tash, reg: T[l].d_reg, self: T[l].d_self }[d] || d; }

const orderTotal = o => Math.round((o.price || 0) * (o.qty || 1) * (100 - (o.discount || 0)) / 100);
// Chegirma: do'st havolasi bilan kelgan birinchi buyurtma yoki taklif qilgani uchun bonus
function discountFor(u) {
  if (!REF.enabled) return 0;
  if (u.refBy && !db.orders.some(o => o.userId === u.id && o.status !== 'canceled')) return REF.percent;
  if ((u.refBonus || 0) > 0) return REF.percent;
  return 0;
}
function orderLines(l, o) {
  const L = T[l]; const lines = [];
  lines.push(`🛍 ${L.f_product}: <b>${esc(l === 'uz' ? o.title : (o.titleL || o.title))}</b>`);
  if (o.size) lines.push(`📏 ${L.f_size}: ${o.size} sm`);
  if (o.meters) lines.push(`📐 ${o.dimsL || ''} · ${o.meters} m · ${esc(o.tier || '')}`);
  if (o.color) lines.push(`🎨 ${L.f_color}: ${COLOR_NAMES[l][o.color] || o.color}`);
  lines.push(`🔢 ${L.f_qty}: ${o.qty}`);
  if (o.discount && o.price > 0) lines.push(`🎁 ${L.f_discount}: ${o.discount}% (−${money(o.price * o.qty - orderTotal(o), l)})`);
  else if (o.discount) lines.push(`🎁 ${L.f_discount}: ${o.discount}%`);
  lines.push(`💰 ${L.f_total}: <b>${o.price > 0 ? money(orderTotal(o), l) : L.total_ask}</b>`);
  lines.push(`👤 ${L.f_name}: ${esc(o.name)}`);
  lines.push(`📱 ${L.f_phone}: ${esc(o.phone)}`);
  lines.push(`🚚 ${L.f_delivery}: ${dlvName(l, o.delivery)}`);
  if (o.address) lines.push(`📍 ${L.f_address}: ${esc(o.address)}`);
  return lines.join('\n');
}

async function showSummary(u, chat) {
  u.s.step = 'confirm'; u.s.discount = discountFor(u);
  return send(chat, `${t(u).summary}\n\n${orderLines(u.lang, u.s)}`, {
    reply_markup: ik([[{ text: t(u).confirm, callback_data: 'ok' }, { text: t(u).cancel, callback_data: 'no' }]]),
  });
}

async function placeOrder(u, chat) {
  const s = u.s; const id = db.nextOrderId();
  const o = {
    id, at: new Date().toISOString(), userId: u.id, username: u.username, tgName: u.name, lang: u.lang, status: 'new',
    flow: s.flow, pid: s.pid, title: s.title, titleL: s.titleL || s.title, color: s.color, size: s.size, qty: s.qty || 1, price: s.price || 0,
    name: s.name, phone: s.phone, delivery: s.delivery, address: s.address || '', ref: u.ref || '',
  };
  if (s.flow === 'laser') Object.assign(o, { meters: s.meters, dimsL: `${s.w}×${s.h} mm`, tier: s.tier, dxfFile: s.fileId, dxfName: s.fname });
  o.discount = discountFor(u);
  if (o.discount) {
    o.discountType = u.refBy && !db.orders.some(x => x.userId === u.id && x.status !== 'canceled') ? 'friend' : 'bonus';
    if (o.discountType === 'bonus') u.refBonus = Math.max(0, (u.refBonus || 0) - 1);
    if (o.discountType === 'friend') o.refBy = u.refBy;
  }
  u.lastName = s.name; u.ordered = Date.now(); u.orderedPids = [...new Set([...(u.orderedPids || []), s.pid].filter(Boolean))]; u.viewed = null; u.sAt = 0;
  // o'z dizayni: DXF va rasmlarni saqlash
  let files = [];
  if (s.flow === 'custom') {
    const d = designs.get(u.id) || await reloadDesign(u);
    if (d) {
      const dx = await design.makeDxf(d.shape, s.size * 10);
      o.dxf = db.saveFile(`${id}.dxf`, dx.dxf);
      o.cutM = +design.cutLength(dx.dxf).toFixed(2); o.dims = `${dx.widthMm}×${dx.heightMm} mm`; if (dx.thin) o.thin = dx.thin;
      const prev = await design.makePreview(d.shape, s.color, `${s.size} sm · ${COLOR_NAMES.uz[s.color] || s.color}`);
      o.preview = db.saveFile(`${id}-korinish.jpg`, prev);
      o.original = db.saveFile(`${id}-asl${d.ext || '.jpg'}`, d.original);
      files = [
        ['sendPhoto', { photo: TG.file(prev, `${id}.jpg`, 'image/jpeg') }],
        ['sendDocument', { document: TG.file(Buffer.from(dx.dxf), `${id}-${s.size}sm.dxf`, 'application/dxf'), caption: `DXF: ${o.dims}, kesish ≈ ${o.cutM} m` }],
        ['sendDocument', { document: TG.file(d.original, `${id}-asl${d.ext || '.jpg'}`) }],
      ];
    }
  }
  if (s.flow === 'laser' && s.fileId) files = [['sendDocument', { document: s.fileId, caption: `${id} — ${s.fname}` }]];
  if (s.flow === 'manual' && s.designPhoto) { o.designPhoto = s.designPhoto; files = [['sendPhoto', { photo: s.designPhoto, caption: `${id} — dizayn` }]]; }
  o.img = s.img || ''; o.tgName = u.name; o.notified = false;
  db.orders.push(o); u.s = {}; db.saveNow();
  await send(chat, t(u).done(id), { reply_markup: mainKb(u) });
  await notifyAdmins(o, files);
  await askPayment(u, chat, o);
}

// Adminga buyurtma xabari: avval matn (eng muhimi), keyin fayllar alohida-alohida.
// Yetib bormasa, o.notified=false qoladi va har 10 daqiqada qayta uriniladi.
async function notifyAdmins(o, files) {
  if (!db.state.admins.length) { console.log(`Yangi buyurtma ${o.id} (admin ulanmagan — /admin KOD yuboring)`); return; }
  const who = `${esc(o.tgName || '')}${o.username ? ' (@' + esc(o.username) + ')' : ''} · <a href="tg://user?id=${o.userId}">profil</a>`;
  const text = `🆕 <b>Yangi buyurtma ${o.id}</b>\n\n${orderLines('uz', o)}${o.dims ? `\n📐 Chizma: ${o.dims}, kesish ≈ ${o.cutM} m${o.thin ? `\n⚠️ Ingichka joylar qalinlashtirildi (${o.thin}) — chizmani tekshiring` : ''}` : ''}\n\n👤 ${who}${o.ref ? `\n🔗 Manba: ${esc(o.ref)}` : ''}${o.discountType === 'friend' ? `\n🎁 Do'st taklifi (taklif qilgan: <a href="tg://user?id=${o.refBy}">${o.refBy}</a>)` : ''}`;
  if (!files) files = filesFromDisk(o);
  let delivered = 0;
  for (const a of db.state.admins) {
    try { await send(a, text, { reply_markup: statusKb(o) }); delivered++; } catch (e) { console.error(`Adminga ${o.id} yuborilmadi:`, e.message); continue; }
    if (o.flow === 'product' && o.img) await tg.call('sendPhoto', { chat_id: a, photo: imgUrl(o.img), caption: o.id }).catch(e => console.error('Rasm:', e.message));
    for (const [m, p] of files) await tg.call(m, { chat_id: a, ...p }).catch(e => console.error(`${o.id} fayli yuborilmadi:`, e.message));
  }
  if (delivered) { o.notified = true; db.saveNow(); }
}
function filesFromDisk(o) {
  const f = [], rd = p => { try { return fs.readFileSync(p); } catch { return null; } };
  const prev = o.preview && rd(o.preview), dxf = o.dxf && rd(o.dxf), orig = o.original && rd(o.original);
  if (prev) f.push(['sendPhoto', { photo: TG.file(prev, `${o.id}.jpg`, 'image/jpeg') }]);
  if (dxf) f.push(['sendDocument', { document: TG.file(dxf, `${o.id}-${o.size}sm.dxf`, 'application/dxf'), caption: `DXF: ${o.dims}, kesish ≈ ${o.cutM} m` }]);
  if (orig) f.push(['sendDocument', { document: TG.file(orig, path.basename(o.original)) }]);
  if (o.designPhoto) f.push(['sendPhoto', { photo: o.designPhoto, caption: `${o.id} — dizayn` }]);
  if (o.dxfFile) f.push(['sendDocument', { document: o.dxfFile, caption: `${o.id} — ${o.dxfName || 'DXF'}` }]);
  return f;
}
async function retryNotifications() {
  for (const o of db.orders) if (o.notified === false && db.state.admins.length) await notifyAdmins(o);
}

function statusKb(o) {
  const b = (st, label) => ({ text: (o.status === st ? '• ' : '') + label, callback_data: `st:${o.id}:${st}` });
  return ik([[b('accepted', '✅ Qabul'), b('making', '🔧 Tayyorlanmoqda')], [b('sent', "🚚 Jo'natildi"), b('done', '🎉 Topshirildi')], [b('canceled', '❌ Bekor')]]);
}

// ---------- o'z dizaynim ----------
async function handleImage(u, chat, fileId) {
  const wait = await send(chat, t(u).processing);
  try {
    const buf = await tg.download(fileId);
    const ext = buf[0] === 0x89 ? '.png' : '.jpg';
    let shape = null;
    try { shape = await design.makeShape(buf); } catch (e) { console.error('Dizayn xatosi:', e.message); }
    if (!shape || shape.stats.complex) return manualRequest(u, chat, buf, ext);
    keepDesign(u.id, { shape, original: buf, ext });
    db.saveFile(`dizayn-${u.id}${ext}`, buf); u.designFile = `dizayn-${u.id}${ext}`;
    const sizes = CFG.custom_sizes; const def = sizes[Math.min(1, sizes.length - 1)];
    u.s = { flow: 'custom', step: 'size', title: '', size: def.cm, price: def.price, color: 'qora' };
    await sendPreview(u, chat);
    await send(chat, t(u).ask_size, { reply_markup: ik(chunk(sizes.map(z => ({ text: `${z.cm} ${u.lang === 'ru' ? 'см' : 'sm'} — ${money(z.price, u.lang)}`, callback_data: 'sz:' + z.cm })), 1)) });
  } catch (e) {
    console.error('Dizayn xatosi:', e.message);
    await send(chat, t(u).bad_image);
  } finally {
    tg.call('deleteMessage', { chat_id: chat, message_id: wait.message_id }).catch(() => {});
  }
}

function rememberReq(adminChat, msgId, userId) {
  const m = db.state.mreq || (db.state.mreq = {});
  m[`${adminChat}:${msgId}`] = { userId, at: Date.now() };
  const keys = Object.keys(m); if (keys.length > 300) for (const k of keys.slice(0, keys.length - 300)) delete m[k];
  db.save();
}
// Admin javobi: chizilgan dizayn rasmini mijozga buyurtma tugmasi bilan yuboramiz
async function adminManualReply(admin, chat, m) {
  const req = db.state.mreq[`${chat}:${m.reply_to_message.message_id}`];
  const cu = db.users[String(req.userId)];
  const ph = m.photo ? m.photo[m.photo.length - 1].file_id : (m.document && /^image\//.test(m.document.mime_type || '') ? m.document.file_id : null);
  if (!cu) return send(chat, 'Mijoz topilmadi.');
  if (!ph) {
    if (m.text) { await send(cu.id, `💬 ${esc(m.text)}`).catch(() => {}); return send(chat, '✅ Matn mijozga yuborildi.'); }
    return send(chat, 'Dizayn rasmini yuboring (javob qilib).');
  }
  const note = (m.caption || '').trim();
  const L = T[cu.lang || 'uz'];
  const rid = 'd' + Date.now().toString(36);
  (cu.mdesigns || (cu.mdesigns = {}))[rid] = ph;
  const ks = Object.keys(cu.mdesigns); if (ks.length > 10) delete cu.mdesigns[ks[0]];
  try {
    const r = await tg.call('sendPhoto', { chat_id: cu.id, photo: ph, caption: L.manual_ready(esc(note)), parse_mode: 'HTML',
      reply_markup: ik([[{ text: L.manual_order_btn, callback_data: 'mbuy:' + rid }], [{ text: L.manual_change_btn, callback_data: 'mchg:' + rid }]]) });
    rememberReq(chat, m.message_id, cu.id); // keyingi tuzatishlar uchun ham shu zanjir ishlaydi
    db.save();
    return send(chat, `✅ Dizayn mijozga yuborildi (${esc(cu.name || cu.id)}).`, { reply_to_message_id: m.message_id });
  } catch (e) { return send(chat, '❌ Yuborilmadi: ' + esc(e.message)); }
}
async function manualChange(u, chat, text) {
  if (text.length < 2) return send(chat, t(u).manual_change);
  u.s = {};
  const who = `<a href="tg://user?id=${u.id}">${esc(u.name || 'Mijoz')}</a>${u.username ? ' @' + esc(u.username) : ''}`;
  await toAdmins(async a => { const r = await send(a, `✏️ <b>Dizaynga tuzatish</b> — ${who}\n\n${esc(text.slice(0, 800))}\n\n👉 Yangi dizaynni shu xabarga javob qilib yuboring.`); rememberReq(a, r.message_id, u.id); });
  return send(chat, t(u).manual_change_sent, { reply_markup: mainKb(u) });
}

// ---------- lazer kesish (DXF) ----------
function laserIntro(u) {
  const rates = LASER.rates.map(r => `• ${r.label} — ${money(r.rate, u.lang)}`).join('\n');
  return t(u).laser_intro(rates, LASER.sheet_mm.join('×'));
}
async function handleDxf(u, chat, doc) {
  const wait = await send(chat, t(u).laser_wait);
  try {
    if ((doc.file_size || 0) > 19 * 1024 * 1024) throw new Error('BIG');
    const buf = await tg.download(doc.file_id);
    const r = dxfcalc.analyze(buf.toString('latin1'));
    if (!(r.meters > 0)) throw new Error('ZERO');
    const meters = +r.meters.toFixed(2);
    u.s = { flow: 'laser', step: 'laser_thick', fileId: doc.file_id, fname: String(doc.file_name || 'chizma.dxf').slice(0, 60), meters, w: r.widthMm, h: r.heightMm };
    await send(chat, t(u).laser_thick(meters, r.widthMm, r.heightMm), { reply_markup: ik(chunk(LASER.rates.map((x, i) => ({ text: x.label, callback_data: 'lt:' + i })), 2)) });
  } catch (e) {
    console.error('DXF xatosi:', e.message);
    u.s = { flow: 'laser', step: 'laser_file' };
    await send(chat, t(u).laser_bad);
  } finally { tg.call('deleteMessage', { chat_id: chat, message_id: wait.message_id }).catch(() => {}); }
}
async function laserQuote(u, chat, idx) {
  const s = u.s; const tier = LASER.rates[idx]; if (!tier || s.flow !== 'laser' || !s.meters) return;
  const piece = Math.max(1000, Math.round(s.meters * tier.rate / 100) * 100);
  const [W, Hh] = LASER.sheet_mm; const fits = (s.w <= W && s.h <= Hh) || (s.w <= Hh && s.h <= W);
  Object.assign(s, { step: 'laser_quote', tier: tier.label, price: piece, title: T.uz.laser_name(s.fname, tier.label), titleL: t(u).laser_name(s.fname, tier.label) });
  return send(chat, t(u).laser_quote(s.meters, esc(tier.label), money(tier.rate, u.lang), money(piece, u.lang), !fits), {
    reply_markup: ik([[{ text: t(u).buy, callback_data: 'lbuy' }], [{ text: t(u).laser_other, callback_data: 'lre' }]]) });
}

// ---------- do'stni taklif qilish ----------
function showInvite(u, chat) {
  const link = `https://t.me/${BOT_NAME}?start=r${u.id}`;
  const share = `https://t.me/share/url?url=${encodeURIComponent(link)}&text=${encodeURIComponent(t(u).invite_share_text)}`;
  return send(chat, t(u).invite(link, REF.percent) + ((u.refBonus || 0) > 0 ? t(u).invite_bonus_have(u.refBonus) : ''), { reply_markup: ik([[{ text: t(u).invite_share, url: share }]]) });
}

// ---------- fikr va rasm (topshirilgandan keyin) ----------
async function askRating(o) {
  const L = T[o.lang || 'uz'];
  await send(o.userId, L.rate_ask(o.id), { reply_markup: ik([[1, 2, 3, 4, 5].map(n => ({ text: `${n}⭐`, callback_data: `rate:${o.id}:${n}` }))]) });
}
async function onRate(u, chat, id, n) {
  const o = db.orders.find(x => x.id === id && x.userId === u.id); if (!o || o.rating) return;
  o.rating = Math.max(1, Math.min(5, n)); db.save();
  const who = `<a href="tg://user?id=${u.id}">${esc(o.name || u.name || 'Mijoz')}</a>`;
  await toAdmins(a => send(a, `${o.rating <= 3 ? '⚠️ ' : ''}⭐ <b>${o.id}</b> — baho: ${'⭐'.repeat(o.rating)} (${o.rating}/5) · ${who}${o.rating <= 3 ? '\nMijoz bilan bog\'laning!' : ''}`));
  u.s = { flow: 'review', step: 'review', oid: o.id };
  await send(chat, o.rating <= 3 ? t(u).review_low : t(u).review_ask, { reply_markup: ik([[{ text: t(u).skip, callback_data: 'rskip' }]]) });
}
async function reviewText(u, chat, text) {
  const o = db.orders.find(x => x.id === u.s.oid); u.s = {};
  if (o && text) { o.comment = text.slice(0, 1000); db.save(); await toAdmins(a => send(a, `💬 <b>${o.id}</b> fikri (${'⭐'.repeat(o.rating || 0)}):\n${esc(o.comment)}`)); }
  await send(chat, t(u).review_thanks, { reply_markup: mainKb(u) });
  if (REF.enabled && (o && o.rating >= 4)) return showInvite(u, chat);
}
async function reviewPhoto(u, chat, fileId) {
  const o = db.orders.find(x => x.id === u.s.oid);
  u.s = {};
  if (!o) return send(chat, t(u).review_thanks, { reply_markup: mainKb(u) });
  (o.reviewPhotos || (o.reviewPhotos = [])).push(fileId); db.save();
  await toAdmins(a => tg.call('sendPhoto', { chat_id: a, photo: fileId, caption: `📸 ${o.id} — mijoz rasmi (${'⭐'.repeat(o.rating || 0)})\nInstagram ruxsati: kutilmoqda` }));
  return send(chat, t(u).ig_ask, { reply_markup: ik([[{ text: t(u).ig_yes, callback_data: `ig:${o.id}:1` }, { text: t(u).ig_no, callback_data: `ig:${o.id}:0` }]]) });
}
// Ruxsat berilgan mijoz rasmlarini GitHub'dagi yangi/mijoz/ papkasiga yuklaymiz — haftalik Reels vazifasi ularni ishlatadi
const GH_TOKEN = (process.env.GH_TOKEN || '').trim();
const GH_REPO = (process.env.GH_REPO || 'oybekkjon1994-coder/metartshop').trim();
const GH_API = (process.env.GH_API || 'https://api.github.com').replace(/\/$/, '');
async function uploadForReels(o) {
  if (!GH_TOKEN || !(o.reviewPhotos || []).length) return 0;
  let n = 0;
  for (const [i, fid] of o.reviewPhotos.entries()) {
    try {
      const buf = await tg.download(fid);
      const fp = `yangi/mijoz/${o.id}-${i + 1}.jpg`;
      const res = await fetch(`${GH_API}/repos/${GH_REPO}/contents/${fp}`, {
        method: 'PUT', signal: AbortSignal.timeout(60000),
        headers: { authorization: 'Bearer ' + GH_TOKEN, accept: 'application/vnd.github+json', 'content-type': 'application/json', 'user-agent': 'metartshop-bot' },
        body: JSON.stringify({ message: `Mijoz rasmi ${o.id} (Instagram ruxsati bor, ${o.rating || '-'}⭐)`, content: buf.toString('base64') }),
      });
      if (res.ok || res.status === 422) n++; else console.error('GitHub yuklash:', res.status, (await res.text()).slice(0, 200));
    } catch (e) { console.error('GitHub yuklash xatosi:', e.message); }
  }
  return n;
}
async function onIg(u, chat, id, yes) {
  const o = db.orders.find(x => x.id === id && x.userId === u.id); if (!o || o.igOk !== undefined) return;
  o.igOk = !!yes; db.save();
  if (o.igOk) uploadForReels(o).then(n => { if (n) { o.reelsUploaded = n; db.save(); toAdmins(a => send(a, `🎬 ${o.id}: ${n} ta mijoz rasmi Reels uchun yuklandi — haftalik videolarga qo'shiladi.`)); } }).catch(() => {});
  await toAdmins(a => send(a, `📸 ${o.id} — Instagram'da ko'rsatishga ruxsat: ${o.igOk ? '✅ BOR' : '❌ yo\'q'}`));
  await send(chat, t(u).review_thanks, { reply_markup: mainKb(u) });
  if (REF.enabled) return showInvite(u, chat);
}

// ---------- oldindan to'lov ----------
async function askPayment(u, chat, o) {
  const card = db.state.card;
  if (!card || !(o.price > 0) || o.paid === true) return;
  const pct = Math.max(1, Math.min(100, PAY.prepay_percent || 50));
  const sum = Math.round(orderTotal(o) * pct / 100 / 1000) * 1000 || orderTotal(o);
  o.prepay = sum; db.save();
  u.s = { flow: 'pay', step: 'receipt', oid: o.id };
  return send(chat, t(u).pay_info(o.id, money(sum, u.lang), pct, esc(card.number), esc(card.holder || '')), { reply_markup: ik([[{ text: t(u).pay_later, callback_data: 'paylater' }]]) });
}
async function gotReceipt(u, chat, fileId, oid, isDoc) {
  const o = db.orders.find(x => x.id === oid && x.userId === u.id); u.s = {};
  if (!o) return send(chat, t(u).use_menu, { reply_markup: mainKb(u) });
  o.paid = 'pending'; o.receipt = fileId; db.save();
  await toAdmins(a => tg.call(isDoc ? 'sendDocument' : 'sendPhoto', { chat_id: a, [isDoc ? 'document' : 'photo']: fileId, parse_mode: 'HTML',
    caption: `💳 <b>To'lov cheki — ${o.id}</b>\nKutilgan summa: ${money(o.prepay || orderTotal(o), 'uz')}\n👤 ${esc(o.name)} · ${esc(o.phone)}\n\nKartangizga pul tushganini tekshiring:`,
    reply_markup: ik([[{ text: '✅ Pul tushdi', callback_data: `pay:${o.id}:ok` }, { text: '❌ Topilmadi', callback_data: `pay:${o.id}:no` }]]) }));
  return send(chat, t(u).pay_receipt_got, { reply_markup: mainKb(u) });
}
async function onPayDecision(q, id, ok) {
  const o = db.orders.find(x => x.id === id); if (!o || o.paid === true) return;
  o.paid = ok ? true : false; o.paidAt = ok ? new Date().toISOString() : undefined;
  if (ok && o.status === 'new') o.status = 'accepted';
  db.save();
  const L = T[o.lang || 'uz'];
  await tg.call('editMessageReplyMarkup', { chat_id: q.message.chat.id, message_id: q.message.message_id, reply_markup: ik([[{ text: ok ? '✅ Tasdiqlandi' : '❌ Rad etildi', callback_data: 'noop' }]]) }).catch(() => {});
  await send(o.userId, ok ? L.pay_ok(o.id) : L.pay_no(o.id), ok ? {} : { reply_markup: ik([[{ text: L.pay_btn(o.id), callback_data: 'paynow:' + o.id }]]) }).catch(() => {});
}
async function adminCard(chat, arg) {
  if (/^o['ʻ’`]?chir/i.test(arg.trim())) { delete db.state.card; db.saveNow(); return send(chat, '✅ Karta o\'chirildi — oldindan to\'lov so\'ralmaydi.'); }
  const m = arg.match(/^([\d\s]{16,23})\s*(.*)$/);
  if (!m) return send(chat, db.state.card ? `💳 Hozirgi karta: <code>${esc(db.state.card.number)}</code> ${esc(db.state.card.holder || '')}\n\nO'zgartirish: /karta 8600 1234 5678 9012 Ism Familiya\nO'chirish: /karta o'chir` : (/^o/i.test(arg) ? '' : 'Foydalanish: /karta 8600 1234 5678 9012 Ism Familiya\nShundan keyin har buyurtmadan keyin mijozga oldindan to\'lov uchun karta raqami va chek yuborish so\'raladi.'));
  const digits = m[1].replace(/\D/g, '');
  if (digits.length !== 16) return send(chat, 'Karta raqami 16 ta raqam bo\'lishi kerak.');
  db.state.card = { number: digits.replace(/(\d{4})(?=\d)/g, '$1 '), holder: m[2].trim().slice(0, 60) }; db.saveNow();
  return send(chat, `✅ Karta saqlandi: <code>${esc(db.state.card.number)}</code> ${esc(db.state.card.holder)}\nOldindan to'lov: ${PAY.prepay_percent}%`);
}

// Murakkab rasm: avtomatik dizayn o'rniga usta qo'lda chizadi (mijoz yo'qolmasin)
async function manualRequest(u, chat, buf, ext) {
  const name = `qolda-${u.id}-${Date.now()}${ext}`;
  db.saveFile(name, buf);
  u.s = { flow: 'manual', step: 'manual_phone', file: name };
  db.save();
  const who = `<a href="tg://user?id=${u.id}">${esc(u.name || 'Mijoz')}</a>${u.username ? ' @' + esc(u.username) : ''}`;
  await toAdmins(async a => {
    const r = await tg.call('sendPhoto', { chat_id: a, photo: TG.file(buf, name, ext === '.png' ? 'image/png' : 'image/jpeg'),
      caption: `🖼 <b>Qo'lda dizayn so'rovi</b>\n👤 ${who}\nRasm murakkab — avtomatik chizilmadi.\n\n👉 Dizaynni chizib, <b>shu xabarga javob (reply) qilib rasmini yuboring</b> — mijozga o'zim yetkazaman. Rasm izohiga narx yoki izoh yozishingiz mumkin.`, parse_mode: 'HTML' });
    rememberReq(a, r.message_id, u.id);
  });
  return manualAsk(u, chat);
}
function manualAsk(u, chat) {
  const kb = [[{ text: t(u).share_phone, request_contact: true }]]; if (u.lastPhone) kb.push([u.lastPhone]);
  return send(chat, t(u).manual_design, { reply_markup: { keyboard: kb, resize_keyboard: true, one_time_keyboard: true } });
}
async function manualPhone(u, chat, raw) {
  let digits = String(raw).replace(/\D/g, '');
  if (digits.length === 10 && digits[0] === '0') digits = digits.slice(1);
  if (digits.length < 9 || digits.length > 13) return send(chat, t(u).bad_phone);
  const ph = digits.length === 9 ? '+998' + digits : '+' + digits;
  u.lastPhone = ph; u.s = {}; db.save();
  const who = `<a href="tg://user?id=${u.id}">${esc(u.name || 'Mijoz')}</a>${u.username ? ' @' + esc(u.username) : ''}`;
  await toAdmins(a => send(a, `📞 <b>Qo'lda dizayn</b> — ${who}\nTelefon: ${esc(ph)}`));
  return send(chat, t(u).manual_thanks, { reply_markup: mainKb(u) });
}

async function reloadDesign(u) {
  if (!u.designFile) return null;
  try {
    const buf = fs.readFileSync(path.join(db.dir, 'fayllar', u.designFile));
    const d = { shape: await design.makeShape(buf), original: buf, ext: path.extname(u.designFile) };
    keepDesign(u.id, d); return d;
  } catch { return null; }
}

async function sendPreview(u, chat) {
  const d = designs.get(u.id) || await reloadDesign(u); if (!d) return;
  const col = COLOR_NAMES[u.lang][u.s.color] || u.s.color;
  const img = await design.makePreview(d.shape, u.s.color, `${u.s.size} sm · ${COLOR_NAMES.uz[u.s.color] || u.s.color}`);
  return tg.call('sendPhoto', { chat_id: chat, photo: TG.file(img, 'dizayn.jpg', 'image/jpeg'), caption: t(u).preview_caption(u.s.size, col), reply_markup: ik([[{ text: t(u).room_btn, callback_data: 'room' }]]) });
}
// Mijoz xonasi rasmiga soatni joylash
async function handleRoom(u, chat, fileId) {
  u.s.roomWait = false;
  const d = designs.get(u.id) || await reloadDesign(u);
  if (!d) return send(chat, t(u).custom_intro);
  const wait = await send(chat, t(u).processing);
  try {
    const room = await tg.download(fileId);
    const img = await design.makePreview(d.shape, u.s.color || 'qora', `${u.s.size} sm · ${COLOR_NAMES.uz[u.s.color] || u.s.color}`, room, u.s.size || 40);
    await tg.call('sendPhoto', { chat_id: chat, photo: TG.file(img, 'devor.jpg', 'image/jpeg'), caption: t(u).room_caption(u.s.size), reply_markup: ik([[{ text: t(u).room_btn, callback_data: 'room' }]]) });
    if (u.s.step === 'size') return send(chat, t(u).ask_size, { reply_markup: ik(chunk(CFG.custom_sizes.map(z => ({ text: `${z.cm} ${u.lang === 'ru' ? 'см' : 'sm'} — ${money(z.price, u.lang)}`, callback_data: 'sz:' + z.cm })), 1)) });
    if (u.s.step === 'color') return send(chat, t(u).ask_color_custom, { reply_markup: ik(chunk(CFG.custom_colors.map(cl => ({ text: COLOR_NAMES[u.lang][cl] || cl, callback_data: 'col:' + cl })), 4).concat([[{ text: t(u).next, callback_data: 'cnext' }]])) });
    return resume(u, chat);
  } catch (e) { console.error('Xona rasmi xatosi:', e.message); return send(chat, t(u).bad_image); }
  finally { tg.call('deleteMessage', { chat_id: chat, message_id: wait.message_id }).catch(() => {}); }
}

// ---------- tugma bosilganda ----------
async function onCallback(q) {
  const u = db.user(q.from); const chat = q.message ? q.message.chat.id : q.from.id; const data = q.data || '';
  tg.call('answerCallbackQuery', { callback_query_id: q.id }).catch(() => {});
  const [k, a, b] = data.split(':');
  const s = u.s || (u.s = {});
  try {
    switch (k) {
      case 'lang': {
        u.lang = a === 'ru' ? 'ru' : 'uz'; const pend = u.pending; delete u.pending;
        await send(chat, t(u).welcome(esc(u.name || '')), { reply_markup: mainKb(u) });
        if (u.refPending) { delete u.refPending; await send(chat, t(u).ref_welcome(REF.percent)); }
        await deepLink(u, chat, pend); break;
      }
      case 'cats': await showCats(u, chat, q.message && q.message.message_id); break;
      case 'cat': await showCat(u, chat, a); break;
      case 'p': await showProduct(u, chat, a); break;
      case 'img': await showProduct(u, chat, a, +b || 0); break;
      case 'buy': await startBuy(u, chat, a); break;
      case 'custom': u.s = { flow: 'custom', step: 'await_image' }; await send(chat, t(u).custom_intro); break;
      case 'col':
        if (s.flow === 'product' && s.step === 'color') { s.color = a; await askQty(u, chat); }
        else if (s.flow === 'custom' && s.step === 'color') { s.color = a; await sendPreview(u, chat); await send(chat, '👍', { reply_markup: ik([[{ text: t(u).next, callback_data: 'cnext' }]]) }); }
        else if (s.flow === 'manual' && s.step === 'color') { s.color = a; await send(chat, `👍 ${COLOR_NAMES[u.lang][a] || a}`, { reply_markup: ik([[{ text: t(u).next, callback_data: 'cnext' }]]) }); }
        break;
      case 'sz': {
        if (s.flow !== 'custom' && s.flow !== 'manual') break;
        const z = CFG.custom_sizes.find(x => String(x.cm) === a); if (!z) break;
        s.size = z.cm; s.price = z.price; s.title = T.uz.custom_name(z.cm); s.titleL = t(u).custom_name(z.cm); s.step = 'color';
        await send(chat, t(u).ask_color_custom, { reply_markup: ik(chunk(CFG.custom_colors.map(cl => ({ text: COLOR_NAMES[u.lang][cl] || cl, callback_data: 'col:' + cl })), 4).concat([[{ text: t(u).next, callback_data: 'cnext' }]])) });
        break;
      }
      case 'cnext': if ((s.flow === 'custom' || s.flow === 'manual') && s.step === 'color' && s.size && s.title) await askQty(u, chat); break;
      case 'qty':
        if (s.step !== 'qty') break;
        if (a === 'x') { s.step = 'qty_text'; await send(chat, t(u).ask_qty_text); }
        else { s.qty = +a; await askName(u, chat); }
        break;
      case 'dlv':
        if (s.step !== 'delivery') break;
        s.delivery = a;
        if (a === 'self') { s.address = ''; await showSummary(u, chat); }
        else { s.step = 'address'; await send(chat, t(u).ask_address, { reply_markup: { remove_keyboard: true } }); }
        break;
      case 'ok': if (s.step === 'confirm') await placeOrder(u, chat); break;
      case 'no': u.s = {}; await send(chat, t(u).canceled, { reply_markup: mainKb(u) }); break;
      case 'st': if (isAdmin(u.id)) await setStatus(q, a, b); break;
      case 'mbuy': {
        const ph = (u.mdesigns || {})[a]; if (!ph) break;
        const sizes = CFG.custom_sizes;
        u.s = { flow: 'manual', step: 'size', designPhoto: ph, color: 'qora' };
        await send(chat, t(u).ask_size, { reply_markup: ik(chunk(sizes.map(z => ({ text: `${z.cm} ${u.lang === 'ru' ? 'см' : 'sm'} — ${money(z.price, u.lang)}`, callback_data: 'sz:' + z.cm })), 1)) });
        break;
      }
      case 'mchg': u.s = { flow: 'mchange', step: 'manual_change' }; await send(chat, t(u).manual_change); break;
      case 'rate': await onRate(u, chat, a, +b); break;
      case 'lt': await laserQuote(u, chat, +a); break;
      case 'laser': if (LASER.enabled) { u.s = { flow: 'laser', step: 'laser_file' }; await send(chat, laserIntro(u)); } break;
      case 'room': if (s.flow === 'custom' && s.size) { s.roomWait = true; await send(chat, t(u).room_ask); } break;
      case 'lre': if (s.flow === 'laser' && s.meters) { s.step = 'laser_thick'; await send(chat, t(u).laser_thick(s.meters, s.w, s.h), { reply_markup: ik(chunk(LASER.rates.map((x, i) => ({ text: x.label, callback_data: 'lt:' + i })), 2)) }); } break;
      case 'lbuy': if (s.flow === 'laser' && s.step === 'laser_quote') await askQty(u, chat); break;
      case 'gift': u.s = {}; await showCats(u, chat); break;
      case 'rskip': u.s = {}; await send(chat, t(u).review_thanks, { reply_markup: mainKb(u) }); break;
      case 'ig': await onIg(u, chat, a, b === '1'); break;
      case 'paylater': u.s = {}; await send(chat, t(u).pay_later_ok, { reply_markup: mainKb(u) }); break;
      case 'paynow': { const o = db.orders.find(x => x.id === a && x.userId === u.id); if (o) { o.paid = o.paid === true ? true : undefined; await askPayment(u, chat, o); } break; }
      case 'pay': if (isAdmin(u.id)) await onPayDecision(q, a, b === 'ok'); break;
      case 'resume': await resume(u, chat); break;
      case 'stop': u.optOut = true; await send(chat, t(u).stopped, { reply_markup: mainKb(u) }); break;
    }
  } finally { db.save(); }
}

async function myOrders(u, chat) {
  const mine = db.orders.filter(o => o.userId === u.id).slice(-10).reverse();
  if (!mine.length) return send(chat, t(u).no_orders);
  const unpaid = db.state.card ? mine.filter(o => o.price > 0 && o.paid !== true && o.paid !== 'pending' && !['canceled', 'done'].includes(o.status)) : [];
  return send(chat, t(u).my_orders + '\n\n' + mine.map(o => `<b>${o.id}</b> · ${esc(o.titleL || o.title)} ×${o.qty}\n${t(u).status[o.status]}${o.paid === true ? ' · ' + t(u).paid.yes : o.paid === 'pending' ? ' · ' + t(u).paid.pending : ''}`).join('\n\n'),
    unpaid.length ? { reply_markup: ik(unpaid.slice(0, 3).map(o => [{ text: t(u).pay_btn(o.id), callback_data: 'paynow:' + o.id }])) } : {});
}

// ---------- admin ----------
async function adminLogin(u, chat, code) {
  if ((u.adminFails || 0) >= 5) return send(chat, '⛔');
  if (!ADMIN_CODE || ADMIN_CODE.length < 8 || code !== ADMIN_CODE) {
    u.adminFails = (u.adminFails || 0) + 1; db.save();
    if (ADMIN_CODE && ADMIN_CODE.length < 8) console.error('❗ ADMIN_CODE juda qisqa (kamida 8 belgi bo\'lsin) — .env ni tuzating.');
    return send(chat, '⛔');
  }
  u.adminFails = 0;
  if (!db.state.admins.includes(u.id)) db.state.admins.push(u.id);
  db.save();
  return adminHelp(chat, '✅ Siz admin bo\'ldingiz. Yangi buyurtmalar shu yerga keladi.\n\n');
}
function adminHelp(chat, pre = '') {
  return send(chat, pre + '<b>Admin buyruqlari</b>\n/buyurtmalar — oxirgi buyurtmalar\n/statistika — umumiy hisob\n/xabar MATN — barcha mijozlarga xabar (rasm bilan ham: rasm yuborib izohiga /xabar yozing)\n/karta 8600… Ism — oldindan to\'lov uchun karta (/karta o\'chir — o\'chirish)\n/yordam — shu ro\'yxat\n\n🖼 Qo\'lda dizayn so\'roviga <b>javob (reply)</b> qilib rasm yuborsangiz, mijozga yetkaziladi.');
}
async function adminOrders(chat) {
  const list = db.orders.slice(-15).reverse();
  if (!list.length) return send(chat, 'Hali buyurtma yo\'q.');
  for (const o of list.slice(0, 5)) await send(chat, `<b>${o.id}</b> · ${T.uz.status[o.status]}\n${orderLines('uz', o)}`, { reply_markup: statusKb(o) });
  if (list.length > 5) await send(chat, list.slice(5).map(o => `${o.id} · ${esc(o.title)} · ${T.uz.status[o.status]}`).join('\n'));
}
async function adminStats(chat) {
  const users = Object.keys(db.users).length; const os = db.orders;
  const by = st => os.filter(o => o.status === st).length;
  const sum = os.filter(o => !['canceled'].includes(o.status)).reduce((a, o) => a + orderTotal(o), 0);
  const tz = ts => new Date(Date.parse(ts) + 5 * 3600 * 1000).toISOString().slice(0, 10);
  const today = tz(new Date().toISOString());
  return send(chat, `📊 <b>Statistika</b>\n\n👥 Bot foydalanuvchilari: ${users}\n📦 Buyurtmalar: ${os.length} (bugun: ${os.filter(o => tz(o.at) === today).length})\n🆕 Yangi: ${by('new')} · ✅ Qabul: ${by('accepted')} · 🔧 ${by('making')} · 🚚 ${by('sent')} · 🎉 ${by('done')} · ❌ ${by('canceled')}\n💰 Jami summa (bekor qilinmagan): ${money(sum, 'uz')}\n🎨 O'z dizayni buyurtmalari: ${os.filter(o => o.flow === 'custom').length}`);
}
async function adminBroadcast(chat, text, m) {
  if (!text) return send(chat, 'Foydalanish: /xabar Bugun barcha soatlarga 10% chegirma!');
  const ids = Object.keys(db.users).map(Number).filter(id => !isAdmin(id) && !db.users[id].blocked);
  await send(chat, `📣 ${ids.length} ta foydalanuvchiga yuborilmoqda...`);
  let ok = 0;
  for (const id of ids) {
    try { await send(id, esc(text)); ok++; } catch (e) { if (e.code === 403) db.users[id].blocked = true; }
    await new Promise(r => setTimeout(r, 60));
  }
  db.save();
  return send(chat, `✅ Yuborildi: ${ok}/${ids.length}`);
}
async function adminBroadcastPhoto(chat, m) {
  const photo = m.photo[m.photo.length - 1].file_id;
  const caption = (m.caption || '').replace(/^\/xabar\s*/, '');
  const ids = Object.keys(db.users).map(Number).filter(id => !isAdmin(id) && !db.users[id].blocked);
  await send(chat, `📣 ${ids.length} ta foydalanuvchiga rasm yuborilmoqda...`);
  let ok = 0;
  for (const id of ids) {
    try { await tg.call('sendPhoto', { chat_id: id, photo, caption }); ok++; } catch (e) { if (e.code === 403) db.users[id].blocked = true; }
    await new Promise(r => setTimeout(r, 60));
  }
  db.save();
  return send(chat, `✅ Yuborildi: ${ok}/${ids.length}`);
}
async function setStatus(q, id, st) {
  const o = db.orders.find(x => x.id === id); if (!o || !T.uz.status[st] || o.status === st) return;
  o.status = st; o.updated = new Date().toISOString(); db.save();
  await tg.call('editMessageReplyMarkup', { chat_id: q.message.chat.id, message_id: q.message.message_id, reply_markup: statusKb(o) }).catch(() => {});
  const L = o.lang || 'uz';
  await send(o.userId, T[L].status_note(o.id, T[L].status[st])).catch(() => {});
  if (st === 'done') {
    if (!o.rateAsked) { o.rateAsked = true; db.save(); await askRating(o).catch(() => {}); }
    // Do'stini taklif qilganga bonus: do'stning birinchi buyurtmasi topshirilganda (bir marta)
    if (REF.enabled && o.discountType === 'friend' && o.refBy && !o.refRewarded) {
      const r = db.users[String(o.refBy)];
      o.refRewarded = true;
      if (r) { r.refBonus = (r.refBonus || 0) + 1; r.refCount = (r.refCount || 0) + 1; db.save(); await send(r.id, T[r.lang || 'uz'].ref_bonus(REF.percent)).catch(() => {}); }
    }
  }
}

// ---------- avtomatik takliflar ----------
const OFF = Object.assign({ enabled: true, from_hour: 10, to_hour: 20, abandon_hours: 2, viewed_hours: 20, weekly_days: 7, repeat_days: 30, max_per_tick: 25 }, CFG.auto_offers || {});
const H = 3600 * 1000, D = 24 * H;
const stopBtn = u => ({ text: t(u).stop_btn, callback_data: 'stop' });

async function resume(u, chat) {
  const s = u.s || {};
  if (!s.flow) return send(chat, t(u).use_menu, { reply_markup: mainKb(u) });
  switch (s.step) {
    case 'color': if (s.flow === 'manual') return send(chat, t(u).ask_color_custom, { reply_markup: ik(chunk(CFG.custom_colors.map(cl => ({ text: COLOR_NAMES[u.lang][cl] || cl, callback_data: 'col:' + cl })), 4).concat([[{ text: t(u).next, callback_data: 'cnext' }]])) });
      return s.flow === 'product' ? startBuy(u, chat, s.pid) : (await sendPreview(u, chat), send(chat, t(u).ask_color_custom, { reply_markup: ik(chunk(CFG.custom_colors.map(cl => ({ text: COLOR_NAMES[u.lang][cl] || cl, callback_data: 'col:' + cl })), 4).concat([[{ text: t(u).next, callback_data: 'cnext' }]])) }));
    case 'size': if (s.flow === 'custom') await sendPreview(u, chat); return send(chat, t(u).ask_size, { reply_markup: ik(chunk(CFG.custom_sizes.map(z => ({ text: `${z.cm} ${u.lang === 'ru' ? 'см' : 'sm'} — ${money(z.price, u.lang)}`, callback_data: 'sz:' + z.cm })), 1)) });
    case 'qty': case 'qty_text': return askQty(u, chat);
    case 'name': return askName(u, chat);
    case 'phone': return askPhone(u, chat);
    case 'delivery': return gotPhone(u, chat, s.phone || u.lastPhone || '');
    case 'address': return send(chat, t(u).ask_address);
    case 'confirm': return showSummary(u, chat);
    case 'laser_thick': case 'laser_quote': return send(chat, t(u).laser_thick(s.meters, s.w, s.h), { reply_markup: ik(chunk(LASER.rates.map((x, i) => ({ text: x.label, callback_data: 'lt:' + i })), 2)) });
    case 'laser_file': return send(chat, laserIntro(u));
    default: return send(chat, t(u).custom_intro);
  }
}

function pickWeekly(u, c) {
  const list = c.products.filter(p => p.stock !== false && p.price > 0 && (p.imgs || []).length && !(u.orderedPids || []).includes(p.id));
  if (!list.length) return null;
  db.state.promoIdx = ((db.state.promoIdx || 0) + 1) % 100000;
  const start = (db.state.promoIdx + (u.id % list.length)) % list.length;
  for (let i = 0; i < list.length; i++) { const p = list[(start + i) % list.length]; if (p.id !== u.lastPromoPid) return p; }
  return list[0];
}

// Yaqinlashayotgan bayram (Toshkent sanasi bo'yicha): days_before kun ichida, bayramdan 1 kun oldingacha
function activeHoliday(now) {
  if (!HOL.enabled || !HOL.list.length) return null;
  const tz = new Date(now + 5 * H);
  let y = tz.getUTCFullYear(), mo = tz.getUTCMonth() + 1, d = tz.getUTCDate();
  if (process.env.HOLIDAY_TODAY) [mo, d] = process.env.HOLIDAY_TODAY.split('-').map(Number);
  const today = Date.UTC(y, mo - 1, d);
  for (const h of HOL.list) {
    const [hm, hd] = h.date.split('-').map(Number);
    for (const yy of [y, y + 1]) {
      const days = Math.round((Date.UTC(yy, hm - 1, hd) - today) / D);
      if (days >= 1 && days <= HOL.days_before) return { ...h, days, key: `${h.id}-${yy}` };
    }
  }
  return null;
}

async function offersTick() {
  if (!OFF.enabled) return;
  const hour = new Date(Date.now() + 5 * H).getUTCHours(); // Toshkent vaqti
  if (!process.env.OFFERS_NOW && (hour < OFF.from_hour || hour >= OFF.to_hour)) return;
  const now = Date.now(); let sent = 0, holSent = 0; const c = await getCatalog();
  const hol = activeHoliday(now);
  for (const u of Object.values(db.users)) {
    if (sent >= OFF.max_per_tick) break;
    if (!u.lang || u.optOut || u.blocked || isAdmin(u.id)) continue;
    if (u.lastSeen && now - u.lastSeen < 30 * 60 * 1000) continue; // hozir botda — bezovta qilmaymiz
    try {
      const s = u.s || {};
      // 1) yarim qolgan buyurtma
      if (['custom', 'product', 'manual', 'laser'].includes(s.flow) && s.step && !['await_image', 'manual_phone', 'laser_file'].includes(s.step) && u.sAt && now - u.sAt > OFF.abandon_hours * H && now - u.sAt < 3 * D && (u.remindedAt || 0) < u.sAt) {
        u.remindedAt = now; sent++;
        await send(u.id, s.flow === 'custom' ? t(u).remind_custom : t(u).remind, { reply_markup: ik([[{ text: t(u).resume_btn, callback_data: 'resume' }], [{ text: t(u).cancel, callback_data: 'no' }, stopBtn(u)]]) });
        continue;
      }
      // 2) bayram oldidan sovg'a taklifi (har bayramga bir marta)
      if (hol && u.hol !== hol.key) {
        u.hol = hol.key; u.lastPromo = now; sent++; holSent++;
        await send(u.id, t(u).holiday_offer(esc(hol[u.lang] || hol.uz), hol.days), { reply_markup: ik([[{ text: t(u).gift_btn, callback_data: 'gift' }], [{ text: t(u).m_custom, callback_data: 'custom' }], [stopBtn(u)]]) });
        continue;
      }
      // 3) ko'rib ketgan, lekin buyurtma bermagan
      const v = u.viewed;
      if (v && !v.offered && now - v.at > OFF.viewed_hours * H && now - v.at < 7 * D && !(u.ordered > v.at)) {
        const p = c.products.find(x => x.id === v.pid);
        v.offered = true;
        if (p && p.stock !== false) {
          sent++; u.lastOfferAt = now;
          const cap = t(u).viewed_offer(esc(pname(p, u.lang)), p.price > 0 ? money(p.price, u.lang) : '');
          const kb = ik([[{ text: t(u).buy, callback_data: 'buy:' + p.id }], [stopBtn(u)]]);
          const img = (p.imgs || [])[0];
          if (img) await tg.call('sendPhoto', { chat_id: u.id, photo: imgUrl(img), caption: cap, parse_mode: 'HTML', reply_markup: kb }).catch(() => send(u.id, cap, { reply_markup: kb }));
          else await send(u.id, cap, { reply_markup: kb });
          continue;
        }
      }
      // 3) haftalik taklif (oldingi mijozlarga alohida matn)
      const joined = Date.parse(u.joined) || now;
      const last = Math.max(u.lastPromo || 0, u.lastOfferAt || 0, u.remindedAt || 0);
      const repeat = u.ordered && now - u.ordered > OFF.repeat_days * D && u.repeatOfferFor !== u.ordered;
      if (now - joined > 2 * D && now - last > OFF.weekly_days * D && (!u.ordered || repeat)) {
        const p = pickWeekly(u, c); if (!p) continue;
        u.lastPromo = now; u.lastPromoPid = p.id; sent++;
        if (repeat) u.repeatOfferFor = u.ordered;
        const cap = (repeat ? t(u).repeat_offer : t(u).weekly_offer)(esc(pname(p, u.lang)), money(p.price, u.lang));
        const kb = ik([[{ text: t(u).buy, callback_data: 'buy:' + p.id }], [{ text: t(u).m_custom, callback_data: 'custom' }], [stopBtn(u)]]);
        await tg.call('sendPhoto', { chat_id: u.id, photo: imgUrl(p.imgs[0]), caption: cap, parse_mode: 'HTML', reply_markup: kb }).catch(() => send(u.id, cap, { reply_markup: kb }));
      }
    } catch (e) {
      if (e.code === 403) u.blocked = true; else console.error('Taklif yuborilmadi:', e.message);
    }
    await new Promise(r => setTimeout(r, 120));
  }
  if (holSent) {
    const st = db.state.holStat || (db.state.holStat = {});
    if (!st[hol.key]) { st[hol.key] = 0; await toAdmins(a => send(a, `🎁 Bayram aksiyasi boshlandi: <b>${esc(hol.uz)}</b> — mijozlarga sovg'a taklifi yuborilmoqda.`)); }
    st[hol.key] += holSent;
  }
  if (sent) { console.log(`Avtomatik takliflar: ${sent} ta yuborildi`); db.save(); }
}

// ---------- ishga tushirish ----------
async function main() {
  const me = await tg.call('getMe'); BOT_NAME = me.username;
  console.log(`\n✅ Bot ishga tushdi: @${me.username}`);
  console.log(`   Havolalar: https://t.me/${me.username}?start=dizayn  |  https://t.me/${me.username}?start=klub`);
  const codeHash = require('crypto').createHash('sha256').update(ADMIN_CODE).digest('hex');
  if (db.state.adminCodeHash && db.state.adminCodeHash !== codeHash) { db.state.admins = []; console.log('   ADMIN_CODE o\'zgargan — eski adminlar o\'chirildi.'); }
  db.state.adminCodeHash = codeHash; db.saveNow();
  if (!db.state.admins.length) console.log('   ❗ Admin hali ulanmagan: botga  /admin KOD  deb yozing (KOD — .env dagi ADMIN_CODE).');
  await tg.call('setMyCommands', { commands: [{ command: 'start', description: 'Bosh menyu / Главное меню' }] }).catch(() => {});
  getCatalog();
  setInterval(() => { retryNotifications().catch(() => {}); offersTick().catch(e => console.error('Takliflar xatosi:', e.message)); }, 10 * 60 * 1000);
  retryNotifications().catch(() => {});
  setTimeout(() => offersTick().catch(e => console.error('Takliflar xatosi:', e.message)), process.env.OFFERS_NOW ? 1500 : 60 * 1000);
  const stop = () => { db.saveNow(); process.exit(0); };
  process.on('SIGINT', stop); process.on('SIGTERM', stop); process.on('SIGHUP', stop);
  await tg.poll(onUpdate, () => db.state.offset, o => { db.state.offset = o; db.save(); });
}
main().catch(e => {
  console.error(e.code === 401 ? '\n❗ BOT_TOKEN noto\'g\'ri. .env faylidagi tokenni tekshiring.\n' : 'Ishga tushmadi: ' + e.message);
  process.exit(e.code === 401 ? 2 : 1);
});
