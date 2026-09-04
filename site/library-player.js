/* site/library-player.js — Day 2 Hour X: Top-level album player on library page.
 *
 * Wires the cassette-wall library view to actual playback for finished albums.
 * Fetches /api/albums → for the first album (no session needed), builds an
 * inline player with cover + tracklist + audio element + standard controls
 * (play/pause, seek, next/prev, volume). The point: a finished album is
 * playable without opening a build session.
 *
 * Audio src: /api/audio/<track-id> per track. Range requests supported
 * server-side. Playlist auto-advance on end-of-track.
 */
(function () {
  "use strict";

  const API = "";
  const $ = (s, root) => (root || document).querySelector(s);
  const $$ = (s, root) => Array.from((root || document).querySelectorAll(s));
  const esc = (s) => String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const fmtDur = (sec) => {
    if (sec == null) return "—";
    const m = Math.floor(sec / 60),
      s = Math.floor(sec % 60);
    return m + ":" + String(s).padStart(2, "0");
  };

  async function api(path, opts) {
    const r = await fetch(API + path, opts);
    if (!r.ok) throw new Error(r.status + " " + (await r.text()).slice(0, 80));
    return r.json();
  }

  /**
   * Build the player for one album.
   * Returns the player DOM element (caller is responsible for mounting).
   */
  async function buildPlayer(album) {
    let tracks = [];
    try {
      tracks = await api(`/api/albums/${encodeURIComponent(album.id)}/tracks`);
    } catch (e) {
      console.warn("library-player: tracks fetch failed", e);
      return null;
    }
    if (!tracks || tracks.length === 0) return null;

    const coverUrl = `/api/albums/${encodeURIComponent(album.id)}/cover`;
    const root = document.createElement("section");
    root.className = "lib-player";
    root.id = "library-player";
    root.setAttribute("aria-label", `Play ${album.title}`);
    root.innerHTML = `
      <div class="lib-player-head">
        <img class="lib-player-cover" src="${esc(coverUrl)}" alt="${esc(album.title)} cover" />
        <div class="lib-player-meta">
          <p class="lib-player-eyebrow">▶ now playing</p>
          <h3 class="lib-player-title">${esc(album.title)}</h3>
          <p class="lib-player-sub">${esc(album.id)} · ${esc(tracks.length)} tracks · ${esc(album.runtime_min || "?")} min</p>
        </div>
      </div>

      <ol class="lib-tracklist" role="listbox" aria-label="Tracks">
        ${tracks
          .map(
            (t, i) => `
          <li class="lib-track" data-track-i="${i}" role="option" tabindex="0">
            <span class="lib-track-num">${String(t.track_num ?? i + 1).padStart(2, "0")}</span>
            <button class="lib-track-play" aria-label="Play ${esc(t.title)}" data-i="${i}">▷</button>
            <span class="lib-track-title">${esc(t.title)}</span>
            <span class="lib-track-dur">${fmtDur(t.duration_sec)}</span>
          </li>`
          )
          .join("")}
      </ol>

      <div class="lib-controls">
        <audio id="lib-audio" preload="metadata"></audio>
        <div class="lib-progress">
          <span class="lib-time lib-time-cur">0:00</span>
          <input type="range" class="lib-seek" min="0" max="100" value="0" step="0.1" aria-label="Seek" />
          <span class="lib-time lib-time-tot">0:00</span>
        </div>
        <div class="lib-buttons">
          <button class="lib-btn lib-prev" aria-label="Previous">⏮</button>
          <button class="lib-btn lib-playpause" aria-label="Play/Pause">▷</button>
          <button class="lib-btn lib-next" aria-label="Next">⏭</button>
          <span class="lib-spacer"></span>
          <button class="lib-btn lib-vol-icon" aria-label="Mute">🔊</button>
          <input type="range" class="lib-vol" min="0" max="1" step="0.01" value="0.85" aria-label="Volume" />
        </div>
      </div>
    `;

    const audio = $(".lib-audio, #lib-audio", root);
    const playpauseBtn = $(".lib-playpause", root);
    const prevBtn = $(".lib-prev", root);
    const nextBtn = $(".lib-next", root);
    const volSlider = $(".lib-vol", root);
    const volIcon = $(".lib-vol-icon", root);
    const seek = $(".lib-seek", root);
    const timeCur = $(".lib-time-cur", root);
    const timeTot = $(".lib-time-tot", root);
    const items = $$(".lib-track", root);

    let currentIdx = 0;
    let savedVolume = 0.85;

    function setTrack(i) {
      if (i < 0) i = 0;
      if (i >= tracks.length) i = tracks.length - 1;
      currentIdx = i;
      const t = tracks[i];
      audio.src = `/api/audio/${encodeURIComponent(t.id)}`;
      // visually mark current row
      items.forEach((el, n) => el.classList.toggle("is-current", n === i));
      // surface title in the head area too
      const titleEl = $(".lib-player-title", root);
      const eyebrow = $(".lib-player-eyebrow", root);
      if (titleEl) titleEl.textContent = t.title;
      if (eyebrow) eyebrow.textContent = `▶ track ${i + 1} of ${tracks.length}`;
    }

    function play() {
      audio
        .play()
        .then(() => {
          playpauseBtn.textContent = "❚❚";
          playpauseBtn.setAttribute("aria-label", "Pause");
        })
        .catch((e) => {
          /* user gesture required, usually means they're not on the page yet */
          console.warn("play() rejected:", e);
        });
    }
    function pause() {
      audio.pause();
      playpauseBtn.textContent = "▷";
      playpauseBtn.setAttribute("aria-label", "Play");
    }

    function toggle() {
      if (audio.paused) play();
      else pause();
    }

    audio.addEventListener("loadedmetadata", () => {
      timeTot.textContent = fmtDur(audio.duration);
      seek.max = audio.duration || 100;
    });
    audio.addEventListener("timeupdate", () => {
      timeCur.textContent = fmtDur(audio.currentTime);
      seek.value = audio.currentTime;
    });
    audio.addEventListener("ended", () => {
      if (currentIdx < tracks.length - 1) {
        setTrack(currentIdx + 1);
        play();
      } else {
        pause();
      }
    });

    playpauseBtn.addEventListener("click", toggle);
    prevBtn.addEventListener("click", () => {
      if (audio.currentTime > 3 || currentIdx === 0) {
        audio.currentTime = 0;
      } else {
        setTrack(currentIdx - 1);
        play();
      }
    });
    nextBtn.addEventListener("click", () => {
      if (currentIdx < tracks.length - 1) {
        setTrack(currentIdx + 1);
        play();
      }
    });

    // Per-row play button OR click on row
    $$(".lib-track", root).forEach((row, n) => {
      const handler = () => {
        if (n === currentIdx && !audio.paused) {
          pause();
        } else {
          setTrack(n);
          play();
        }
      };
      row.addEventListener("click", handler);
      row.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          handler();
        }
      });
    });

    seek.addEventListener("input", () => {
      audio.currentTime = Number(seek.value);
    });
    volSlider.addEventListener("input", () => {
      audio.volume = Number(volSlider.value);
      savedVolume = audio.volume;
    });
    volIcon.addEventListener("click", () => {
      if (audio.volume > 0) {
        savedVolume = audio.volume;
        audio.volume = 0;
        volSlider.value = 0;
        volIcon.textContent = "🔇";
      } else {
        audio.volume = savedVolume || 0.85;
        volSlider.value = audio.volume;
        volIcon.textContent = "🔊";
      }
    });

    // Initial track loaded but not playing (user gesture required)
    setTrack(0);

    return root;
  }

  /**
   * Mount: find #library-player-mount in DOM, fetch albums, build player.
   */
  async function mount() {
    const slot = document.getElementById("library-player-mount");
    if (!slot) return;
    let albums = [];
    try {
      albums = await api("/api/albums");
    } catch (e) {
      console.warn("library-player: /api/albums failed", e);
      return;
    }
    if (!albums || !albums.length) {
      slot.innerHTML = '<p class="lib-player-empty hand">No albums to play yet — seed or build one first.</p>';
      return;
    }
    // For now: play the first album that has tracks. Future: pick by status.
    for (const album of albums) {
      const player = await buildPlayer(album);
      if (player) {
        slot.appendChild(player);
        return;
      }
    }
    slot.innerHTML = '<p class="lib-player-empty hand">No tracks in this album yet.</p>';
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
})();
