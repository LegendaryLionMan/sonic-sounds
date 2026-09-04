/* === albums.js · mixtape '85 === */
const API = '';
const PHASES = ['Brief','Lyrics Drafts','Lyrics Finalize','Vocal Recordings','Instrumental','Cover Art','Mixdown','Mastering','Distribution'];
const STATUS_ORDER = {draft:0,queued:1,active:2,paused:3,done:4};

/* ---- helpers ---- */
const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);
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
  const m = Math.floor(ms/60); const sec = ((ms%60)/1000)|0;
  return m + ':' + String(sec).padStart(2,'0');
}
function relativeTime(iso) {
  if (!iso) return '—';
  const diff = Date.now() - new Date(iso).getTime();
  const s = Math.floor(diff/1000);
  if (s < 60) return 'just now';
  if (s < 3600) return Math.floor(s/60) + 'm ago';
  if (s < 86400) return Math.floor(s/3600) + 'h ago';
  return Math.floor(s/86400) + 'd ago';
}
function badgeHtml(st) {
  const cls = {active:'badge-active',paused:'badge-active',queued:'badge-queued',done:'badge-done',draft:'badge-draft'}[st]||'badge-draft';
  return `<span class="badge ${cls}">${esc(st)}</span>`;
}

/* ---- state ---- */
let sessions = [];
let albums = [];
let liveInterval = null;

/* ---- render: page header stats ---- */
function renderStats() {
  const active = sessions.filter(s => s.status==='active').length;
  const done = albums.filter(a => a.status==='done').length;
  $('#stat-active').textContent = active;
  $('#stat-albums').textContent = albums.length;
  $('#stat-done').textContent = done;
  const txt = `${active} ACTIVE`;
  $('#status-text').textContent = txt;
  const pill = $('#status-pill');
  pill.className = 'pill ' + (active>0?'status-active':'status-done');
}

/* ---- render: active sessions grid ---- */
function renderSessions() {
  const grid = $('#session-grid');
  const active = sessions.filter(s => s.status==='active' || s.status==='paused');
  if (!active.length) { grid.innerHTML = '<div class="empty-card"><p class="hand">No active sessions. Open one from an album below.</p></div>'; return; }
  grid.innerHTML = active.map(s => {
    const ph = PHASES[s.current_layer-1] || `Layer ${s.current_layer}`;
    return `<div class="session-card" data-session="${esc(s.id)}">
      <div class="meta">
        <span class="layer">${esc(ph)} · ${s.session_phase?esc(s.session_phase):''}</span>
        <span class="album-title">${esc(s.album_title)}</span>
        <span class="artist">${esc(s.album_artist)}</span>
      </div>
      <div class="card-actions">
        ${s.status==='active'
          ?`<button class="btn btn-yellow" data-action="pause" data-id="${esc(s.id)}">⏸ Pause</button>`
          :`<button class="btn btn-cyan" data-action="resume" data-id="${esc(s.id)}">▶ Resume</button>`}
        ${s.status!=='done'
          ?`<button class="btn btn-red" data-action="complete" data-id="${esc(s.id)}">✓ Complete</button>`
          :''}
        <button class="btn btn-ghost" data-action="open-studio" data-id="${esc(s.id)}">Studio</button>
      </div>
    </div>`;
  }).join('');
}

