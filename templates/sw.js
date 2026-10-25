/* KamKarao service worker: caches the app shell so repeat visits load fast on slow networks. */
const CACHE = "kk-v1";
const SHELL = ["/static/css/app.css", "/static/js/app.js", "/static/vendor/htmx.min.js", "/static/img/icon.svg"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))));
  self.clients.claim();
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  if (url.pathname.startsWith("/static/") || url.pathname.startsWith("/media/")) {
    // Static files: cache first.
    e.respondWith(caches.match(e.request).then((hit) => hit || fetch(e.request).then((res) => {
      const copy = res.clone();
      caches.open(CACHE).then((c) => c.put(e.request, copy));
      return res;
    })));
    return;
  }
  if (e.request.mode === "navigate") {
    // Pages: always fresh, fall back to a friendly offline page.
    e.respondWith(fetch(e.request).catch(() => caches.match("/hi/offline/").then((r) => r || Response.error())));
  }
});
