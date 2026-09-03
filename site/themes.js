/* site/themes.js · Theme switcher for album-studio (Omarchy-inspired).
 *
 * Renders a small floating swatch dock in the bottom-left corner of
 * every page. Each swatch shows the theme's gradient preview; click
 * to switch. The choice persists in localStorage so it survives
 * reloads.
 *
 * Available themes are defined in site/themes.css (CSS variables).
 */
(function() {
  const THEMES = [
    { id: "mixtape85",  label: "Mixtape '85" },
    { id: "tokyonight", label: "Tokyo Night" },
    { id: "catppuccin", label: "Catppuccin" },
    { id: "gruvbox",    label: "Gruvbox" },
  ];
  const STORAGE_KEY = "studio-theme";

  function currentTheme() {
    return localStorage.getItem(STORAGE_KEY) || "mixtape85";
  }
  function apply(themeId) {
    if (!THEMES.find(t => t.id === themeId)) return;
    document.documentElement.dataset.theme = themeId;
    localStorage.setItem(STORAGE_KEY, themeId);
    document.querySelectorAll(".theme-swatch").forEach(s => {
      s.classList.toggle("active", s.dataset.theme === themeId);
      s.setAttribute("aria-checked", s.dataset.theme === themeId ? "true" : "false");
    });
    document.dispatchEvent(new CustomEvent("studio:theme-changed", {
      detail: { theme: themeId }
    }));
  }

  function build() {
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
      sw.setAttribute("aria-checked", t.id === active ? "true" : "false");
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

  function init() {
    apply(currentTheme());   // sets the data-theme on :root
    build();                 // builds the dock with the active swatch highlighted
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