/* ---- render: album library grid ---- */
function renderAlbums() {
  const grid = $('#album-grid');
  if (!albums.length) { grid.innerHTML = '<div class="empty-card"><p class="hand">No albums yet. The first one sets the tone.</p></div>'; return; }
  const sorted = [...albums].sort((a,b) => (STATUS_ORDER[b.status]??0) - (STATUS_ORDER[a.status]??0) || new Date(b.release_date||0) - new Date(a.release_date||0));
  grid.innerHTML = sorted.map(a => {
    const cover = (a.cover_asset_id || a.cover_image_asset_id)
      ? `<div class="album-cover"><img src="/api/albums/${encodeURIComponent(a.id)}/cover" alt="${esc(a.title)}" style="width:100%;aspect-ratio:1/1;object-fit:cover;border-radius:8px;display:block;" onerror="this.parentElement.innerHTML='<div class=\\'album-cover-placeholder\\' style=\\'display:flex;align-items:center;justify-content:center;font-family:var(--display);font-size:20px;color:var(--ink-muted);aspect-ratio:1/1;background:rgba(255,255,255,.04);border-radius:8px;\\'>${esc(a.title.charAt(0))}</div>'"></div>`
      : `<div class="album-cover" style="display:flex;align-items:center;justify-content:center;font-family:var(--display);font-size:20px;color:var(--ink-muted);">${a.title.charAt(0)}</div>`;
    return `<div class="album-card" data-id="${esc(a.id)}">
      <div class="album-header">${cover}
        <div class="album-title">${esc(a.title)}</div>
      </div>
      <div class="album-meta">
        <span>${esc(a.primary_artist_id)} · ${a.release_date||'—'}</span>
        ${a.runtime_min?`<span>${a.runtime_min} min</span>` : ''}
      </div>
      <div class="album-bottom">
        <span class="album-runtime">${a.runtime_min?a.runtime_min+' min':'—'}</span>
        ${badgeHtml(a.status)}
      </div>
    </div>`;
  }).join('');
}

/* ---- footer meta ---- */
function renderFooterMeta() {
  const total = sessions.length;
  const phases = PHASES.length;
  $('#foot-meta-text').textContent = `${total} sessions tracked · ${phases} layers · mixtape '85`;
}

/* ---- render everything ---- */
function render() { renderStats(); renderSessions(); renderAlbums(); renderFooterMeta(); }

/* ---- live fetch ---- */
async function refresh() {
  try {
    const [ss, al] = await Promise.all([api('/api/sessions'), api('/api/albums')]);
    sessions = ss.items||ss;
    albums = al.items||al;
    render();
  } catch (e) {
    console.error('refresh failed', e);
  }
}

/* ---- actions ---- */
async function actionSession(aid, act) {
  const map = {pause:'/api/sessions/'+aid+'/pause', resume:'/api/sessions/'+aid+'/resume', complete:'/api/sessions/'+aid+'/complete'};
  if (!map[act]) return;
  try {
    await fetch(API+map[act],{method:'POST'});
    await refresh();
  } catch(e) { alert('Action failed: '+e.message); }
}
async function openStudio(sid) { window.open('/studio.html?session='+encodeURIComponent(sid),'_blank'); }

/* ---- create album modal ---- */
const modal = $('#new-album-modal');
$('#new-album-btn').addEventListener('click', () => { modal.hidden=false; $('#form-error').hidden=true; });
$('#modal-close-btn').addEventListener('click', closeModal);
$('#modal-cancel-btn').addEventListener('click', closeModal);
modal.addEventListener('click', (e) => { if (e.target===modal) closeModal(); });
$('#new-album-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const id = fd.get('id').trim().toLowerCase().replace(/\s+/g,'-');
  const payload = {id, title: fd.get('title')?.trim(), primary_artist_id: fd.get('primary_artist_id')?.trim()||'maren-sol', release_date: fd.get('release_date')?.trim()||null, runtime_min: parseInt(fd.get('runtime_min'))||40};
  $('#form-error').hidden=true;
  try {
    await api('/api/albums',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    closeModal(); e.target.reset(); await refresh();
  } catch(err) {
    const el = $('#form-error'); el.textContent=err.message; el.hidden=false;
  }
});
function closeModal() { modal.hidden=true; }

/* ---- wire page event delegation ---- */
document.addEventListener('click', async (e) => {
  const btn = e.target.closest('[data-action]');
  if (btn) { const act=btn.dataset.action, id=btn.dataset.id; if (act==='open-studio') openStudio(id); else actionSession(id,act); return; }
  const card = e.target.closest('.album-card');
  if (card && !e.target.closest('.btn')) { location.href = '/site/album.html?id=' + encodeURIComponent(card.dataset.id); }
});

/* ---- init ---- */
refresh();
liveInterval = setInterval(refresh, 30000);
// Re-fetch on focus
window.addEventListener('focus', refresh);
