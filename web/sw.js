// Service Worker de Integrated — Garantiza funcionamiento 100% offline sin internet
const CACHE_NAME = 'integrated-simulador-offline-v11';
const RECURSOS_CACHE = [
  './',
  './index.html',
  './estilos.css',
  './traductor_web.js',
  './app.js?v=simulador-2',
  './manifest.json',
  './icono.svg'
];

self.addEventListener('install', (evento) => {
  evento.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(RECURSOS_CACHE);
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (evento) => {
  evento.waitUntil(
    caches.keys().then((claves) => {
      return Promise.all(
        claves.map((clave) => {
          if (clave !== CACHE_NAME) {
            return caches.delete(clave);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (evento) => {
  const solicitud = evento.request;
  const url = new URL(solicitud.url);
  if (solicitud.method !== 'GET' || url.origin !== self.location.origin) {
    return;
  }
  if (url.pathname.startsWith('/api/')) {
    return;
  }

  evento.respondWith(
    (async () => {
      const esNavegacion = solicitud.mode === 'navigate';
      const respuestaCache = await caches.match(solicitud);

      if (respuestaCache && !esNavegacion) {
        return respuestaCache;
      }

      try {
        const respuestaRed = await fetch(solicitud);
        if (respuestaRed && respuestaRed.status === 200 && respuestaRed.type === 'basic') {
          const cache = await caches.open(CACHE_NAME);
          await cache.put(solicitud, respuestaRed.clone());
        }
        return respuestaRed;
      } catch (error) {
        if (respuestaCache) return respuestaCache;
        if (esNavegacion) {
          const paginaInicio = await caches.match('./index.html');
          if (paginaInicio) return paginaInicio;
        }
        throw error;
      }
    })()
  );
});
