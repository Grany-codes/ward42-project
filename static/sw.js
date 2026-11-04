const cacheName = 'fixit-v1';
const appShell = ['/', '/static/css/style.css', '/static/js/main.js', '/offline.html'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(cacheName).then(cache => cache.addAll(appShell)));
});

self.addEventListener('fetch', e => {
  e.respondWith(
    caches.match(e.request).then(res => res || fetch(e.request).catch(() => caches.match('/offline.html')))
  );
});