/* site/themes.js · Theme switcher for album-studio (Omarchy-inspired).
 *
 * Renders a small floating swatch dock in the bottom-left corner of
 * every page. Each swatch shows the theme's gradient preview; click
 * to switch. The choice persists in localStorage so it survives
 * reloads.
 *
 * Available themes are defined in site/themes.css (CSS variables).
 *
 * Day 1 backlog (completed):
 *   - Filter input with substring match (Omarchy v4.0 carousel pattern)
 *   - Theme accent color picker (overrides --accent-2 with a swatch grid)
 *   - Per-theme font-family (overrides --display / --mono / --sans)
 */
(function() {
  const THEMES = [
    {
      id: "mixtape85",
      label: "Mixtape '85",
      font: { display: "'Bebas Neue', sans-serif", mono: "'JetBrains Mono', monospace", sans: "'Inter', sans-serif" },
    },
    {
      id: "tokyonight",
      label: "Tokyo Night",
      font: { display: "'Inter', sans-serif", mono: "'JetBrains Mono', monospace", sans: "'Inter', sans-serif" },
    },
    {
      id: "catppuccin",
      label: "Catppuccin",
      font: { display: "'Inter', sans-serif", mono: "'JetBrains Mono', monospace", sans: "'Inter', sans-serif" },
    },
    {
      id: "gruvbox",
      label: "Gruvbox",
      font: { display: "'Bebas Neue', sans-serif", mono: "'JetBrains Mono', monospace", sans: "'Inter', sans-serif" },
    },
  ];
  // 8 curated accent colors. User's choice is layered on top of the
  // theme's base palette — so Mixtape '85 + violet still has the
  // cassette yellow vibe, just with violet accents.
  const ACCENTS = [
    { id: "amber",  label: "Amber",  hex: "#f0c53c" },
    { id: "cyan",   label: "Cyan",   hex: "#2dd8f0" },
    { id: "violet", label: "Violet", hex: "#b94af5" },
    { id: "rose",   label: "Rose",   hex: "#f25cb0" },
    { id: "lime",   label: "Lime",   hex: "#a3e635" },
    { id: "amber2", label: "Tangerine", hex: "#ff7b00" },
    { id: "blue",   label: "Cobalt", hex: "#2962ff" },
    { id: "teal",   label: "Teal",   hex: "#14b8a6" },
  ];
  const STORAGE_KEY = "studio-theme";
  const ACCENT_KEY = "studio-accent"; // null = use theme's base

  function currentTheme() {
    return localStorage.getItem(STORAGE_KEY) || "mixtape85";
  }
  function currentAccent() {
    return localStorage.getItem(ACCENT_KEY);
  }
  function themeFont(themeId) {
    const t = THEMES.find(t => t.id === themeId);
    return t ? t.font : null;
  }
  function accentColor(accentId) {
    const a = ACCENTS.find(a => a.id === accentId);
    return a ? a.hex : null;
  }

  function applyFont(themeId) {
    const font = themeFont(themeId);
    if (!font) return;
    const r = document.documentElement.style;
    r.setProperty("--display", font.display);
    r.setProperty("--mono", font.mono);
    r.setProperty("--sans", font.sans);
  }
  function applyAccent(accentId) {
    if (!accentId) return;
    const hex = accentColor(accentId);
    if (!hex) return;
    document.documentElement.style.setProperty("--accent-2", hex);
  }

  function apply(themeId) {
    if (!THEMES.find(t => t.id === themeId)) return;
    document.documentElement.dataset.theme = themeId;
    localStorage.setItem(STORAGE_KEY, themeId);
    applyFont(themeId);             // per-theme font
    applyAccent(currentAccent());   // user's accent override (if any)
    document.querySelectorAll(".theme-swatch").forEach(s => {
      s.classList.toggle("active", s.dataset.theme === themeId);
      s.setAttribute("aria-checked", s.dataset.theme === themeId ? "true" : false);
    });
    document.querySelectorAll(".theme-carousel .theme-card").forEach(c => {
      c.classList.toggle("active", c.dataset.theme === themeId);
    });
    document.dispatchEvent(new CustomEvent("studio:theme-changed", {
      detail: { theme: themeId }
    }));
  }

  function buildSwatchDock() {
    const active = currentTheme();
    const dock = document.createElement("div");
    dock.className = "theme-switcher";
    dock.setAttribute("role", "radiogroup");
    dock.setAttribute("aria-label", "Theme switcher");
    for (const t of THEMES) {
      const sw = document.createElement("button");
      sw.className = "theme-swatch" + (t.id === active ? " active" : "");
      sw.dataset.theme = t.id;
      sw.setAttribute("role", "radio");
      sw.setAttribute("aria-checked", t.id === active ? "true" : false);
      sw.setAttribute("aria-label", t.label);
      sw.title = t.label;
      const lbl = document.createElement("span");
      lbl.className = "label";
      lbl.textContent = t.label;
      sw.appendChild(lbl);
      sw.addEventListener("click", () => apply(t.id));
      dock.appendChild(sw);
    }
    document.body.appendChild(dock);
  }

  // Filterable theme carousel (Omarchy v4.0 pattern) — opens via the
  // dock's "⋯" button, shows all themes as full-size cards with a
  // substring filter input at the top.
  function buildCarousel() {
    const active = currentTheme();
    const root = document.createElement("div");
    root.className = "theme-carousel";
    root.id = "theme-carousel";
    root.hidden = true;  // hide by default
    root.setAttribute("aria-hidden", "true");
    root.setAttribute("role", "dialog");
    root.setAttribute("aria-label", "Theme carousel");
    root.innerHTML = `
      <div class="theme-carousel-inner">
        <header class="theme-carousel-header">
          <h2 class="theme-carousel-title">themes</h2>
          <input class="theme-carousel-filter" type="search"
                 placeholder="filter (e.g. catppuccin, gruvbox, mixtape)"
                 aria-label="Filter themes" />
          <button class="theme-carousel-close" aria-label="Close">×</button>
        </header>
        <div class="theme-carousel-grid"></div>
      </div>
    `;
    document.body.appendChild(root);
    const grid = root.querySelector(".theme-carousel-grid");
    function renderThemes(filter) {
      const q = (filter || "").trim().toLowerCase();
      grid.innerHTML = "";
      for (const t of THEMES) {
        if (q && !t.label.toLowerCase().includes(q) && !t.id.includes(q)) continue;
        const card = document.createElement("button");
        card.className = "theme-card" + (t.id === active ? " active" : "");
        card.dataset.theme = t.id;
        card.setAttribute("role", "listitem");
        card.setAttribute("aria-label", t.label);
        card.innerHTML = `
          <div class="theme-card-preview" data-theme="${t.id}"></div>
          <div class="theme-card-label">${t.label}</div>
        `;
        card.addEventListener("click", () => {
          apply(t.id);
          // close after selection (per Omarchy carousel UX)
          setTimeout(() => close(), 250);
        });
        grid.appendChild(card);
      }
      if (!grid.children.length) {
        grid.innerHTML = `<p class="theme-carousel-empty">no themes match "${q}"</p>`;
      }
    }
    renderThemes("");

    const filterInput = root.querySelector(".theme-carousel-filter");
    filterInput.addEventListener("input", (e) => renderThemes(e.target.value));

    // Close handlers
    const closeBtn = root.querySelector(".theme-carousel-close");
    closeBtn.addEventListener("click", close);
    root.addEventListener("click", (e) => {
      if (e.target === root) close();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !root.hidden) close();
    });
    function open() {
      root.hidden = false;
      root.setAttribute("aria-hidden", "false");
      filterInput.focus();
    }
    function close() {
      root.hidden = true;
      root.setAttribute("aria-hidden", "true");
    }
    window.themeCarousel = { open, close };
  }

  // Accent color picker — opens from the dock's "A" button. The
  // user's accent is layered on top of the active theme.
  function buildAccentPicker() {
    const root = document.createElement("div");
    root.className = "accent-picker";
    root.setAttribute("role", "group");
    root.setAttribute("aria-label", "Accent color");
    for (const a of ACCENTS) {
      const sw = document.createElement("button");
      sw.className = "accent-swatch";
      sw.dataset.accent = a.id;
      sw.setAttribute("aria-label", a.label);
      sw.title = a.label;
      sw.style.background = a.hex;
      sw.addEventListener("click", () => {
        // Clear accent on the same accent (toggle off)
        if (currentAccent() === a.id) {
          localStorage.removeItem(ACCENT_KEY);
          applyAccent(null);
        } else {
          localStorage.setItem(ACCENT_KEY, a.id);
          applyAccent(a.id);
        }
        document.dispatchEvent(new CustomEvent("studio:accent-changed", {
          detail: { accent: a.id }
        }));
        updateActive();
      });
      root.appendChild(sw);
    }
    function updateActive() {
      const cur = currentAccent();
      root.querySelectorAll(".accent-swatch").forEach(s => {
        s.classList.toggle("active", s.dataset.accent === cur);
        s.setAttribute("aria-pressed", s.dataset.accent === cur ? "true" : "false");
      });
    }
    updateActive();
    document.body.appendChild(root);
  }

  function buildTriggerButtons() {
    // Two small trigger buttons docked at the bottom-right:
    //   T  → theme carousel
    //   A  → accent picker (already docked via CSS positioning)
    const triggers = document.createElement("div");
    triggers.className = "theme-triggers";
    const carouselBtn = document.createElement("button");
    carouselBtn.className = "trigger-btn";
    carouselBtn.setAttribute("aria-label", "Open theme carousel");
    carouselBtn.textContent = "⋯";
    carouselBtn.title = "Themes";
    carouselBtn.addEventListener("click", () => window.themeCarousel.open());
    triggers.appendChild(carouselBtn);
    document.body.appendChild(triggers);
  }

  function init() {
    apply(currentTheme());   // sets data-theme + font + accent
    buildSwatchDock();
    buildAccentPicker();
    buildCarousel();
    buildTriggerButtons();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
