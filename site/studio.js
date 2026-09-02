/* === studio.js · mixtape '85 === */
const API = '';
const PHASES = ['Brief','Lyrics Drafts','Lyrics Finalize','Vocal Recordings','Instrumental','Cover Art','Mixdown','Mastering','Distribution'];

/* helpers */
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

async function api(path, opts={}) {
  const r = await fetch(API + path, {headers:{'Accept':'application/json'}, ...opts});
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
    return `<div class="pipe-cell ${state}">
      <span class="pipe-cell-num">${String(num).padStart(2,'0')}</span>
      <span class="pipe-cell-name">${esc(name)}</span>
    </div>`;
  }).join('');
  $('#pipeline').innerHTML = cells;
  // Sidebar layer stat also reflects derived value
  $('#stat-layer').textContent = layer ? String(layer).padStart(2,'0') : '—';
  $('#stat-phase').textContent = layer ? (PHASES[layer-1] || `L${layer}`).toUpperCase() : '—';
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
    </div>`).join('');
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
      const [alb, trk, ast, evs, decs] = await Promise.all([
        api(`/api/albums/${encodeURIComponent(session.album_id)}`),
        api(`/api/albums/${encodeURIComponent(session.album_id)}/tracks`).catch(()=>({items:[]})),
        api(`/api/albums/${encodeURIComponent(session.album_id)}/assets`).catch(()=>({items:[]})),
        api(`/api/sessions/${encodeURIComponent(session.id)}/events?limit=100`).catch(()=>[]),
        api(`/api/sessions/${encodeURIComponent(session.id)}/decisions`).catch(()=>[]),
      ]);
      currentAlbum = alb.item || alb;
      tracks = trk.items || trk || [];
      assets = ast.items || ast || [];
      events = Array.isArray(evs) ? evs : (evs.items || []);
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

  refresh();
  liveInterval = setInterval(refresh, 15000);
  // Events need faster polling than the rest of the page (15s) —
  // the chat-log section is the live surface. 2s idle, scales down
  // when session is paused/done.
  eventsPollInterval = setInterval(pollEvents, 2000);
  window.addEventListener('focus', refresh);
});
