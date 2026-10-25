// Oddiy JSON fayl saqlagich (buyurtmalar, foydalanuvchilar, sozlamalar)
'use strict';
const fs = require('fs');
const path = require('path');

class Store {
  constructor(dir) {
    this.dir = dir;
    fs.mkdirSync(dir, { recursive: true });
    fs.mkdirSync(path.join(dir, 'fayllar'), { recursive: true });
    this.state = this.load('state.json', { offset: 0, admins: [], orderSeq: 0 });
    this.users = this.load('users.json', {});
    this.orders = this.load('orders.json', []);
    this.timer = null;
  }
  load(name, def) {
    const p = path.join(this.dir, name);
    let raw;
    try { raw = fs.readFileSync(p, 'utf8'); } catch (e) { if (e.code === 'ENOENT') return def; throw e; }
    try { return JSON.parse(raw); } catch {
      // Buzilgan faylni o'chirib yubormaymiz: nusxasini saqlab, aniq xabar beramiz
      const bad = p + '.buzilgan-' + Date.now();
      fs.copyFileSync(p, bad);
      throw new Error(`${name} fayli buzilgan. Nusxasi: ${bad}. Faylni tuzating yoki zaxiradan tiklang.`);
    }
  }
  writeAtomic(p, text) {
    fs.writeFileSync(p + '.tmp', text);
    for (let i = 0; ; i++) {
      try { fs.renameSync(p + '.tmp', p); return; } catch (e) {
        // Windows: antivirus/OneDrive faylni ushlab tursa, biroz kutib qayta urinamiz
        if (i >= 5 || !['EPERM', 'EBUSY', 'EACCES'].includes(e.code)) { fs.copyFileSync(p + '.tmp', p); return; }
        const until = Date.now() + 100 * (i + 1); while (Date.now() < until) { /* kutish */ }
      }
    }
  }
  saveNow() {
    clearTimeout(this.timer);
    for (const [name, v] of [['state.json', this.state], ['users.json', this.users], ['orders.json', this.orders]]) {
      try { this.writeAtomic(path.join(this.dir, name), JSON.stringify(v, null, 1)); }
      catch (e) { console.error(`❗ ${name} saqlanmadi (keyinroq qayta uriniladi):`, e.message); this.save(); }
    }
  }
  save() { clearTimeout(this.timer); this.timer = setTimeout(() => this.saveNow(), 300); }

  user(from) {
    const id = String(from.id);
    const u = this.users[id] || (this.users[id] = { id: from.id, lang: null, joined: new Date().toISOString(), s: {} });
    u.name = [from.first_name, from.last_name].filter(Boolean).join(' ');
    u.username = from.username || '';
    return u;
  }
  nextOrderId() { this.state.orderSeq++; return 'M-' + String(this.state.orderSeq).padStart(4, '0'); }
  saveFile(name, buf) { const p = path.join(this.dir, 'fayllar', name); fs.writeFileSync(p, buf); return p; }
}

module.exports = Store;
