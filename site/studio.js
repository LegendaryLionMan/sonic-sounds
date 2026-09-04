/* === studio.js · mixtape '85 === */
const API = '';
const PHASES = ['Brief','Lyrics Drafts','Lyrics Finalize','Vocal Recordings','Instrumental','Cover Art','Mixdown','Mastering','Distribution'];

/* helpers */
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

async function api(path, opts={}) {
  // Always send Accept: application/json, and Content-Type when there's a body.
  const headers = {'Accept': 'application/json'};
  if (opts.body && !opts.headers) {
    headers['Content-Type'] = 'application/json';
  }
  const r = await fetch(API + path, {headers, ...opts});
  if (!r.ok) { const e = await r.text(); throw new Error(`${r.status}: ${e}`); }
  return r.json();
}

function fmtDuration(s) {
  if (s == null) return '—';
  const m = Math.floor(s/60); const sec = s%60;
  return m + ':' + String(sec).padStart(2,'0');
}
function fmtMs(ms) {
  if (ms == null) return '—';
  const m = Math.floor(ms/60000); const sec = ((ms%60000)/1000)|0;
  return m + ':' + String(sec).padStart(2,'0');
}
function relativeTime(iso) {
  if (!iso) return '—';
  const diff = Date.now() - new Date(iso).getTime();
  const s = Math.floor(diff/1000);
  if (s < 0) return 'just now';
  if (s < 60) return 'just now';
  if (s < 3600) return Math.floor(s/60) + 'm ago';
  if (s < 86400) return Math.floor(s/3600) + 'h ago';
  return Math.floor(s/86400) + 'd ago';
}
function isoShort(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '—';
  return d.toISOString().slice(0,16).replace('T',' ');
}

/* state */
let sessions = [];
let currentSessionId = null;
let currentAlbum = null;
let tracks = [];
let assets = [];
let events = [];
let decisions = [];
let liveInterval = null;
let eventsPollInterval = null;
let eventsCursorId = null;
// Day 7: per-layer job state for the [invoke] button pipeline UI.
// Keyed by layer number (1..9). Value: {job_id, status, output_path} or null.
let layerJobs = {};
// Pipeline-deps layer_id for each phase index 1..9. The studio pipeline
// shows 9 phases (per PHASES); map them to the canonical layer_ids.
const PHASE_TO_LAYER_ID = {
  1: '01_brief',
  2: '02_lyrics_drafts',
  3: '03_lyrics_finalize',
  4: '04_vocal_recordings',
  5: '05_instrumental',
  6: '06_cover_art',
  7: '07_cassette_sticker',
  8: '08_audio_mastering',
  9: '09_metadata_isrc',
};

/* toast */
let toastTimer = null;
function toast(msg, kind='') {
  const el = $('#toast');
  el.textContent = msg;
  el.className = 'toast ' + kind;
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.hidden = true; }, 3000);
}

/* session picker */
function renderPicker() {
  const sel = $('#session-picker');
  if (!sessions.length) {
    sel.innerHTML = '<option value="">— no sessions —</option>';
    return;
  }
  const opts = sessions.map(s => {
    // Prefer the human album title from the joined album fetch, falling
    // back to whatever the session payload exposes.
    const album = currentSessionId === s.id ? currentAlbum : null;
    const title = (album && album.title) || s.album_title || s.album_id || s.id;
    const phase = PHASES[(s.current_layer||1)-1] || `Layer ${s.current_layer}`;
    const sel_ = s.id === currentSessionId ? 'selected' : '';
    return `<option value="${esc(s.id)}" ${sel_}>${esc(title)} · ${esc(phase)} · ${esc(s.status)}</option>`;
  }).join('');
  sel.innerHTML = opts;
}

