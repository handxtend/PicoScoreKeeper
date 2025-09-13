const CACHE='psk-starter-v1';
const ASSETS=['/','/index.html','/manifest.webmanifest','/src/styles.css','/src/app.js','/src/api.js'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS)).then(()=>self.skipWaiting()))});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()))});
self.addEventListener('fetch',e=>{const u=new URL(e.request.url); if(e.request.method!=='GET') return; if(u.origin===location.origin){e.respondWith(caches.match(e.request).then(r=>r||fetch(e.request)))}});
