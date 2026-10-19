// Metartshop service worker: works offline, always tries fresh data first
const CACHE = "metartshop-v1";
const SHELL = ["./", "index.html", "manifest.json", "img/logo.png", "img/icon-192.png", "img/icon-512.png"];
self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return; // GitHub API, fonts, Telegram: straight to network
  const isImg = url.pathname.includes("/img/");
  if (isImg) {
    // images never change name: cache first
    e.respondWith(caches.match(req).then(hit => hit || fetch(req).then(res => {
      const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)); return res;
    })));
    return;
  }
  // page and data.json: network first, cache when offline
  const key = url.pathname.endsWith("data.json") ? new Request(url.origin + url.pathname) : req;
  e.respondWith(fetch(req).then(res => {
    if (res.ok) { const copy = res.clone(); caches.open(CACHE).then(c => c.put(key, copy)); }
    return res;
  }).catch(() => caches.match(key).then(hit => hit || caches.match("index.html"))));
});