/* sidebar: header + lifecycle buttons + meta */
function renderSidebar() {
  const session = sessions.find(s => s.id === currentSessionId);
  if (!session) {
    $('#album-title').textContent = '—';
    $('#album-artist').textContent = 'No session selected';
    $('#stat-layer').textContent = '—';
    $('#stat-phase').textContent = '—';
    $('#stat-runtime').textContent = '—';
    $('#stat-idle').textContent = '—';
    $('#meta-session').textContent = '—';
    $('#meta-album-id').textContent = '—';
    $('#meta-opened').textContent = '—';
    $('#meta-updated').textContent = '—';
    $('#btn-pause').disabled = true;
    $('#btn-resume').disabled = true;
    $('#btn-complete').disabled = true;
    setStatusPill('—', '');
    return;
  }
  $('#album-title').textContent = (currentAlbum && currentAlbum.title)
                                    || session.album_title
                                    || session.primary_artist_id
                                    || session.album_id
                                    || session.id;
  $('#album-artist').textContent = (currentAlbum && currentAlbum.primary_artist_id)
                                    || session.album_artist
                                    || session.primary_artist_id
                                    || '';
  // layer/phase are owned by renderPipeline() (derived from build events)
  $('#stat-runtime').textContent = fmtMs(session.elapsed_ms || session.current_position_ms);
  $('#stat-idle').textContent = relativeTime(session.updated_at || session.last_activity || session.created_at);
  $('#meta-session').textContent = session.id;
  $('#meta-album-id').textContent = session.album_id || '—';
  $('#meta-opened').textContent = isoShort(session.opened_at || session.created_at);
  $('#meta-updated').textContent = isoShort(session.updated_at);

  // lifecycle buttons reflect status
  const st = session.status;
  $('#btn-pause').disabled = st !== 'active';
  $('#btn-resume').disabled = st !== 'paused';
  $('#btn-complete').disabled = st === 'done' || st === 'completed';
  setStatusPill(st, 'status-' + st);
}
function setStatusPill(text, cls) {
  const pill = $('#status-pill');
  pill.className = 'pill ' + cls;
  $('#status-text').textContent = text || 'no session';
}

/* pipeline */
function renderPipeline() {
  // Derive current_layer from the most recent build event's payload.
  // The session row doesn't store layer — layer is a property of the
  // build event stream. This means closing/reopening a session
  // preserves layer progress (it's in the events log, not on the row).
  let layer = 0;
  for (const e of events) {
    if (e.kind === "build" && e.payload && typeof e.payload.layer === "number") {
      layer = Math.max(layer, e.payload.layer);
    }
  }
  const cells = PHASES.map((name, i) => {
    const num = i + 1;
    let state = 'upcoming';
    if (layer && num < layer) state = 'done';
    else if (layer && num === layer) state = 'active';
    // Day 7: per-layer [invoke] button state. We can't store job state
    // in layerJobs forever (page reload loses it), but for a live
    // session it's good enough. Job status drives button label + class.
    const job = layerJobs[num];
    let btnCls = 'pipe-invoke';
    let btnLabel = 'invoke';
    let btnDisabled = '';
    if (job) {
      const s = job.status;
      if (s === 'todo' || s === 'needs_approval') {
        btnLabel = 'queued'; btnCls += ' running';
      } else if (s === 'running') {
        btnLabel = 'running…'; btnCls += ' running';
      } else if (s === 'done' || s === 'succeeded') {
        btnLabel = '✓ done'; btnCls += ' done';
        btnDisabled = 'disabled';
      } else if (s === 'failed' || s === 'crashed' || s === 'blocked') {
        btnLabel = 'retry'; btnCls += ' failed';
      }
    }
    return `<div class="pipe-cell ${state}" data-layer="${num}">
      <span class="pipe-cell-num">${String(num).padStart(2,'0')}</span>
      <span class="pipe-cell-name">${esc(name)}</span>
      <button class="${btnCls}" data-layer="${num}" ${btnDisabled}>${esc(btnLabel)}</button>
    </div>`;
  }).join('');
  $('#pipeline').innerHTML = cells;
  // Wire up click handlers for the [invoke] buttons (Day 7)
  // NOTE: our $ helper is querySelector (single Element). We need
  // querySelectorAll to get the NodeList of all buttons.
  document.querySelectorAll('#pipeline .pipe-invoke').forEach(btn => {
    btn.addEventListener('click', () => invokeLayer(parseInt(btn.dataset.layer, 10)));
  });
  // Sidebar layer stat also reflects derived value
  $('#stat-layer').textContent = layer ? String(layer).padStart(2,'0') : '—';
  $('#stat-phase').textContent = layer ? (PHASES[layer-1] || `L${layer}`).toUpperCase() : '—';
}

