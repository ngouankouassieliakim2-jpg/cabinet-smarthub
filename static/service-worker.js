// Service worker minimal -- sert uniquement à rendre l'application installable.
// Aucune mise en cache, aucun fonctionnement hors connexion, exactement comme demandé :
// sans connexion, l'application ne fait rien, comme une appli classique qui a besoin du réseau.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));
self.addEventListener('fetch', () => {});
