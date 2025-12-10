// Safegloss Service Worker for Offline Support
const CACHE_NAME = 'safegloss-v1';
const OFFLINE_URL = '/offline/';

// Assets to cache immediately on install
const PRECACHE_ASSETS = [
  OFFLINE_URL,
  '/static/core/css/styles.css',
  '/static/core/icons/favicon.ico',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js',
];

// Install event - cache core assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(PRECACHE_ASSETS);
    })
  );
  self.skipWaiting();
});

// Activate event - clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    })
  );
  self.clients.claim();
});

// Fetch event - network first, fall back to cache
self.addEventListener('fetch', (event) => {
  // Skip non-GET requests
  if (event.request.method !== 'GET') return;

  // Skip cross-origin requests except CDNs
  const url = new URL(event.request.url);
  const isSameOrigin = url.origin === location.origin;
  const isCDN = url.hostname.includes('cdn.jsdelivr.net');

  if (!isSameOrigin && !isCDN) return;

  event.respondWith(
    // Try network first
    fetch(event.request)
      .then((response) => {
        // Clone response to cache it
        const responseClone = response.clone();

        // Cache successful responses
        if (response.status === 200) {
          caches.open(CACHE_NAME).then((cache) => {
            // Only cache GET requests for HTML, CSS, JS, images
            const contentType = response.headers.get('content-type') || '';
            if (
              contentType.includes('text/html') ||
              contentType.includes('text/css') ||
              contentType.includes('javascript') ||
              contentType.includes('image/')
            ) {
              cache.put(event.request, responseClone);
            }
          });
        }

        return response;
      })
      .catch(() => {
        // Network failed, try cache
        return caches.match(event.request).then((cachedResponse) => {
          if (cachedResponse) {
            return cachedResponse;
          }

          // If it's a navigation request, show offline page
          if (event.request.mode === 'navigate') {
            return caches.match(OFFLINE_URL);
          }

          // Return a basic offline response for other requests
          return new Response('Offline', {
            status: 503,
            statusText: 'Service Unavailable',
            headers: new Headers({ 'Content-Type': 'text/plain' }),
          });
        });
      })
  );
});

// =============================================================================
// INDEXEDDB FOR OFFLINE QUIZ STORAGE
// =============================================================================

const DB_NAME = 'safegloss-offline';
const DB_VERSION = 1;
const STORE_NAME = 'pending-quiz-submissions';

function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);

    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: 'id', autoIncrement: true });
      }
    };
  });
}

async function getPendingSubmissions() {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readonly');
    const store = tx.objectStore(STORE_NAME);
    const request = store.getAll();
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function deleteSubmission(id) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    const request = store.delete(id);
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}

// =============================================================================
// BACKGROUND SYNC FOR QUIZ SUBMISSIONS
// =============================================================================

self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-quiz') {
    event.waitUntil(syncQuizSubmissions());
  }
});

async function syncQuizSubmissions() {
  console.log('Background sync: Starting quiz sync...');

  try {
    const submissions = await getPendingSubmissions();
    console.log(`Found ${submissions.length} pending submissions`);

    for (const submission of submissions) {
      try {
        const response = await fetch(submission.url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': submission.csrfToken,
          },
          body: submission.formData,
          credentials: 'same-origin',
        });

        if (response.ok || response.status === 302) {
          // Success - delete from queue
          await deleteSubmission(submission.id);
          console.log(`Synced submission ${submission.id}`);

          // Notify the user
          self.registration.showNotification('Quiz Submitted', {
            body: 'Your offline quiz answer has been synced.',
            icon: '/static/core/icons/icon-192.png',
            badge: '/static/core/icons/icon-72.png',
          });
        } else {
          console.warn(`Failed to sync submission ${submission.id}: ${response.status}`);
        }
      } catch (err) {
        console.error(`Error syncing submission ${submission.id}:`, err);
      }
    }
  } catch (err) {
    console.error('Background sync error:', err);
  }
}

// Handle messages from the main page
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SYNC_QUIZ') {
    event.waitUntil(syncQuizSubmissions());
  }
});