/* Day 7: invoke a single layer's build job via POST /api/build/invoke */
async function invokeLayer(layerNum) {
  if (!currentAlbum) {
    toast('no album selected', 'error');
    return;
  }
  const layer_id = PHASE_TO_LAYER_ID[layerNum];
  if (!layer_id) {
    toast(`unknown layer number ${layerNum}`, 'error');
    return;
  }
  // Optimistic update — mark as queued so the button disables immediately.
  layerJobs[layerNum] = { status: 'todo', job_id: null };
  renderPipeline();
  toast(`queueing layer ${String(layerNum).padStart(2,'0')}…`);
  try {
    const r = await api(`/api/build/invoke`, {
      method: 'POST',
      body: JSON.stringify({
        album_id: currentAlbum.id || currentAlbum.album_id,
        layer_id,
        synchronous: true,  // run inline; the daemon's mmx call is fast
      }),
    });
    // r is {job_id, status, output_path, ...} on success
    if (r && r.job_id) {
      layerJobs[layerNum] = {
        status: r.status || 'done',
        job_id: r.job_id,
        output_path: r.output_path,
      };
      if (r.status === 'done' || r.status === 'succeeded') {
        toast(`layer ${String(layerNum).padStart(2,'0')} ✓ done`);
      } else {
        toast(`layer ${String(layerNum).padStart(2,'0')} ${r.status}: ${r.error || 'see daemon log'}`, 'error');
      }
    } else {
      toast(`invoke failed: no job_id in response`, 'error');
    }
  } catch (e) {
    toast(`invoke failed: ${e.message}`, 'error');
    // Reset button to default state
    delete layerJobs[layerNum];
  }
  renderPipeline();
  // Refresh events to pick up any new build_* events written by the runner.
  // The runner also writes events with album_id but no session_id (global),
  // which the existing since_id poll won't pick up. Trigger a full refresh.
  refresh();
}

/* tracks */
function renderTracks() {
  const list = $('#track-list');
  if (!tracks.length) { list.innerHTML = '<p class="hand empty-line">No tracks yet.</p>'; return; }
  list.innerHTML = tracks.map((t,i) => `
    <div class="track-row">
      <span class="t-num">${String(i+1).padStart(2,'0')}</span>
      <span class="t-title">${esc(t.title||'(untitled)')}</span>
      <span class="t-meta">${(() => {
        // API returns duration_sec (per db/albums.py:tracks). Older
        // clients may expect duration_ms. Accept either; format as
        // m:ss either way.
        const secs = t.duration_sec ?? (t.duration_ms ? t.duration_ms / 1000 : null);
        return secs != null ? fmtDuration(secs) : '—';
      })()}</span>
      <button class="t-play" data-track-id="${esc(t.id)}" data-track-title="${esc(t.title||'')}">▷</button>
    </div>`).join('');
  // Day 10: wire audio player — click ▶ on a track to load + play it.
  // The /api/audio/<track_id> endpoint supports HTTP Range so the
  // <audio> element can scrub without re-downloading the file.
  // NOTE: $ = document.querySelector (single Element), so use
  // document.querySelectorAll for multi-element iteration.
  document.querySelectorAll('#track-list .t-play').forEach(btn => {
    btn.addEventListener('click', () => loadTrack(btn.dataset.trackId, btn.dataset.trackTitle));
  });
}

/* Day 10: load + play a track via the range-supported /api/audio endpoint. */
function loadTrack(trackId, title) {
  const player = $('#audio-player');
  const el = $('#audio-el');
  const meta = $('#audio-meta');
  if (!player || !el) return;
  el.src = `/api/audio/${encodeURIComponent(trackId)}`;
  meta.textContent = `▷ ${title || trackId}`;
  player.hidden = false;
  // Play programmatically after the metadata loads (Range request fires
  // on the first byte-range query when controls are visible).
  el.play().catch(() => { /* user gesture required for autoplay */ });
}

/* assets */
function renderAssets() {
  const list = $('#asset-list');
  if (!assets.length) { list.innerHTML = '<p class="hand empty-line">No assets yet.</p>'; return; }
  list.innerHTML = assets.map(a => `
    <div class="asset-row">
      <span class="a-kind">${esc(a.kind || a.asset_kind || '—')}</span>
      <span class="a-name">${esc(a.id)} ${a.filename?'· '+esc(a.filename):''}</span>
      <span class="a-time">${relativeTime(a.updated_at || a.created_at)}</span>
    </div>`).join('');
}

/* Day 11+: cover art — set the <img src> from /api/albums/<id>/cover.
   Falls back gracefully: if the endpoint 404s, the img src stays empty
   and the alt text "album cover" is shown. */
