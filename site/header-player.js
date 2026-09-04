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
    muted: false,         // mute via speaker-icon click — preserves slider position
    volumeBeforeMute: 0.7,
    repeat: 'off',        // 'off' | 'all' | 'one' — repeat entire album or current track
    shuffle: false,       // shuffle playlist order
  };

  function loadLS() {
    try {
      const raw = localStorage.getItem(LS_KEY);
      if (raw) {
        const saved = JSON.parse(raw);
        if (saved && typeof saved === 'object') {
          state.currentTime = saved.currentTime || 0;
          state.volume = saved.volume != null ? saved.volume : 0.7;
          state.volumeBeforeMute = saved.volumeBeforeMute != null ? saved.volumeBeforeMute : state.volume;
          state.muted = !!saved.muted;
          state.albumId = saved.albumId || null;
          state.currentIdx = saved.currentIdx != null ? saved.currentIdx : -1;
          state.repeat = (saved.repeat === 'all' || saved.repeat === 'one') ? saved.repeat : 'off';
          state.shuffle = !!saved.shuffle;
          state.sleepAt = saved.sleepAt || null;
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
        volumeBeforeMute: state.volumeBeforeMute,
        muted: state.muted,
        repeat: state.repeat,
        shuffle: state.shuffle,
        sleepAt: state.sleepAt,
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
        <div class="hp-cassette-art"></div>
        <div class="hp-meta">
          <p class="hp-meta-eyebrow">/cassette · no album loaded</p>
          <h3 class="hp-meta-title">—</h3>
          <p class="hp-meta-sub">—</p>
        </div>
      </div>

      <div class="hp-transport">
        <button class="hp-btn hp-btn-mode" data-action="shuffle" aria-label="Shuffle" title="Shuffle">🔀</button>
        <button class="hp-btn hp-btn-seeksec" data-action="seek-back" aria-label="Back 15 seconds" title="−15 seconds">⟲</button>
        <button class="hp-btn hp-btn-skip" data-action="prev" aria-label="Previous track">⏮</button>
        <button class="hp-btn hp-btn-play" data-action="play" aria-label="Play / Pause">▷</button>
        <button class="hp-btn hp-btn-skip" data-action="next" aria-label="Next track">⏭</button>
        <button class="hp-btn hp-btn-seeksec" data-action="seek-fwd" aria-label="Forward 15 seconds" title="+15 seconds">⟳</button>
        <button class="hp-btn hp-btn-mode" data-action="repeat" aria-label="Repeat" title="Repeat: off">↻</button>
      </div>

      <div class="hp-progress">
        <span class="hp-time" data-role="cur">0:00</span>
        <div class="hp-seek" data-role="seek">
          <div class="hp-seek-fill"></div>
          <div class="hp-seek-hover" data-role="seek-hover"></div>
          <div class="hp-seek-tooltip" data-role="seek-tooltip">0:00</div>
        </div>
        <span class="hp-time" data-role="dur">0:00</span>
      </div>

      <div class="hp-right">
        <div class="hp-vol-wrap">
          <button class="hp-btn-mute" data-action="mute" aria-label="Mute" title="Mute / Unmute" type="button">🔊</button>
          <input type="range" class="hp-vol" min="0" max="1" step="0.01" value="0.7">
        </div>
        <button class="hp-btn-mini" data-action="sleep" aria-label="Sleep timer" title="Sleep timer (off)">⏱</button>
        <button class="hp-btn-mini" data-action="lyrics" aria-label="Lyrics" title="Lyrics">♪</button>
        <button class="hp-list-btn" data-action="toggle-list">▤ tracks</button>
      </div>

      <div class="hp-lyrics-panel" role="dialog" aria-label="Lyrics">
        <div class="hp-lyrics-head">
          <span data-role="lyrics-track-name">—</span>
          <button class="hp-btn-mini" data-action="close-lyrics" aria-label="Close lyrics" title="Close lyrics">✕</button>
        </div>
        <div class="hp-lyrics-body" data-role="lyrics-body">
          <p class="hp-lyrics-empty">Lyrics aren't transcribed yet.<br><span class="hand">They'll appear here when available.</span></p>
        </div>
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
      else if (act === 'mute') toggleMute();
      else if (act === 'repeat') cycleRepeat();
      else if (act === 'shuffle') toggleShuffle();
      else if (act === 'seek-back') skipSec(-15);
      else if (act === 'seek-fwd') skipSec(+15);
      else if (act === 'sleep') cycleSleep();
      else if (act === 'lyrics') root.classList.toggle('lyrics-open');
      else if (act === 'close-lyrics') root.classList.remove('lyrics-open');
    });

    // Seek bar — click to seek, hover shows preview tooltip + vertical
    // indicator line at the hover position (YouTube/Spotify pattern).
    const seek = root.querySelector('[data-role="seek"]');
    const seekHover = root.querySelector('[data-role="seek-hover"]');
    const seekTooltip = root.querySelector('[data-role="seek-tooltip"]');
    function hideHover() {
      if (seekHover) seekHover.style.width = '0%';
      if (seekTooltip) { seekTooltip.style.opacity = '0'; seekTooltip.style.left = '0'; }
    }
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
    seek.addEventListener('mousemove', (e) => {
      if (!state.duration) return;
      const r = seek.getBoundingClientRect();
      const ratio = Math.max(0, Math.min(1, (e.clientX - r.left) / r.width));
      const t = ratio * state.duration;
      const pct = (ratio * 100).toFixed(2) + '%';
      if (seekHover) seekHover.style.width = pct;
      if (seekTooltip) {
        seekTooltip.textContent = fmt(t);
        seekTooltip.style.left = pct;
        seekTooltip.style.opacity = '1';
      }
    });
    seek.addEventListener('mouseleave', hideHover);
    // Touch support: also update on touchmove
    seek.addEventListener('touchmove', (e) => {
      if (!state.duration || !e.touches[0]) return;
      const r = seek.getBoundingClientRect();
      const ratio = Math.max(0, Math.min(1, (e.touches[0].clientX - r.left) / r.width));
      const t = ratio * state.duration;
      const pct = (ratio * 100).toFixed(2) + '%';
      if (seekHover) seekHover.style.width = pct;
      if (seekTooltip) {
        seekTooltip.textContent = fmt(t);
        seekTooltip.style.left = pct;
        seekTooltip.style.opacity = '1';
      }
    }, { passive: true });
    seek.addEventListener('touchend', hideHover);

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
      // Sleep timer: if the deadline has passed, pause playback.
      // We use audio.currentTime % 1 to throttle — check at most ~once a second.
      if (state.sleepAt && Date.now() >= state.sleepAt) {
        state.sleepAt = null;
        try { audio.pause(); } catch (e) {}
        saveLS();
      }
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
      // Repeat-one: replay the same track from 0 (single-track loop).
      if (state.repeat === 'one') {
        const t = state.tracks[state.currentIdx];
        if (t) {
          state.currentTime = 0;
          state.audio.src = `/api/audio/${encodeURIComponent(t.id)}`;
          state.audio.load();
          state.audio.play().catch(() => {});
          paint();
        }
        return;
      }
      // Repeat-all: roll over to track 0 when last track ends.
      if (state.repeat === 'all' && state.tracks.length) {
        loadTrack(0, true);
        return;
      }
      // Default (repeat off): stop at end of album, otherwise auto-advance.
      const isLastTrack = state.currentIdx >= state.tracks.length - 1;
      if (isLastTrack) {
        state.isPlaying = false;
        state.currentTime = state.audio.currentTime || 0;
        saveLS();
        paint();
        return;
      }
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

  // Click the speaker icon: mute (preserves slider position) or unmute back
  // to the volume the user had before they muted. The slider still moves
  // live with the audio when dragged — but a click on the icon is the
  // toggle.
  function toggleMute() {
    // state.audio is set in mount(); use it instead of a closure variable
    if (state.muted) {
      // Unmute: restore the previous volume (or a sensible default)
      const v = state.volumeBeforeMute > 0.05 ? state.volumeBeforeMute : 0.7;
      state.volume = v;
      state.muted = false;
      state.audio.volume = v;
      const slider = state.root.querySelector('.hp-vol');
      if (slider) slider.value = v;
    } else {
      // Mute: remember current volume, set to 0
      if (state.volume > 0.05) state.volumeBeforeMute = state.volume;
      state.volume = 0;
      state.muted = true;
      state.audio.volume = 0;
      const slider = state.root.querySelector('.hp-vol');
      if (slider) slider.value = 0;
    }
    paint();
    saveLS();
  }

  // Cycle repeat modes: off → all → one → off
  function cycleRepeat() {
    const order = ['off', 'all', 'one'];
    const idx = order.indexOf(state.repeat);
    state.repeat = order[(idx + 1) % order.length];
    paint();
    saveLS();
  }

  function toggleShuffle() {
    state.shuffle = !state.shuffle;
    paint();
    saveLS();
  }

  // Skip forward / backward by N seconds while a track is playing.
  // Clamps to [0, duration] so we don't seek past the end or before 0.
  function skipSec(sec) {
    if (!state.duration) return;
    let t = state.currentTime + sec;
    if (t < 0) t = 0;
    if (t > state.duration) t = state.duration;
    state.audio.currentTime = t;
    state.currentTime = t;
    paint();
    saveLS();
  }

  // Sleep timer: cycles through off → 15m → 30m → 60m → off.
  // When set, stores an epoch-ms deadline; a 1s poll in timeupdate will
  // auto-pause when the deadline passes.
  function cycleSleep() {
    const now = Date.now();
    // Duration to next deadline per state (in minutes)
    const next = ({ null: 15, 15: 30, 30: 60, 60: null }); // null = off
    const minutes = next[minutesFromSleep()];
    if (minutes == null) {
      state.sleepAt = null;
    } else {
      state.sleepAt = now + minutes * 60 * 1000;
    }
    paint();
    saveLS();
  }
  function minutesFromSleep() {
    if (state.sleepAt == null) return null;
    const ms = state.sleepAt - Date.now();
    if (ms <= 0) return null;
    if (ms <= 15 * 60 * 1000) return 15;
    if (ms <= 30 * 60 * 1000) return 30;
    return 60;
  }
  function fmtSleepRemaining() {
    if (state.sleepAt == null) return null;
    const ms = state.sleepAt - Date.now();
    if (ms <= 0) return 'done';
    const m = Math.floor(ms / 60000);
    const s = Math.floor((ms % 60000) / 1000);
    return `${m}m ${s}s`;
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

    // Cover — we now use the cassette sticker image as a fixed artwork;
    // a cover image slot can be re-added in the future when an album-specific
    // cassette sticker exists. For now the artwork is always cassette-yellow-tape.
    const img = root.querySelector('.hp-cover-img');
    if (img) {
      img.removeAttribute('src');
      img.hidden = true;
    }

    // Play/pause icon
    const playBtn = root.querySelector('.hp-btn-play');
    playBtn.textContent = audio && !audio.paused ? '⏸' : '▷';

    // Mute speaker icon — flips between 🔊 and 🔇, plus a class for CSS
    const muteBtn = root.querySelector('.hp-btn-mute');
    if (muteBtn) {
      muteBtn.textContent = state.muted ? '🔇' : '🔊';
      muteBtn.classList.toggle('is-muted', !!state.muted);
      muteBtn.setAttribute('aria-label', state.muted ? 'Unmute' : 'Mute');
    }

    // Repeat button — three states with distinct visual + ARIA
    const repeatBtn = root.querySelector('.hp-btn-mode[data-action="repeat"]');
    if (repeatBtn) {
      const labels = { off: 'Repeat: off', all: 'Repeat: album', one: 'Repeat: one' };
      const icons  = { off: '↻', all: '🔁', one: '🔂' };
      repeatBtn.textContent = icons[state.repeat] || '↻';
      repeatBtn.title = labels[state.repeat] || 'Repeat';
      repeatBtn.setAttribute('aria-label', labels[state.repeat] || 'Repeat');
      repeatBtn.classList.toggle('is-active', state.repeat !== 'off');
      repeatBtn.dataset.mode = state.repeat;
    }

    // Shuffle button — toggle with visual active state
    const shuffleBtn = root.querySelector('.hp-btn-mode[data-action="shuffle"]');
    if (shuffleBtn) {
      shuffleBtn.classList.toggle('is-active', !!state.shuffle);
      shuffleBtn.title = state.shuffle ? 'Shuffle: on' : 'Shuffle: off';
      shuffleBtn.setAttribute('aria-label', shuffleBtn.title);
    }

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

    // (Removed: now-playing pip + cassette glow. The cassette image should
    // just show the artwork cleanly, no overlays.)

    // Sleep timer button label. Reverted to the static ⏱ icon
    // (don't swap to a number when active — feels visually inconsistent).
    // The .is-active class + the title attribute carry the state.
    const sleepBtn = root.querySelector('.hp-btn-mini[data-action="sleep"]');
    if (sleepBtn) {
      const mins = minutesFromSleep();
      sleepBtn.classList.toggle('is-active', !!mins);
      const label = mins ? `Sleep timer: ${mins} min remaining` : 'Sleep timer (off)';
      sleepBtn.title = label;
      sleepBtn.setAttribute('aria-label', label);
      sleepBtn.textContent = '⏱';
    }

    // Lyrics track name in the panel
    const lyricName = root.querySelector('[data-role="lyrics-track-name"]');
    if (lyricName) {
      const cur = state.currentIdx >= 0 ? state.tracks[state.currentIdx] : null;
      lyricName.textContent = cur ? cur.title : '— no track —';
    }
  }

  // ---- Keyboard shortcuts ----
  // Space=play/pause, ←/→=prev/next, ↑/↓=volume, M=mute, R=repeat,
  // S=shuffle, comma/period=±15s skip, L=lyrics, T=tracks panel
  function onKeydown(e) {
    const t = e.target;
    // Don't intercept typing in inputs
    if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
    const k = e.key.toLowerCase();
    if (k === ' ') { e.preventDefault(); togglePlay(); }
    else if (k === 'm') toggleMute();
    else if (k === 'r') cycleRepeat();
    else if (k === 's') toggleShuffle();
    else if (k === 'l') {
      if (state.root) state.root.classList.toggle('lyrics-open');
    }
    else if (k === 't') {
      if (state.root) state.root.classList.toggle('is-open');
    }
    else if (k === ',') skipSec(-15);
    else if (k === '.') skipSec(+15);
    else if (e.key === 'ArrowLeft') skip(-1);
    else if (e.key === 'ArrowRight') skip(+1);
    else if (e.key === 'ArrowUp') {
      e.preventDefault();
      const v = Math.min(1, parseFloat(state.root.querySelector('.hp-vol').value) + 0.05);
      state.root.querySelector('.hp-vol').value = v;
      state.root.querySelector('.hp-vol').dispatchEvent(new Event('input'));
    }
    else if (e.key === 'ArrowDown') {
      e.preventDefault();
      const v = Math.max(0, parseFloat(state.root.querySelector('.hp-vol').value) - 0.05);
      state.root.querySelector('.hp-vol').value = v;
      state.root.querySelector('.hp-vol').dispatchEvent(new Event('input'));
    }
  }
  document.addEventListener('keydown', onKeydown);

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

    // Wire tracklist clicks (delegated).
    // Two click semantics:
    //   • Click on the .hp-track-play button → toggle play/pause for THIS track
    //     (if it's the current track, this pauses; if it's a different track,
    //     this jumps to it and starts playing).
    //   • Click anywhere else on the .hp-track-item row → jump to that track.
    // Without this split, a click on the pause button of the CURRENT track
    // would also fire the row handler and reload the track from 0 (restart).
    state.root.addEventListener('click', (e) => {
      // Play-button click: handle play/pause toggle
      const playBtn = e.target.closest('.hp-track-play');
      if (playBtn) {
        e.stopPropagation();
        const item = playBtn.closest('.hp-track-item');
        if (!item) return;
        const idx = parseInt(item.dataset.trackIdx, 10);
        if (isNaN(idx)) return;
        if (idx === state.currentIdx) {
          togglePlay(); // current track → pause/resume (preserve position)
        } else {
          jumpToTrack(idx); // different track → load and play from start
        }
        return;
      }
      // Row click anywhere else → jump to that track
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
