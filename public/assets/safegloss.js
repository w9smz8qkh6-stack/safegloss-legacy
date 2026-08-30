(() => {
    'use strict';

    const layout = document.querySelector('.reading-layout');
    if (!layout) {
        return;
    }

    const attemptId = layout.dataset.attemptId;
    const csrfToken = layout.dataset.csrfToken;
    const margin = layout.querySelector('.gloss-margin');
    const isContiguous = layout.classList.contains('treatment-contiguous');
    let active = null;

    const decodeDefinition = (encoded) => {
        const bytes = Uint8Array.from(atob(encoded), character => character.charCodeAt(0));
        return new TextDecoder().decode(bytes);
    };

    const recordEvent = async (action, term) => {
        const data = new FormData();
        data.set('csrf_token', csrfToken);
        data.set('attempt_id', attemptId);
        data.set('event_action', action);
        data.set('term', term);
        data.set('client_event_id', crypto.randomUUID());
        data.set('client_recorded_at', new Date().toISOString());
        data.set('client_timezone_offset', String(new Date().getTimezoneOffset()));
        try {
            await fetch('/event.php', { method: 'POST', body: data, credentials: 'same-origin', keepalive: true });
        } catch (_error) {
            // The server remains the source of truth; a later action may still be recorded.
        }
    };

    const closeGloss = async () => {
        if (!active) {
            return;
        }
        const { button, panel, term } = active;
        active = null;
        button.setAttribute('aria-expanded', 'false');
        if (isContiguous) {
            panel.remove();
        } else {
            margin.innerHTML = '<p>Select a blue word to view its definition.</p>';
        }
        await recordEvent('gloss_close', term);
    };

    const openGloss = async (button) => {
        if (active?.button === button) {
            await closeGloss();
            return;
        }
        await closeGloss();

        const term = button.dataset.term;
        const definition = decodeDefinition(button.dataset.definition);
        const panel = document.createElement('section');
        panel.className = isContiguous ? 'gloss-popover' : 'gloss-panel-content';
        panel.setAttribute('role', 'dialog');
        panel.setAttribute('aria-label', `Glossary definition for ${term}`);
        panel.innerHTML = `<div class="gloss-heading"><strong></strong><button class="gloss-close" type="button" aria-label="Close definition">×</button></div><div class="gloss-definition"></div>`;
        panel.querySelector('strong').textContent = term;
        panel.querySelector('.gloss-definition').innerHTML = definition;
        panel.querySelector('.gloss-close').addEventListener('click', closeGloss);

        if (isContiguous) {
            layout.querySelector('.reading-passage').append(panel);
            const buttonRect = button.getBoundingClientRect();
            const readingRect = layout.querySelector('.reading-passage').getBoundingClientRect();
            panel.style.left = `${Math.max(0, Math.min(buttonRect.left - readingRect.left, readingRect.width - panel.offsetWidth))}px`;
            panel.style.top = `${buttonRect.bottom - readingRect.top + 8}px`;
        } else {
            margin.replaceChildren(panel);
        }

        button.setAttribute('aria-expanded', 'true');
        active = { button, panel, term };
        await recordEvent('gloss_open', term);
        panel.querySelector('.gloss-close').focus();
    };

    layout.querySelectorAll('.gloss-target').forEach((button) => {
        button.addEventListener('click', () => openGloss(button));
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && active) {
            const returnFocus = active.button;
            closeGloss().then(() => returnFocus.focus());
        }
    });

    const finishForm = document.querySelector('[data-confirm-reading-finished]');
    finishForm?.addEventListener('submit', async (event) => {
        event.preventDefault();
        if (!window.confirm('Continue to the quiz? You will not be able to return to the reading during this attempt.')) {
            return;
        }
        await closeGloss();
        finishForm.submit();
    });
})();
