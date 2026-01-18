// Service Worker for Darshi - Offline support and caching
const CACHE_NAME = 'darshi-v2';
const STATIC_CACHE = 'darshi-static-v2';
const DYNAMIC_CACHE = 'darshi-dynamic-v2';
const IMAGE_CACHE = 'darshi-images-v2';
const MAP_TILE_CACHE = 'darshi-map-tiles-v2';

// Static assets to cache on install
const STATIC_ASSETS = [
	'/',
	'/fonts.css',
	'/manifest.json'
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
	console.log('[SW] Installing service worker...');
	event.waitUntil(
		caches.open(STATIC_CACHE).then((cache) => {
			console.log('[SW] Caching static assets');
			return cache.addAll(STATIC_ASSETS);
		}).catch((err) => {
			console.log('[SW] Cache failed:', err);
		})
	);
	self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
	console.log('[SW] Activating service worker...');
	event.waitUntil(
		caches.keys().then((cacheNames) => {
			return Promise.all(
				cacheNames.map((cache) => {
					if (cache !== STATIC_CACHE && cache !== DYNAMIC_CACHE && cache !== IMAGE_CACHE && cache !== MAP_TILE_CACHE) {
						console.log('[SW] Clearing old cache:', cache);
						return caches.delete(cache);
					}
				})
			);
		})
	);
	self.clients.claim();
});

// Fetch event - network first with cache fallback
self.addEventListener('fetch', (event) => {
	const { request } = event;
	const url = new URL(request.url);

	// Handle OpenStreetMap tile requests - cache first with network fallback
	if (url.hostname.includes('tile.openstreetmap.org')) {
		event.respondWith(
			caches.open(MAP_TILE_CACHE).then((cache) => {
				return cache.match(request).then((cachedResponse) => {
					if (cachedResponse) {
						// Return cached tile immediately
						return cachedResponse;
					}
					// Fetch from network and cache
					return fetch(request).then((response) => {
						if (response.status === 200) {
							// Cache successful tile requests
							cache.put(request, response.clone());
						}
						return response;
					}).catch(() => {
						// Return empty tile if offline and not cached
						return new Response('', { status: 404 });
					});
				});
			})
		);
		return;
	}

	// Skip other cross-origin requests
	if (url.origin !== location.origin) {
		return;
	}

	// Handle images separately - cache first strategy
	if (request.destination === 'image') {
		event.respondWith(
			caches.open(IMAGE_CACHE).then((cache) => {
				return cache.match(request).then((cachedResponse) => {
					if (cachedResponse) {
						return cachedResponse;
					}
					return fetch(request).then((response) => {
						// Only cache successful responses
						if (response.status === 200) {
							cache.put(request, response.clone());
						}
						return response;
					}).catch(() => {
						// Return placeholder if offline and not cached
						return new Response('', { status: 404 });
					});
				});
			})
		);
		return;
	}

	// Handle API requests - network first, cache fallback
	// EXCLUDE auth endpoints from caching to prevent stale user data
	if (url.pathname.startsWith('/api/') &&
		!url.pathname.includes('/auth/') &&
		!url.pathname.includes('/oauth/') &&
		!url.pathname.includes('/health')) {
		event.respondWith(
			fetch(request)
				.then((response) => {
					// Clone response for caching
					const responseClone = response.clone();
					if (response.status === 200) {
						caches.open(DYNAMIC_CACHE).then((cache) => {
							cache.put(request, responseClone);
						});
					}
					return response;
				})
				.catch(() => {
					// Return cached version if offline
					return caches.match(request).then((cachedResponse) => {
						if (cachedResponse) {
							return cachedResponse;
						}
						// Return offline response
						return new Response(JSON.stringify({
							error: 'Offline',
							message: 'You are currently offline'
						}), {
							status: 503,
							headers: { 'Content-Type': 'application/json' }
						});
					});
				})
		);
		return;
	}

	// Handle navigation requests - network first with cache fallback
	if (request.mode === 'navigate') {
		event.respondWith(
			fetch(request)
				.then((response) => {
					const responseClone = response.clone();
					caches.open(DYNAMIC_CACHE).then((cache) => {
						cache.put(request, responseClone);
					});
					return response;
				})
				.catch(() => {
					return caches.match(request).then((cachedResponse) => {
						if (cachedResponse) {
							return cachedResponse;
						}
						// Fallback to cached homepage
						return caches.match('/');
					});
				})
		);
		return;
	}

	// Default: network first, cache fallback
	event.respondWith(
		fetch(request)
			.then((response) => {
				if (response.status === 200) {
					const responseClone = response.clone();
					caches.open(DYNAMIC_CACHE).then((cache) => {
						cache.put(request, responseClone);
					});
				}
				return response;
			})
			.catch(() => {
				return caches.match(request);
			})
	);
});

// Background sync for offline report submissions
self.addEventListener('sync', (event) => {
	if (event.tag === 'sync-reports') {
		event.waitUntil(syncReports());
	}
});

async function syncReports() {
	// Implementation for syncing offline-created reports
	console.log('[SW] Syncing reports...');
	// This would be implemented with IndexedDB for storing offline submissions
}

// Push notifications support
self.addEventListener('push', (event) => {
	console.log('[SW] Push received:', event);

	if (!event.data) {
		console.log('[SW] Push event but no data');
		return;
	}

	try {
		const data = event.data.json();
		console.log('[SW] Push data:', data);

		const title = data.title || 'Darshi Notification';
		const options = {
			body: data.message || 'You have a new notification',
			icon: '/icon-192.png',
			badge: '/icon-96.png',
			data: {
				url: data.url || '/',
				report_id: data.report_id,
				notification_id: data.notification_id,
				timestamp: data.timestamp || new Date().toISOString()
			},
			tag: data.notification_id || `notification-${Date.now()}`,
			requireInteraction: false,
			vibrate: [200, 100, 200],
			actions: [
				{
					action: 'view',
					title: 'View'
				},
				{
					action: 'close',
					title: 'Dismiss'
				}
			]
		};

		event.waitUntil(
			self.registration.showNotification(title, options)
		);
	} catch (error) {
		console.error('[SW] Error parsing push data:', error);
		event.waitUntil(
			self.registration.showNotification('Darshi Notification', {
				body: 'You have a new notification',
				icon: '/icon-192.png'
			})
		);
	}
});

self.addEventListener('notificationclick', (event) => {
	console.log('[SW] Notification clicked:', event);

	event.notification.close();

	// Handle action buttons
	if (event.action === 'close') {
		return;
	}

	// Get the URL to open
	const urlToOpen = event.notification.data?.url || '/';

	// Open or focus the client window
	event.waitUntil(
		clients.matchAll({
			type: 'window',
			includeUncontrolled: true
		}).then((clientList) => {
			// Check if there's already a window open
			for (let i = 0; i < clientList.length; i++) {
				const client = clientList[i];
				if (client.url.startsWith(self.location.origin)) {
					return client.focus().then(() => {
						return client.navigate(urlToOpen);
					});
				}
			}
			// No existing window found, open a new one
			if (clients.openWindow) {
				return clients.openWindow(urlToOpen);
			}
		})
	);
});
