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
    try { return JSON.parse(fs.readFileSync(path.join(this.dir, name), 'utf8')); } catch { return def; }
  }
  saveNow() {
    for (const [name, v] of [['state.json', this.state], ['users.json', this.users], ['orders.json', this.orders]]) {
      const p = path.join(this.dir, name);
      fs.writeFileSync(p + '.tmp', JSON.stringify(v, null, 1));
      fs.renameSync(p + '.tmp', p);
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
