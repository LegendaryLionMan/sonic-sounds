/* site/header-player.js — Persistent header music player.
 *
 * Behavior:
 *  - Auto-mounts on every page (script tag at end of body)
 *  - On load: fetches /api/albums → picks the first one with tracks → renders the player
 *  - Reads last-played state from localStorage (track id, currentTime, isPlaying, volume)
 *  - If user was playing, resumes the same track at the same position
 *  - Click cassette art / play button / track title → expand to tracklist
 *  - All audio events save state to localStorage so navigating pages keeps the place
 *
 * Theme: Mixtape '85 dark. Cassette reels spin while playing (CSS keyframes).
 */
(function () {
  'use strict';

  const API = '';
  const LS_KEY = 'album-studio:header-player:v1';
  const $ = (s) => document.querySelector(s);

  function esc(s) { return String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }
  function fmt(sec) {
    if (!sec && sec !== 0) return '0:00';
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m}:${String(s).padStart(2, '0')}`;
  }

  // ---- State ----
  let state = {
    albumId: null,
    tracks: [],     // [{id, title, duration_sec, mood, mp3_path}]
    album: null,    // {id, title, primary_artist_id, cover_path, ...}
    currentIdx: -1,
    isPlaying: false,
    currentTime: 0,
    duration: 0,
    volume: 0.7,
  };

  function loadLS() {
    try {
      const raw = localStorage.getItem(LS_KEY);
      if (raw) {
        const saved = JSON.parse(raw);
        if (saved && typeof saved === 'object') {
          state.currentTime = saved.currentTime || 0;
          state.volume = saved.volume != null ? saved.volume : 0.7;
          state.albumId = saved.albumId || null;
          state.currentIdx = saved.currentIdx != null ? saved.currentIdx : -1;
        }
      }
    } catch (e) { /* ignore */ }
  }

  function saveLS() {
    try {
      localStorage.setItem(LS_KEY, JSON.stringify({
        albumId: state.albumId,
        currentIdx: state.currentIdx,
        currentTime: state.currentTime,
        volume: state.volume,
        isPlaying: state.isPlaying,
        ts: Date.now(),
      }));
    } catch (e) { /* ignore */ }
  }

  // ---- Mount the markup ----
  function mount() {
    document.body.classList.add('has-header-player');
    const root = document.createElement('div');
    root.className = 'header-player';
    root.innerHTML = `
      <div class="hp-cassette">
        <div class="hp-cassette-art">
          <img class="hp-cover-img" src="" alt="" hidden>
          <div class="hp-reels">
            <div class="hp-reel"></div>
            <div class="hp-reel"></div>
          </div>
        </div>
        <div class="hp-meta">
          <p class="hp-meta-eyebrow">/cassette · no album loaded</p>
          <h3 class="hp-meta-title">—</h3>
          <p class="hp-meta-sub">—</p>
        </div>
      </div>

      <div class="hp-transport">
        <button class="hp-btn hp-btn-skip" data-action="prev" aria-label="Previous">⏮</button>
        <button class="hp-btn hp-btn-play" data-action="play" aria-label="Play/Pause">▷</button>
        <button class="hp-btn hp-btn-skip" data-action="next" aria-label="Next">⏭</button>
        <div class="hp-progress">
          <span class="hp-time" data-role="cur">0:00</span>
          <div class="hp-seek" data-role="seek"><div class="hp-seek-fill"></div></div>
          <span class="hp-time" data-role="dur">0:00</span>
        </div>
      </div>

      <div class="hp-right">
        <div class="hp-vol-wrap">
          <span style="font-size:14px">🔊</span>
          <input type="range" class="hp-vol" min="0" max="1" step="0.01" value="0.7">
        </div>
        <button class="hp-list-btn" data-action="toggle-list">▤ tracks</button>
      </div>

      <div class="hp-tracklist-panel">
        <div class="hp-tracklist-head">
          <h4 data-role="album-title">—</h4>
          <span data-role="track-count">0 tracks</span>
        </div>
        <ol class="hp-tracklist" data-role="tracklist" style="list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:2px;"></ol>
      </div>
    `;
    document.body.appendChild(root);

    // Audio element (hidden — controlled by player)
    const audio = document.createElement('audio');
    audio.id = 'hp-audio';
    audio.preload = 'metadata';
    audio.volume = state.volume;
    audio.hidden = true;
    document.body.appendChild(audio);

    wire(root, audio);
    state.root = root;
    state.audio = audio;
  }

  // ---- Wire interactions ----
  function wire(root, audio) {
    // Transport buttons
    root.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-action]');
      if (!btn) return;
      const act = btn.dataset.action;
      if (act === 'play') togglePlay();
      else if (act === 'prev') skip(-1);
      else if (act === 'next') skip(+1);
      else if (act === 'toggle-list') root.classList.toggle('is-open');
    });

    // Seek bar
    const seek = root.querySelector('[data-role="seek"]');
    seek.addEventListener('click', (e) => {
      if (!state.duration) return;
      const r = seek.getBoundingClientRect();
      const ratio = (e.clientX - r.left) / r.width;
      const t = ratio * state.duration;
      audio.currentTime = t;
      state.currentTime = t;
      paint();
      saveLS();
    });

    // Volume
    const vol = root.querySelector('.hp-vol');
    vol.value = state.volume;
    vol.addEventListener('input', () => {
      state.volume = parseFloat(vol.value);
      audio.volume = state.volume;
      saveLS();
    });

    // Audio events
    audio.addEventListener('timeupdate', () => {
      state.currentTime = audio.currentTime;
      paint();
      // Save every 2s so a page reload can resume
      if (Math.floor(audio.currentTime) % 2 === 0) saveLS();
    });
    audio.addEventListener('loadedmetadata', () => {
      state.duration = audio.duration || 0;
      paint();
    });
    audio.addEventListener('play', () => {
      state.isPlaying = true;
      root.classList.add('is-playing');
      paint();
      saveLS();
    });
    audio.addEventListener('pause', () => {
      state.isPlaying = false;
      root.classList.remove('is-playing');
      paint();
      saveLS();
    });
    audio.addEventListener('ended', () => {
      skip(+1, true);
    });
    audio.addEventListener('error', () => {
      console.warn('[header-player] audio error', audio.error);
      state.isPlaying = false;
      root.classList.remove('is-playing');
      paint();
    });
  }

  // ---- Actions ----
  function togglePlay() {
    if (state.currentIdx < 0) {
      // Start from first track
      if (state.tracks.length) loadTrack(0, true);
      return;
    }
    if (state.audio.paused) state.audio.play().catch((e) => console.warn('[header-player] play failed:', e));
    else state.audio.pause();
  }

  function skip(delta, autoAdvance = false) {
    if (!state.tracks.length) return;
    let next = state.currentIdx + delta;
    if (next < 0) next = 0;
    if (next >= state.tracks.length) next = state.tracks.length - 1;
    loadTrack(next, true);
  }

  function loadTrack(idx, autoplay) {
    if (idx < 0 || idx >= state.tracks.length) return;
    const t = state.tracks[idx];
    state.currentIdx = idx;
    state.currentTime = 0;
    state.audio.src = `/api/audio/${encodeURIComponent(t.id)}`;
    state.audio.load();
    paint();
    if (autoplay) state.audio.play().catch(() => {});
    saveLS();
  }

  function jumpToTrack(idx) {
    loadTrack(idx, true);
    // Close panel on mobile
    if (window.matchMedia('(max-width: 720px)').matches) state.root.classList.remove('is-open');
  }

  // ---- Painting ----
  function paint() {
    const root = state.root;
    if (!root) return;
    const audio = state.audio;
    const cur = state.currentIdx >= 0 ? state.tracks[state.currentIdx] : null;
    const dur = state.duration || (cur ? (cur.duration_sec || 0) : 0);
    const t = state.currentTime || 0;

    // Eyebrow / title / sub
    const eyebrow = root.querySelector('.hp-meta-eyebrow');
    const title = root.querySelector('.hp-meta-title');
    const sub = root.querySelector('.hp-meta-sub');
    if (state.album) {
      eyebrow.textContent = `/cassette · ${esc(state.album.title)}`;
    }
    if (cur) {
      title.textContent = cur.title;
      const trackNum = String(idx0(cur.track_num, state.currentIdx + 1)).padStart(2, '0');
      const total = state.tracks.length;
      sub.textContent = `track ${trackNum} / ${total} · ${state.album ? state.album.primary_artist_id : ''}`;
    } else if (state.tracks.length) {
      title.textContent = state.album ? state.album.title : '—';
      sub.textContent = `${state.tracks.length} tracks`;
    } else {
      title.textContent = state.album ? state.album.title : '—';
      sub.textContent = 'no tracks loaded';
    }

    // Cover
    const img = root.querySelector('.hp-cover-img');
    if (state.album && state.album.cover_path) {
      img.src = `/api/albums/${encodeURIComponent(state.album.id)}/cover`;
      img.alt = state.album.title;
      img.hidden = false;
    } else {
      img.hidden = true;
    }

    // Play/pause icon
    const playBtn = root.querySelector('.hp-btn-play');
    playBtn.textContent = audio && !audio.paused ? '⏸' : '▷';

    // Time + seek
    root.querySelector('[data-role="cur"]').textContent = fmt(t);
    root.querySelector('[data-role="dur"]').textContent = fmt(dur);
    const pct = dur > 0 ? Math.min(100, (t / dur) * 100) : 0;
    root.querySelector('.hp-seek-fill').style.width = pct + '%';

    // Tracklist
    const tl = root.querySelector('[data-role="tracklist"]');
    const titleEl = root.querySelector('[data-role="album-title"]');
    const countEl = root.querySelector('[data-role="track-count"]');
    if (state.album) titleEl.textContent = state.album.title;
    countEl.textContent = `${state.tracks.length} tracks`;
    if (state.tracks.length) {
      tl.innerHTML = state.tracks.map((t, i) => `
        <li class="hp-track-item ${i === state.currentIdx ? 'is-current' : ''}" data-track-idx="${i}">
          <span class="hp-track-num">${String(idx0(t.track_num, i + 1)).padStart(2, '0')}</span>
          <span class="hp-track-title">${esc(t.title)}</span>
          <span class="hp-track-dur">${fmt(t.duration_sec)}</span>
          <button class="hp-track-play" aria-label="Play ${esc(t.title)}">${i === state.currentIdx && !audio.paused ? '⏸' : '▷'}</button>
        </li>`).join('');
    } else {
      tl.innerHTML = `<li class="hp-empty" style="padding:14px;text-align:center;">no tracks yet</li>`;
    }
  }

  function idx0(a, b) { return a != null ? a : b; }

  // ---- Bootstrap ----
  async function init() {
    loadLS();
    mount();

    try {
      // Fetch albums list
      const r = await fetch(API + '/api/albums');
      if (!r.ok) throw new Error(`/api/albums → ${r.status}`);
      const albums = await r.json();
      // Pick first album with tracks
      let chosen = null;
      for (const a of albums) {
        try {
          const tr = await fetch(`${API}/api/albums/${encodeURIComponent(a.id)}/tracks`);
          if (tr.ok) {
            const tracks = await tr.json();
            if (tracks && tracks.length) { chosen = { album: a, tracks }; break; }
          }
        } catch (e) { /* skip */ }
      }
      if (!chosen) {
        state.album = albums[0] || null;
        state.tracks = [];
      } else {
        state.album = chosen.album;
        state.tracks = chosen.tracks;
      }

      paint();

      // Restore previous track + position if same album
      if (state.album && state.albumId === state.album.id && state.currentIdx >= 0 && state.currentIdx < state.tracks.length) {
        const t = state.tracks[state.currentIdx];
        state.audio.src = `/api/audio/${encodeURIComponent(t.id)}`;
        state.audio.volume = state.volume;
        state.audio.addEventListener('loadedmetadata', () => {
          try { state.audio.currentTime = Math.min(state.currentTime, state.audio.duration || state.currentTime); } catch (e) {}
          paint();
          if (state.isPlaying) {
            state.audio.play().catch((e) => {
              console.warn('[header-player] autoplay blocked, click play to start', e);
              paint();
            });
          }
        }, { once: true });
      }
    } catch (e) {
      console.warn('[header-player] failed to load albums:', e);
      paint();
    }

    // Wire tracklist clicks (delegated)
    state.root.addEventListener('click', (e) => {
      const item = e.target.closest('.hp-track-item');
      if (!item) return;
      const idx = parseInt(item.dataset.trackIdx, 10);
      if (!isNaN(idx)) jumpToTrack(idx);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