function renderCover() {
  const img = $('#album-cover');
  const meta = $('#cover-meta');
  if (!img) return;
  if (currentAlbum && currentAlbum.id) {
    const url = `/api/albums/${encodeURIComponent(currentAlbum.id)}/cover`;
    img.src = url;
    img.alt = `${currentAlbum.title || currentAlbum.id} — album cover`;
    if (meta) {
      const coverRel = currentAlbum.cover_path || '';
      const size = currentAlbum.runtime_min ? `${currentAlbum.runtime_min} MIN` : '';
      meta.textContent = `${currentAlbum.title || currentAlbum.id}  ·  ${size}`.trim();
      if (coverRel) meta.title = `cover_path: ${coverRel}`;
    }
  } else {
    img.removeAttribute('src');
    img.alt = 'album cover — no album selected';
    if (meta) meta.textContent = 'no album selected';
  }
}

/* events (chat log) */
function renderEvents() {
  const list = $('#event-list');
  if (!events.length) { list.innerHTML = '<p class="hand empty-line">No events yet.</p>'; return; }
  list.innerHTML = events.map(e => `
    <div class="event-row ${esc(e.role)}">
      <span class="e-role">${esc(e.role)}</span>
      <span class="e-kind">${esc(e.kind)}</span>
      <span class="e-content">${esc(e.content||'')}</span>
    </div>`).join('');
}

/* Poll for new events since last seen id. Fast (2s) while session active,
   slower (30s) otherwise. Updates the on-screen list in-place. */
async function pollEvents() {
  if (!currentSessionId) return;
  try {
    const url = eventsCursorId
      ? `/api/sessions/${encodeURIComponent(currentSessionId)}/events?since_id=${eventsCursorId}`
      : `/api/sessions/${encodeURIComponent(currentSessionId)}/events?limit=100`;
    const rows = await api(url);
    if (Array.isArray(rows) && rows.length > 0) {
      const existing = new Set(events.map(e => e.id));
      const newOnes = rows.filter(e => !existing.has(e.id));
      events = events.concat(newOnes);
      eventsCursorId = Math.max(eventsCursorId || 0, ...rows.map(e => e.id));
      renderEvents();
    } else if (rows.length === 0) {
      // first poll — set cursor
      eventsCursorId = Math.max(eventsCursorId || 0, ...(events.map(e => e.id)));
    }
  } catch (e) {
    // Polling errors are non-fatal; the next tick will retry.
    console.warn('event poll failed', e);
  }
}

/* decisions (locked choices) */
function renderDecisions() {
  const list = $('#decision-list');
  if (!decisions.length) { list.innerHTML = '<p class="hand empty-line">No decisions yet.</p>'; return; }
  list.innerHTML = decisions.map(d => {
    const tier = d.tier || 'recommended';
    const code = d.code || '';
    const question = d.question || '';
    const answer = d.answer || '(no answer)';
    const rationale = d.rationale ? `<p class="d-rationale">"${esc(d.rationale)}"</p>` : '';
    const meta = [];
    if (d.source_doc) meta.push(`<span>DOC: ${esc(d.source_doc)}</span>`);
    if (d.locked_at) meta.push(`<span>LOCKED ${esc(d.locked_at)}</span>`);
    const metaRow = meta.length ? `<div class="d-meta">${meta.join('')}</div>` : '';
    return `
    <div class="decision-card tier-${esc(tier)}">
      <div class="d-head">
        <span class="d-code">${esc(code)}</span>
        <span class="d-tier tier-badge-${esc(tier)}">${esc(tier)}</span>
      </div>
      ${question ? `<p class="d-question">${esc(question)}</p>` : ''}
      <p class="d-answer">${esc(answer)}</p>
      ${rationale}
      ${metaRow}
    </div>`;
  }).join('');
}

/* footer */
function renderFooter() {
  $('#foot-meta-text').textContent = `${sessions.length} session${sessions.length===1?'':'s'} · 9 layers · mixtape '85`;
}

/* lifecycle actions */
async function action(act) {
  if (!currentSessionId) return;
  try {
    await api(`/api/sessions/${currentSessionId}/${act}`, {method:'POST'});
    toast(`${act} OK`, 'ok');
    await refresh();
  } catch (e) {
    toast(`${act} failed: ${e.message}`, 'error');
  }
}

