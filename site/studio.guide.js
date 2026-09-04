/* site/studio.guide.js - Day 13: Interactive user guide overlay.
 *
 * Opt-in per-session tutorial that walks new users through 4 core
 * actions. Triggered by:
 *   - URL ?guide=on
 *   - Clicking the ❓ Help button in the footer (footer.js)
 *   - localStorage not having 'guide-seen' set
 *
 * The guide remembers dismissal per-session via localStorage so it
 * doesn't auto-popup every visit. Users can re-enable it via the
 * footer help button.
 *
 * Pattern: matches the "click-follow" tutorial in games. The overlay
 * highlights the next action, waits for the user to do it, then
 * advances to the next step.
 */
(function() {
  const STEPS = [
    {
      id: 'invoke-brief',
      title: 'Run your first pipeline layer',
      body: 'The pipeline at the bottom of the studio has 9 layers. Click [INVOKE] on layer 01 (Brief) to run it. Watch the events panel — build_started + build_succeeded will appear.',
      target: '.pipe-invoke[data-layer="1"]',
      advance: 'btn-invoke-1',
      requires: 'a layer-1 invoke to flip to done',
    },
    {
      id: 'play-track',
      title: 'Play a track',
      body: 'Click the [▷] button next to track 01 (Dusk Index, 3:24). The MP3 streams from OneDrive via HTTP Range.',
      target: '.t-play[data-track-id="half-light-hours:01"]',
      advance: 'btn-1',
      requires: 'audio element to have a src',
    },
    {
      id: 'pause-session',
      title: 'Pause your session',
      body: 'Click [⏸ PAUSE] in the sidebar. The session status will flip to "paused" and the resume button will become enabled.',
      target: '#btn-pause',
      advance: 'btn-pause',
      requires: 'session status === "paused"',
    },
    {
      id: 'lock-decision',
      title: 'Lock a concept decision',
      body: 'Use the API to lock an M-tier decision (try: curl -X POST http://127.0.0.1:8765/api/decisions -d \'{"code":"M01","tier":"mandatory","answer":"<your answer>","album_id":"half-light-hours","session_id":"<your session>"}\' -H "Content-Type: application/json"). The decisions panel will populate.',
      target: '#decision-list',
      advance: null,
      requires: 'at least one decision card visible',
    },
  ];

  // ------------------------------------------------------------------
  // State
  // ------------------------------------------------------------------

  let currentStep = 0;
  let overlayEl = null;
  let activeHighlight = null;

  const SEEN_KEY = 'studio-guide-seen';

  function isEnabled() {
    const params = new URLSearchParams(location.search);
    if (params.get('guide') === 'on') return true;
    if (params.get('guide') === 'off') return false;
    // Default: enable if not seen this session
    return !localStorage.getItem(SEEN_KEY);
  }

  // ------------------------------------------------------------------
  // DOM construction
  // ------------------------------------------------------------------

  function buildOverlay() {
    const overlay = document.createElement('div');
    overlay.id = 'guide-overlay';
    overlay.style.cssText = `
      position: fixed; bottom: 24px; right: 24px; z-index: 10000;
      width: 360px; padding: 20px 24px;
      background: hsl(220 14% 11%); border: 1px solid hsl(45 90% 60%);
      border-radius: 12px; color: hsl(36 30% 97%);
      font-family: var(--sans, system-ui); box-shadow: 0 8px 32px rgba(0,0,0,.5);
      transition: all .3s ease;
    `;
    overlay.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
        <span style="font-family:var(--mono);font-size:10px;letter-spacing:.16em;color:hsl(45 90% 60%);text-transform:uppercase;">user guide · step <span id="guide-step-num"></span>/4</span>
        <button id="guide-close" style="background:none;border:none;color:hsl(220 10% 60%);cursor:pointer;font-size:18px;padding:0;line-height:1;">×</button>
      </div>
      <h3 id="guide-title" style="margin:0 0 8px 0;font-family:var(--display);font-size:18px;color:hsl(45 90% 60%);line-height:1.2;"></h3>
      <p id="guide-body" style="margin:0;font-size:13px;line-height:1.5;color:hsl(36 30% 97%);"></p>
      <div style="margin-top:16px;display:flex;gap:8px;justify-content:flex-end;">
        <button id="guide-skip" style="padding:6px 12px;background:transparent;border:1px solid hsl(220 10% 30%);color:hsl(220 10% 60%);border-radius:6px;cursor:pointer;font-family:var(--sans);font-size:12px;">Skip tutorial</button>
        <button id="guide-next" style="padding:6px 14px;background:hsl(45 90% 60%);border:none;color:hsl(220 14% 11%);border-radius:6px;cursor:pointer;font-family:var(--sans);font-size:12px;font-weight:600;">Next →</button>
      </div>
    `;
    document.body.appendChild(overlay);
    return overlay;
  }

  function highlight(target) {
    if (activeHighlight) {
      activeHighlight.classList.remove('guide-highlight');
      activeHighlight.style.boxShadow = '';
    }
    if (!target) return;
    const el = document.querySelector(target);
    if (!el) return;
    el.style.transition = 'box-shadow .3s ease';
    el.style.boxShadow = '0 0 0 4px hsl(45 90% 60%), 0 0 32px hsl(45 90% 60% / 0.5)';
    el.classList.add('guide-highlight');
    activeHighlight = el;
    // Scroll into view if needed
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  function renderStep() {
    if (currentStep >= STEPS.length) {
      dismiss();
      return;
    }
    const step = STEPS[currentStep];
    document.getElementById('guide-step-num').textContent = currentStep + 1;
    document.getElementById('guide-title').textContent = step.title;
    document.getElementById('guide-body').textContent = step.body;
    highlight(step.target);
    document.getElementById('guide-next').textContent = step.advance ? 'Mark done →' : 'Finish ✓';
  }

  function dismiss() {
    if (overlayEl) overlayEl.remove();
    if (activeHighlight) {
      activeHighlight.classList.remove('guide-highlight');
      activeHighlight.style.boxShadow = '';
    }
    localStorage.setItem(SEEN_KEY, '1');
  }

  function checkAdvance() {
    const step = STEPS[currentStep];
    if (!step) return;
    if (step.requires === 'a layer-1 invoke to flip to done') {
      const btn = document.querySelector('.pipe-invoke[data-layer="1"]');
      if (btn && btn.textContent.toLowerCase().includes('done')) {
        currentStep++;
        renderStep();
      }
    } else if (step.requires === 'audio element to have a src') {
      const el = document.getElementById('audio-el');
      if (el && el.src && el.src.includes('audio')) {
        currentStep++;
        renderStep();
      }
    } else if (step.requires === 'session status === "paused"') {
      const status = document.getElementById('status-text')?.textContent;
      if (status === 'paused') {
        currentStep++;
        renderStep();
      }
    } else if (step.requires === 'at least one decision card visible') {
      const cards = document.querySelectorAll('.decision-card');
      if (cards.length > 0) {
        currentStep++;
        renderStep();
      }
    }
  }

  // ------------------------------------------------------------------
  // Lifecycle
  // ------------------------------------------------------------------

  function start() {
    if (!isEnabled()) return;
    // Don't start if the overlay's already on screen
    if (document.getElementById('guide-overlay')) return;
    overlayEl = buildOverlay();
    currentStep = 0;
    renderStep();

    document.getElementById('guide-close').addEventListener('click', dismiss);
    document.getElementById('guide-skip').addEventListener('click', dismiss);
    document.getElementById('guide-next').addEventListener('click', () => {
      currentStep++;
      renderStep();
    });

    // Watch for step advancement conditions (poll every 500ms)
    setInterval(checkAdvance, 500);
  }

  // Re-trigger from the footer help button
  window.addEventListener('studio:show-guide', () => {
    localStorage.removeItem(SEEN_KEY);
    if (overlayEl) overlayEl.remove();
    start();
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    // The studio.js may have already initialized; defer to next tick
    setTimeout(start, 200);
  }
})();
