// Telegram Bot API uchun kichik mijoz (qo'shimcha kutubxonasiz, Node 18+ fetch)
'use strict';

class TG {
  constructor(token, base = 'https://api.telegram.org') {
    this.token = token;
    this.base = base.replace(/\/$/, '');
  }
  url(method) { return `${this.base}/bot${this.token}/${method}`; }

  async call(method, params = {}) {
    const hasFile = Object.values(params).some(v => v && typeof v === 'object' && v.__file);
    let res;
    if (hasFile) {
      const fd = new FormData();
      for (const [k, v] of Object.entries(params)) {
        if (v === undefined || v === null) continue;
        if (v && v.__file) fd.append(k, new Blob([v.data], { type: v.type || 'application/octet-stream' }), v.name);
        else fd.append(k, typeof v === 'object' ? JSON.stringify(v) : String(v));
      }
      res = await fetch(this.url(method), { method: 'POST', body: fd });
    } else {
      res = await fetch(this.url(method), {
        method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(params),
      });
    }
    const json = await res.json().catch(() => ({ ok: false, description: 'bad json' }));
    if (!json.ok) {
      const err = new Error(`${method}: ${json.description || res.status}`);
      err.code = json.error_code; err.retry = json.parameters && json.parameters.retry_after;
      throw err;
    }
    return json.result;
  }

  static file(data, name, type) { return { __file: true, data, name, type }; }

  async download(fileId) {
    const f = await this.call('getFile', { file_id: fileId });
    const res = await fetch(`${this.base}/file/bot${this.token}/${f.file_path}`);
    if (!res.ok) throw new Error('download ' + res.status);
    return Buffer.from(await res.arrayBuffer());
  }

  // Uzluksiz so'rov (long polling)
  async poll(onUpdate, getOffset, setOffset) {
    for (;;) {
      try {
        const ups = await this.call('getUpdates', { offset: getOffset(), timeout: 30, allowed_updates: ['message', 'callback_query'] });
        for (const u of ups) {
          setOffset(u.update_id + 1);
          try { await onUpdate(u); } catch (e) { console.error('Xato (update):', e); }
        }
      } catch (e) {
        if (e.code === 401) { console.error('\nBOT_TOKEN noto\'g\'ri! .env faylini tekshiring.\n'); process.exit(2); }
        if (e.code === 409) console.error('Boshqa joyda ham shu bot ishlab turibdi (409). Faqat bitta oynada ishga tushiring.');
        else console.error('Ulanish xatosi:', e.message);
        await new Promise(r => setTimeout(r, (e.retry || 3) * 1000));
      }
    }
  }
}

module.exports = TG;
