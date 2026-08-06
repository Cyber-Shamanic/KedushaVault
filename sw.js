const CACHE = "kedusha-vault-1.0.0";
const CORE = [
  "./", "./index.html", "./assets/css/styles.css", "./assets/js/markdown.js",
  "./assets/js/app.js", "./assets/icons/icon.svg", "./manifest.webmanifest",
  "./data/chapters.json", "./data/chapters.js", "./data/docs.js", "./cards/preview/KedushaPath_Fronts_Preview.jpg"
];

self.addEventListener("install", event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(CORE)));
  self.skipWaiting();
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(keys.filter(key => key !== CACHE).map(key => caches.delete(key))))
  );
  self.clients.claim();
});

self.addEventListener("fetch", event => {
  if (event.request.method !== "GET") return;
  event.respondWith(
    caches.match(event.request).then(cached => cached || fetch(event.request).then(response => {
      if (response.ok && new URL(event.request.url).origin === self.location.origin) {
        const clone = response.clone();
        caches.open(CACHE).then(cache => cache.put(event.request, clone));
      }
      return response;
    }))
  );
});
