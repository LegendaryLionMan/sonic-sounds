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
let liveInterval = null;

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
    const title = s.album_title || s.album_id || s.id;
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
  $('#album-title').textContent = session.album_title || session.album_id || session.id;
  $('#album-artist').textContent = session.album_artist || session.primary_artist_id || '';
  const layer = session.current_layer || 1;
  $('#stat-layer').textContent = String(layer).padStart(2,'0');
  $('#stat-phase').textContent = (PHASES[layer-1] || `L${layer}`).toUpperCase();
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
  const session = sessions.find(s => s.id === currentSessionId);
  const layer = session ? (session.current_layer || 1) : 0;
  const cells = PHASES.map((name, i) => {
    const num = i + 1;
    let state = 'upcoming';
    if (session && num < layer) state = 'done';
    else if (session && num === layer) state = 'active';
    return `<div class="pipe-cell ${state}">
      <span class="pipe-cell-num">${String(num).padStart(2,'0')}</span>
      <span class="pipe-cell-name">${esc(name)}</span>
    </div>`;
  }).join('');
  $('#pipeline').innerHTML = cells;
}

/* tracks */
function renderTracks() {
  const list = $('#track-list');
  if (!tracks.length) { list.innerHTML = '<p class="hand empty-line">No tracks yet.</p>'; return; }
  list.innerHTML = tracks.map((t,i) => `
    <div class="track-row">
      <span class="t-num">${String(i+1).padStart(2,'0')}</span>
      <span class="t-title">${esc(t.title||'(untitled)')}</span>
      <span class="t-meta">${t.duration_ms ? fmtDuration(t.duration_ms/1000) : '—'}</span>
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
  currentAlbum = null; tracks = []; assets = [];
  const session = sessions.find(s => s.id === currentSessionId);
  if (session && session.album_id) {
    try {
      const [alb, trk, ast] = await Promise.all([
        api(`/api/albums/${encodeURIComponent(session.album_id)}`),
        api(`/api/albums/${encodeURIComponent(session.album_id)}/tracks`).catch(()=>({items:[]})),
        api(`/api/albums/${encodeURIComponent(session.album_id)}/assets`).catch(()=>({items:[]})),
      ]);
      currentAlbum = alb.item || alb;
      tracks = trk.items || trk || [];
      assets = ast.items || ast || [];
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
  window.addEventListener('focus', refresh);
});
