// Service worker — « À l'eau, les Moutiers ! »
// Objectif : lancement offline depuis le raccourci + installabilité Android, SANS piéger sur une vieille version.
// Stratégie : réseau d'abord pour le HTML (jamais périmé), cache d'abord pour les assets, version.json et /hit toujours au réseau.
const V = '2026.08.04-0945';
const CACHE = 'moutiers-' + V;
const SHELL = ['/', '/manifest.webmanifest', '/icon-192.png', '/icon-512.png', '/icon-512-maskable.png'];

self.addEventListener('install', (e) => {
  e.waitUntil((async () => {
    try { const c = await caches.open(CACHE); await c.addAll(SHELL); } catch (_) {}
    self.skipWaiting();
  })());
});

self.addEventListener('activate', (e) => {
  e.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)));
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;   // APIs, PostHog, beacon… : laissés au navigateur
  if (url.pathname === '/hit') return;                // compteur : jamais de cache
  if (url.pathname === '/version.json') return;       // auto-mise à jour : toujours frais

  // HTML / navigations : réseau d'abord (évite le cache périmé), cache en secours hors-ligne
  if (req.mode === 'navigate' || (req.headers.get('accept') || '').includes('text/html')) {
    e.respondWith((async () => {
      try {
        const net = await fetch(req);
        try { const c = await caches.open(CACHE); c.put('/', net.clone()); } catch (_) {}
        return net;
      } catch (_) {
        return (await caches.match('/')) || (await caches.match('/index.html')) || Response.error();
      }
    })());
    return;
  }

  // autres GET même origine (icônes, manifest) : cache d'abord
  e.respondWith((async () => {
    const hit = await caches.match(req);
    if (hit) return hit;
    try {
      const net = await fetch(req);
      try { const c = await caches.open(CACHE); c.put(req, net.clone()); } catch (_) {}
      return net;
    } catch (_) { return Response.error(); }
  })());
});
