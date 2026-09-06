/* library.js · sonic-sounds · Day 10
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
      // Cover art: live <img> from /api/albums/:id/cover so the OneDrive
      // canonical path resolves. Per 2026-09-06 user feedback: when an
      // album has no cover, the endpoint returns a 1x1 transparent PNG.
      // We render a CSS placeholder tile instead so the album card
      // doesn't explode to 1377x1377 (the aspect-ratio:1/1 with width:100%
      // + a 1x1 natural source fills the whole card). The placeholder uses
      // the theme's --bg-elevated token + the album's first letter.
      const hasCover = !!a.cover_path;
      const coverAlt = `${a.title || a.id} — album cover`;
      const coverBlock = hasCover
        ? `<img src="${esc(`/api/albums/${encodeURIComponent(a.id)}/cover`)}" alt="${esc(coverAlt)}"
             style="width:100%; aspect-ratio:1/1; object-fit:cover; border-radius:8px; display:block;"
             loading="lazy"
             onerror="this.style.display='none'" />`
        : `<div class="cover-placeholder" aria-label="${esc(coverAlt)}"
               style="width:100%; aspect-ratio:1/1; display:flex; align-items:center;
                      justify-content:center; border-radius:8px; background:var(--bg-elevated, #1a1a22);
                      font-family:var(--display, sans-serif); font-size:5rem; color:var(--accent,#f0c53c);
                      letter-spacing:.04em;">${esc((a.title || a.id).slice(0, 2).toUpperCase())}</div>`;
      return `<article class="card shell">
        ${coverBlock}
        <p class="eyebrow">${esc(status.toUpperCase())} · ${esc(a.runtime_min || 0)} MIN · ${esc(a.track_count ?? '?')} TRACKS</p>
        <h3>${esc(a.title || a.id)}</h3>
        <p>Album id: <code>${esc(a.id)}</code></p>
        <a class="btn" href="/site/albums.html?album=${encodeURIComponent(a.id)}">▷ Open</a>
      </article>`;
    }).join('');
    // Update header count
    const eyebrow = document.querySelector('.shell-page .eyebrow');
    if (eyebrow) eyebrow.textContent = `/albums · ${albums.length}`;

    // Hour 2: magnetic hover tilt on cassette cards. Cursor position
    // drives --tilt-x / --tilt-y CSS vars, the transform in CSS reads
    // them via perspective + rotateX/Y. Subtle (max 6°) so it feels
    // alive, not nauseating.
    document.querySelectorAll('.card.shell').forEach(card => {
      card.addEventListener('mousemove', (e) => {
        const rect = card.getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width;   // 0..1
        const y = (e.clientY - rect.top) / rect.height;
        const tiltX = (x - 0.5) * 6;                     // -3..3 deg
        const tiltY = (0.5 - y) * 6;                     // -3..3 deg
        card.style.setProperty('--tilt-x', tiltX + 'deg');
        card.style.setProperty('--tilt-y', tiltY + 'deg');
      });
      card.addEventListener('mouseleave', () => {
        card.style.setProperty('--tilt-x', '0deg');
        card.style.setProperty('--tilt-y', '0deg');
      });
    });
  }

  document.addEventListener('DOMContentLoaded', render);
})();
