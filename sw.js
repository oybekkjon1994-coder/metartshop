// Metartshop service worker v2: never intercepts page loads (safer inside Instagram's browser);
// only caches images and data so the catalog still shows when the connection drops.
const CACHE = "metartshop-v2";
self.addEventListener("install", e => { self.skipWaiting(); });
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET" || req.mode === "navigate") return; // page loads go straight to the network
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;
  if (url.pathname.includes("/img/")) {
    e.respondWith(caches.match(req).then(hit => hit || fetch(req).then(res => {
      if (res.ok) { const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)); }
      return res;
    })));
    return;
  }
  if (url.pathname.endsWith("data.json")) {
    const key = new Request(url.origin + url.pathname);
    e.respondWith(fetch(req).then(res => {
      if (res.ok) { const copy = res.clone(); caches.open(CACHE).then(c => c.put(key, copy)); }
      return res;
    }).catch(() => caches.match(key).then(hit => hit || Response.error())));
  }
});
