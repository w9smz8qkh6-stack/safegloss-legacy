/**
 * Offline Quiz Submission Handler
 * Saves quiz submissions to IndexedDB when offline and syncs when back online
 */

const OfflineQuiz = (function() {
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

  async function saveSubmission(url, formData, csrfToken) {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite');
      const store = tx.objectStore(STORE_NAME);

      const submission = {
        url: url,
        formData: formData,
        csrfToken: csrfToken,
        timestamp: Date.now(),
      };

      const request = store.add(submission);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  async function getPendingCount() {
    try {
      const db = await openDB();
      return new Promise((resolve, reject) => {
        const tx = db.transaction(STORE_NAME, 'readonly');
        const store = tx.objectStore(STORE_NAME);
        const request = store.count();
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
      });
    } catch (e) {
      return 0;
    }
  }

  function registerSync() {
    if ('serviceWorker' in navigator && 'sync' in window.SyncManager) {
      navigator.serviceWorker.ready.then((registration) => {
        registration.sync.register('sync-quiz').catch((err) => {
          console.log('Background sync registration failed:', err);
        });
      });
    }
  }

  function setupFormHandler(form) {
    if (!form) return;

    form.addEventListener('submit', async function(event) {
      // Check if we're online
      if (navigator.onLine) {
        // Let the form submit normally
        return;
      }

      // Offline - save to IndexedDB
      event.preventDefault();

      const formData = new URLSearchParams(new FormData(form)).toString();
      const csrfToken = form.querySelector('[name="csrfmiddlewaretoken"]')?.value || '';
      const url = form.action || window.location.href;

      try {
        await saveSubmission(url, formData, csrfToken);
        registerSync();

        // Show offline message
        showOfflineMessage();
      } catch (err) {
        console.error('Failed to save offline submission:', err);
        alert('Could not save your quiz. Please try again when online.');
      }
    });
  }

  function showOfflineMessage() {
    // Create or update offline message
    let msg = document.getElementById('offline-quiz-message');
    if (!msg) {
      msg = document.createElement('div');
      msg.id = 'offline-quiz-message';
      msg.className = 'alert alert-warning alert-dismissible fade show position-fixed';
      msg.style.cssText = 'bottom: 1rem; right: 1rem; z-index: 1060; max-width: 350px;';
      msg.innerHTML = `
        <i class="bi bi-cloud-arrow-up me-2"></i>
        <strong>Saved Offline</strong><br>
        Your quiz answer will be submitted when you're back online.
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
      `;
      document.body.appendChild(msg);
    }
  }

  async function showPendingBadge() {
    const count = await getPendingCount();
    if (count > 0) {
      let badge = document.getElementById('pending-sync-badge');
      if (!badge) {
        badge = document.createElement('div');
        badge.id = 'pending-sync-badge';
        badge.className = 'position-fixed badge bg-warning text-dark';
        badge.style.cssText = 'bottom: 1rem; left: 1rem; z-index: 1060;';
        document.body.appendChild(badge);
      }
      badge.innerHTML = `<i class="bi bi-cloud-arrow-up"></i> ${count} pending sync`;
      badge.style.display = 'block';
    }
  }

  // Listen for online event to trigger sync
  window.addEventListener('online', () => {
    console.log('Back online - triggering sync');
    registerSync();

    // Also try direct sync via message
    if (navigator.serviceWorker.controller) {
      navigator.serviceWorker.controller.postMessage({ type: 'SYNC_QUIZ' });
    }

    // Hide pending badge
    const badge = document.getElementById('pending-sync-badge');
    if (badge) badge.style.display = 'none';
  });

  // Initialize
  function init() {
    // Setup any quiz forms
    document.querySelectorAll('form.quiz-form').forEach(setupFormHandler);

    // Show pending badge if any
    showPendingBadge();
  }

  // Auto-init when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  return {
    saveSubmission,
    getPendingCount,
    registerSync,
    setupFormHandler,
  };
})();
