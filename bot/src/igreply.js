// Instagram izohlariga AI bilan avtomatik javob (Instagram Graph API, polling — webhook/server shart emas).
// .env: IG_TOKEN = Facebook sahifa tokeni (instagram_basic + instagram_manage_comments ruxsatlari bilan)
'use strict';
const esc = s => String(s ?? '').replace(/[<>&]/g, c => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;' }[c]));

function create({ token, api, db, ai, notify, log = console }) {
  const base = (api || 'https://graph.facebook.com').replace(/\/$/, '');
  let igId = null, myName = '', warned = false;
  const st = () => db.state.ig || (db.state.ig = { done: {}, replies: 0 });

  async function g(path, params = {}, method = 'GET') {
    const u = new URL(base + '/' + path.replace(/^\//, ''));
    const body = new URLSearchParams({ ...params, access_token: token });
    const res = method === 'GET'
      ? await fetch(u + '?' + body, { signal: AbortSignal.timeout(20000) })
      : await fetch(u, { method, body, signal: AbortSignal.timeout(20000) });
    const j = await res.json().catch(() => ({}));
    if (!res.ok || j.error) { const e = new Error((j.error && j.error.message) || 'HTTP ' + res.status); e.code = j.error && j.error.code; throw e; }
    return j;
  }

  async function init() {
    const me = await g('me', { fields: 'id,name,instagram_business_account{id,username}' });
    if (!me.instagram_business_account) throw new Error('Sahifaga Instagram biznes akkaunt ulanmagan');
    igId = me.instagram_business_account.id; myName = me.instagram_business_account.username || '';
    log.log(`   Instagram izohlari: @${myName} ulandi (har 3 daqiqada tekshiriladi)`);
  }

  async function tick() {
    try {
      if (!igId) await init();
      const S = st(); const now = Date.now(); let n = 0;
      const media = await g(`${igId}/media`, { fields: 'id,caption,timestamp,permalink', limit: '15' });
      for (const m of media.data || []) {
        const cm = await g(`${m.id}/comments`, { fields: 'id,text,username,timestamp,replies{username}', limit: '50' });
        for (const c of cm.data || []) {
          if (S.done[c.id] || n >= 15) continue;
          const age = now - Date.parse(c.timestamp || 0);
          const ours = (c.replies && c.replies.data || []).some(r => r.username === myName);
          if (c.username === myName || ours || age > 3 * 24 * 3600e3) { S.done[c.id] = now; continue; }
          let reply = '';
          try { reply = await ai(c.text || '', (m.caption || '').slice(0, 400)); } catch (e) { log.error('IG AI xatosi:', e.message); continue; }
          S.done[c.id] = now;
          if (!reply || /^SKIP\b/i.test(reply)) continue;
          reply = reply.replace(/\[\[[^\]]*\]\]/g, '').replace(/\*\*/g, '').trim().slice(0, 600);
          await g(`${c.id}/replies`, { message: `@${c.username} ${reply}` }, 'POST');
          n++; S.replies = (S.replies || 0) + 1;
          notify(`💬 <b>Instagram izohi</b> (@${esc(c.username)}):\n${esc(c.text)}\n\n🤖 Javob: ${esc(reply)}${m.permalink ? `\n${esc(m.permalink)}` : ''}`);
        }
      }
      // eski yozuvlarni tozalash (7 kundan eski)
      for (const [k, v] of Object.entries(S.done)) if (now - v > 7 * 24 * 3600e3) delete S.done[k];
      warned = false; db.save();
      return n;
    } catch (e) {
      log.error('Instagram izohlari xatosi:', e.message);
      if (!warned && (e.code === 190 || e.code === 10 || e.code === 200)) { warned = true; notify(`⚠️ Instagram izohlariga ulanishda xato: ${esc(e.message)}\nIG_TOKEN ni yangilash kerak bo'lishi mumkin.`); }
      return 0;
    }
  }
  return { tick };
}

module.exports = { create };
