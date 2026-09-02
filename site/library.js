/* library.js · album-studio · Day 10
 * Fetches /api/albums + /api/health and renders the cassette wall.
 * Server-rendered HTML provides the shell; this script populates
 * the .shell-grid with cards per album.
 */
(function() {
  const $ = (s) => document.querySelector(s);
  const esc = (s) => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const fmtMs = (ms) => {
    if (ms == null) return '—';
    const m = Math.floor(ms / 60000), sec = Math.floor((ms % 60000) / 1000);
    return m + ':' + String(sec).padStart(2, '0');
  };

  async function api(path, opts) {
    const r = await fetch(path, opts);
    if (!r.ok) throw new Error(r.status + ' ' + await r.text());
    return r.json();
  }

  async function render() {
    let albums = [];
    try {
      const r = await api('/api/albums');
      albums = (r && r.items) || r || [];
    } catch (e) {
      console.warn('albums fetch failed', e);
    }
    const grid = document.querySelector('.shell-grid');
    if (!grid) return;
    if (!albums.length) {
      grid.innerHTML = '<p class="hand empty-line">No albums yet — open <a href="/site/intake.html">intake</a> to start one.</p>';
      return;
    }
    // Render one card per album
    grid.innerHTML = albums.map(a => {
      const status = (a.status || 'active').toLowerCase();
      return `<article class="card shell">
        <p class="eyebrow">${esc(status.toUpperCase())} · ${esc(a.runtime_min || 0)} MIN</p>
        <h3>${esc(a.title || a.id)}</h3>
        <p>Album id: <code>${esc(a.id)}</code></p>
        <p>Tracks: ${esc(a.track_count ?? '?')}</p>
        <a class="btn" href="/site/albums.html?album=${encodeURIComponent(a.id)}">▷ Open</a>
      </article>`;
    }).join('');
    // Update header count
    const eyebrow = document.querySelector('.shell-page .eyebrow');
    if (eyebrow) eyebrow.textContent = `/albums · ${albums.length}`;
  }

  document.addEventListener('DOMContentLoaded', render);
})();