/* live fetch */
async function refresh() {
  try {
    const ss = await api('/api/sessions');
    sessions = ss.items || ss;
  } catch (e) {
    toast('sessions fetch failed: '+e.message, 'error');
    sessions = [];
  }
  // ensure currentSessionId still valid, otherwise pick first
  if (!sessions.find(s => s.id === currentSessionId)) {
    currentSessionId = sessions[0]?.id || null;
  }
  // fetch drilldowns for the selected session's album
  currentAlbum = null; tracks = []; assets = []; events = []; decisions = []; eventsCursorId = null;
  const session = sessions.find(s => s.id === currentSessionId);
  if (session && session.album_id) {
    try {
      const [alb, trk, ast, sessionEvs, albumEvs, decs] = await Promise.all([
        api(`/api/albums/${encodeURIComponent(session.album_id)}`),
        api(`/api/albums/${encodeURIComponent(session.album_id)}/tracks`).catch(()=>({items:[]})),
        api(`/api/albums/${encodeURIComponent(session.album_id)}/assets`).catch(()=>({items:[]})),
        api(`/api/sessions/${encodeURIComponent(session.id)}/events?limit=100`).catch(()=>[]),
        // Album-scoped events include GLOBAL build events (Day 6/7 runner
        // writes events with session_id=NULL but album_id=session.album_id).
        api(`/api/events?album=${encodeURIComponent(session.album_id)}&limit=200`).catch(()=>[]),
        api(`/api/sessions/${encodeURIComponent(session.id)}/decisions`).catch(()=>[]),
      ]);
      currentAlbum = alb.item || alb;
      tracks = trk.items || trk || [];
      assets = ast.items || ast || [];
      // Merge session-scoped + album-scoped events. The album query
      // is a superset (includes session events too, since they share
      // album_id). Use album-scoped as the canonical source.
      events = Array.isArray(albumEvs) ? albumEvs : (albumEvs.items || []);
      decisions = Array.isArray(decs) ? decs : (decs.items || []);
      // Initialize the event cursor at the highest id seen — subsequent
      // pollEvents() calls will fetch only rows with id > eventsCursorId.
      eventsCursorId = events.reduce((mx, e) => Math.max(mx, e.id || 0), 0);
    } catch (e) {
      // album-level errors are non-fatal — keep the session card visible
      console.warn('album drilldown failed', e);
    }
  }
  renderPicker();
  renderSidebar();
  renderCover();           // Day 11+: album cover art from /api/albums/:id/cover
  renderPipeline();
  renderTracks();
  renderAssets();
  renderEvents();
  renderDecisions();
  renderFooter();
}

/* wire */
document.addEventListener('DOMContentLoaded', () => {
  // URL ?session=ID preselects
  const params = new URLSearchParams(location.search);
  currentSessionId = params.get('session');

  $('#session-picker').addEventListener('change', (e) => {
    currentSessionId = e.target.value || null;
    refresh();
  });
  $('#btn-pause').addEventListener('click', () => action('pause'));
  $('#btn-resume').addEventListener('click', () => action('resume'));
  $('#btn-complete').addEventListener('click', () => action('complete'));
  $('#back-btn').addEventListener('click', () => { location.href = '/site/albums.html'; });
  // Day 13: ❓ Help button — re-trigger the interactive user guide
  $('#help-btn').addEventListener('click', () => {
    window.dispatchEvent(new Event('studio:show-guide'));
  });

  refresh();
  liveInterval = setInterval(refresh, 15000);
  // Events need faster polling than the rest of the page (15s) —
  // the chat-log section is the live surface. 2s idle, scales down
  // when session is paused/done.
  eventsPollInterval = setInterval(pollEvents, 2000);
  window.addEventListener('focus', refresh);
});

/* Day 1 Hour 11: scroll-progress updater.
 * Sets --scroll-progress on :root based on window.scrollY,
 * threshold 200px. CSS uses this var to compress the topbar.
 * (Loaded after studio.js's main IIFE.) */
(function() {
  var ticking = false;
  function update() {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(function() {
      var y = window.scrollY || 0;
      var progress = Math.max(0, Math.min(1, (y - 200) / 200));
      document.documentElement.style.setProperty('--scroll-progress', progress.toFixed(3));
      // Also toggle .is-scrolled for the @supports fallback
      if (y > 200) {
        document.body.classList.add('is-scrolled');
      } else {
        document.body.classList.remove('is-scrolled');
      }
      ticking = false;
    });
  }
  window.addEventListener('scroll', update, { passive: true });
  update();  // initial state
})();
