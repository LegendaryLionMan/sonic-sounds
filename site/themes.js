/* site/themes.js — Album-studio theme manager.
 *
 * - On DOMContentLoaded: read the saved theme from localStorage and apply
 *   it BEFORE the page paints (so there's no flash of default theme).
 * - Exposes a small global API (`window.Themes`) so the theme picker can
 *   list themes, apply a theme, and listen to changes.
 * - Switching a theme plays a 320ms transition on every colored property
 *   so the change feels like a paint roll, not a snap.
 *
 * Pair with site/themes.css which defines the 6 themes.
 */
(function () {
  'use strict';

  const LS_KEY = 'sonic-studio:theme:v1';
  const FALLBACK = 'mixtape85';

  // Canonical list of themes. Same shape as palettes.json minus the hex
  // values, so we can render the picker without a second fetch.
  const THEMES = [
    {
      id: 'mixtape85',
      name: "Mixtape '85",
      desc: 'Warm yellow + cyan on near-black. The sonic-studio default.',
      isMain: true,
      swatches: ['#f0c53c', '#2dd8f0', '#fafafa'],
      swatchBg: '#0a0a0f'
    },
    {
      id: 'tokyo-night',
      name: 'Tokyo Night',
      desc: 'Calm nocturnal deep-blue. Soft pastel.',
      swatches: ['#7aa2f7', '#bb9af7', '#1a1b26'],
      swatchBg: '#1a1b26'
    },
    {
      id: 'catppuccin-latte',
      name: 'Catppuccin Latte',
      desc: 'Warm pastel light. Daytime, reading-friendly.',
      swatches: ['#1e66f5', '#8839ef', '#fe640b'],
      swatchBg: '#eff1f5'
    },
    {
      id: 'gruvbox-dark',
      name: 'Gruvbox',
      desc: 'Warm retro amber on warm-black. Den-studio vibes.',
      swatches: ['#fabd2f', '#83a598', '#fb4934'],
      swatchBg: '#282828'
    },
    {
      id: 'everforest',
      name: 'Everforest',
      desc: 'Forest greens + cream. Acoustic, organic, outdoors.',
      swatches: ['#7fbbb3', '#a7c080', '#d699b6'],
      swatchBg: '#2d353b'
    },
    {
      id: 'kanagawa',
      name: 'Kanagawa',
      desc: 'Sumi-e ink + wave blue. Zen, ink-on-paper.',
      swatches: ['#7fb4ca', '#b6927b', '#d27e99'],
      swatchBg: '#1f1f28'
    }
  ];

  const byId = Object.fromEntries(THEMES.map(t => [t.id, t]));

  // ----- Storage -----
  function load() {
    try {
      const raw = localStorage.getItem(LS_KEY);
      if (!raw) return FALLBACK;
      const v = JSON.parse(raw);
      if (v && v.theme && byId[v.theme]) return v.theme;
    } catch (e) { /* corrupt; fall through */ }
    return FALLBACK;
  }
  function save(theme) {
    try {
      localStorage.setItem(LS_KEY, JSON.stringify({
        v: 1,
        theme,
        appliedAt: Date.now()
      }));
    } catch (e) { /* private mode — ignore */ }
  }

  // ----- Apply -----
  function apply(themeId, withTransition) {
    const t = byId[themeId] ? themeId : FALLBACK;
    const root = document.documentElement;
    if (withTransition) {
      root.classList.add('theme-transitioning');
      // Auto-remove the transition class once the animation finishes so
      // future hovers/draws don't get a 320ms tail.
      setTimeout(() => root.classList.remove('theme-transitioning'), 380);
    }
    root.dataset.theme = t;
    root.style.colorScheme = (t === 'catppuccin-latte') ? 'light' : 'dark';
    try {
      // Update meta theme-color so phone browser chrome matches.
      let meta = document.querySelector('meta[name="theme-color"]');
      if (!meta) {
        meta = document.createElement('meta');
        meta.name = 'theme-color';
        document.head.appendChild(meta);
      }
      meta.content = getComputedStyle(root).getPropertyValue('--bg').trim() || '#0a0a0f';
    } catch (e) { /* ignore */ }
    // Broadcast
    window.dispatchEvent(new CustomEvent('theme:change', { detail: { theme: t } }));
    return t;
  }

  function set(themeId) {
    const t = apply(themeId, true);
    save(t);
    // Update any active picker's selected marker
    document.querySelectorAll('[data-theme-picker]').forEach(picker => {
      picker.dataset.theme = t;
      const rows = picker.querySelectorAll('.theme-picker-row');
      rows.forEach(row => {
        row.setAttribute('aria-selected', row.dataset.themeId === t ? 'true' : 'false');
      });
      const btn = picker.querySelector('.theme-picker-btn .tp-name');
      if (btn) btn.textContent = byId[t].name;
      const dot = picker.querySelector('.theme-picker-btn .tp-dot');
      if (dot) dot.style.background = byId[t].swatches[0];
    });
    return t;
  }

  function current() {
    return document.documentElement.dataset.theme || FALLBACK;
  }

  function list() {
    return THEMES.slice();
  }

  // ----- Mount theme pickers in the topbar -----
  function mountPicker(hostEl, opts) {
    opts = opts || {};
    hostEl.classList.add('theme-picker');
    hostEl.setAttribute('data-theme-picker', '');
    const t = current();
    hostEl.dataset.theme = t;
    const theme = byId[t];

    hostEl.innerHTML = `
      <button class="theme-picker-btn" type="button" aria-haspopup="listbox" aria-expanded="false">
        <span class="tp-dot" style="background:${theme.swatches[0]}"></span>
        <span class="tp-name">${esc(theme.name)}</span>
        <span style="opacity:.6">▾</span>
      </button>
      <div class="theme-picker-menu" role="listbox">
        <div class="theme-picker-head">theme</div>
        ${THEMES.map(th => `
          <div class="theme-picker-row" role="option" data-theme-id="${th.id}"
               aria-selected="${th.id === t ? 'true' : 'false'}">
            <span class="tpr-marker"></span>
            <span>
              <div class="tpr-name">${esc(th.name)}${th.isMain ? ' <span style="font-size:9px;color:var(--ink-muted);letter-spacing:.14em">· MAIN</span>' : ''}</div>
              <div class="tpr-desc">${esc(th.desc)}</div>
            </span>
            <span class="tpr-swatches">
              ${th.swatches.map(sw => `<span class="tpr-swatch" style="background:${sw}"></span>`).join('')}
            </span>
          </div>`).join('')}
      </div>
    `;

    const btn = hostEl.querySelector('.theme-picker-btn');
    const menu = hostEl.querySelector('.theme-picker-menu');
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const isOpen = hostEl.classList.toggle('is-open');
      btn.setAttribute('aria-expanded', String(isOpen));
    });
    hostEl.querySelectorAll('.theme-picker-row').forEach(row => {
      row.addEventListener('click', (e) => {
        e.stopPropagation();
        set(row.dataset.themeId);
        hostEl.classList.remove('is-open');
        btn.setAttribute('aria-expanded', 'false');
      });
    });
    // Close on outside click
    document.addEventListener('click', () => {
      hostEl.classList.remove('is-open');
      btn.setAttribute('aria-expanded', 'false');
    });
    // Keyboard
    btn.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') { hostEl.classList.remove('is-open'); btn.setAttribute('aria-expanded', 'false'); }
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        const isOpen = hostEl.classList.toggle('is-open');
        btn.setAttribute('aria-expanded', String(isOpen));
      }
    });
    hostEl.addEventListener('keydown', (e) => {
      const rows = Array.from(hostEl.querySelectorAll('.theme-picker-row'));
      const i = rows.findIndex(r => r === document.activeElement);
      if (e.key === 'ArrowDown') { e.preventDefault(); rows[(i + 1 + rows.length) % rows.length].focus(); }
      if (e.key === 'ArrowUp')   { e.preventDefault(); rows[(i - 1 + rows.length) % rows.length].focus(); }
      if (e.key === 'Enter' && document.activeElement.classList.contains('theme-picker-row')) {
        e.preventDefault();
        set(document.activeElement.dataset.themeId);
        hostEl.classList.remove('is-open');
        btn.setAttribute('aria-expanded', 'false');
      }
    });
    // Make rows focusable
    hostEl.querySelectorAll('.theme-picker-row').forEach(r => r.tabIndex = 0);
  }

  function esc(s) {
    return String(s).replace(/[<>&"]/g, c => ({ '<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;' }[c]));
  }

  // ----- Bootstrap -----
  // Apply synchronously to avoid flash. We read from localStorage NOW
  // (before <body> paints) and write to data-theme.
  let savedTheme = FALLBACK;
  try { savedTheme = load(); } catch (e) { savedTheme = FALLBACK; }
  document.documentElement.dataset.theme = savedTheme;
  if (savedTheme === 'catppuccin-latte') {
    document.documentElement.style.colorScheme = 'light';
  }

  // Expose API
  window.Themes = {
    list, current, set, apply, mountPicker, save, load,
    THEMES,
    /** Initialize after DOMContentLoaded. Mounts any picker with [data-theme-mount]. */
    init() {
      // Wire any auto-mounted picker slots
      document.querySelectorAll('[data-theme-mount]').forEach(el => mountPicker(el));
    }
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', window.Themes.init);
  } else {
    window.Themes.init();
  }
})();
