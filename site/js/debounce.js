/* === sonic-studio · debounce.js === */
/* Per Phase 0.U of PLAN-2026-07-28-v3.2:
   debounceButton(el, fn, {timeout: 60000, idempotency: true}) handles:
   - 2xx → navigate/re-render
   - 4xx → toast with specifics
   - 5xx/network → "Couldn't reach daemon" + retry
   - 60s timeout → re-enable + "request timed out"
   - Idempotency-Key header for safe POST retries
*/
(function() {
  'use strict';

  /**
   * Wrap a button with intelligent state management.
   * @param {HTMLButtonElement} el - The button to wrap
   * @param {Function} fn - The async function to call on click. Should throw on error.
   * @param {Object} [opts] - Options
   * @param {number} [opts.timeout=60000] - Max time before state goes to timeout
   * @param {boolean} [opts.idempotency=true] - Send Idempotency-Key on POST
   * @param {string} [opts.confirmText] - Optional confirmation text
   * @returns {Function} - Cleanup function to remove the wrapper
   */
  function debounceButton(el, fn, opts) {
    opts = opts || {};
    var timeout = opts.timeout || 60000;
    var idempotency = opts.idempotency !== false;

    if (!el.dataset.origText) el.dataset.origText = el.textContent;

    function setState(state, text) {
      el.classList.remove('is-loading', 'is-success', 'is-error', 'is-timeout', 'is-disabled');
      if (state) el.classList.add('is-' + state);
      el.disabled = state === 'loading' || state === 'disabled';
      el.setAttribute('aria-busy', state === 'loading' ? 'true' : 'false');
      if (text) el.textContent = text;
    }

    function clearTimer() {
      if (timerId) { clearTimeout(timerId); timerId = null; }
    }

    function reset() {
      clearTimer();
      el.classList.remove('is-loading', 'is-success', 'is-error', 'is-timeout');
      el.disabled = false;
      el.textContent = el.dataset.origText;
      el.setAttribute('aria-busy', 'false');
    }

    function showToast(message, type) {
      var existing = document.querySelector('.toast');
      if (existing) existing.remove();
      var toast = document.createElement('div');
      toast.className = 'toast toast-' + type;
      toast.setAttribute('role', 'status');
      toast.setAttribute('aria-live', 'polite');
      toast.innerHTML = '<span class="toast-icon">'
        + (type === 'error' ? '✗' : type === 'timeout' ? '⏱' : '✓')
        + '</span><span class="toast-msg">' + message + '</span>'
        + '<button class="toast-action" onclick="this.parentNode.remove()">Dismiss</button>';
      document.body.appendChild(toast);
      setTimeout(function() { if (toast.parentNode) toast.remove(); }, 8000);
    }

    var timerId = null;

    async function handler() {
      if (el.disabled || el.classList.contains('is-loading')) return;

      if (opts.confirmText && !window.confirm(opts.confirmText)) return;

      var idemKey = idempotency ? crypto.randomUUID() : null;

      clearTimer();
      setState('loading', opts.loadingText || 'Working…');

      timerId = setTimeout(function() {
        if (el.classList.contains('is-loading')) {
          setState('timeout', 'Timed out — try again');
          showToast('Request timed out. Check your connection and try again.', 'timeout');
          setTimeout(reset, 2000);
        }
      }, timeout);

      try {
        var result = await fn({
          idempotencyKey: idemKey,
          signal: null
        });
        clearTimer();
        setState('success', opts.successText || 'Done');
        showToast(opts.successToast || 'Done.', 'success');
        setTimeout(reset, 1800);
        return result;
      } catch (err) {
        clearTimer();
        var status = err.status || (err.message && err.message.indexOf('fetch') >= 0 ? 0 : 500);
        if (status >= 400 && status < 500) {
          setState('error', opts.error4xxText || 'Try again');
          showToast(opts.error4xxToast || err.message || 'Request failed', 'error');
        } else {
          setState('error', opts.error5xxText || "Couldn't reach daemon");
          showToast(opts.error5xxToast || "Couldn't reach daemon (is it running?)", 'error');
        }
        setTimeout(reset, 3000);
        throw err;
      }
    }

    el.addEventListener('click', handler);

    return function cleanup() {
      el.removeEventListener('click', handler);
      clearTimer();
    };
  }

  // Auto-attach to any button with data-action set
  document.addEventListener('DOMContentLoaded', function() {
    var buttons = document.querySelectorAll('button[data-action]');
    buttons.forEach(function(btn) {
      if (btn.dataset.attached === 'true') return;
      btn.dataset.attached = 'true';
    });
  });

  window.debounceButton = debounceButton;
})();
