// ============================================================
// PENPOT AUTO-IMPORTER — fired when the browser plugin connects
// ============================================================
// Run by the background watcher. Idempotent.

const r = { steps: [], created: [] };

// ----- 1. Token set -----
function getOrCreateSet(name) {
  const s = penpot.library.local.tokens.sets.find(x => x.name === name);
  return s ? s : penpot.library.local.tokens.addSet({ name });
}
const ds = getOrCreateSet("sonic-studio/design-system");

function getOrCreateToken(set, type, name, value) {
  const t = set.tokens.find(x => x.name === name);
  return t ? t : set.addToken({ type, name, value });
}

const COLORS = [
  ["color/paper",            "#F4EFE6"],
  ["color/ink",              "#1B1714"],
  ["color/ink-soft",         "#3D3530"],
  ["color/rule",             "#C9BFAE"],
  ["color/accent",           "#B8503A"],
  ["color/accent-soft",      "#D9846F"],
  ["color/highlight",        "#E8D9A8"],
  ["color/status-done",      "#4A6B47"],
  ["color/status-active",    "#B8503A"],
  ["color/status-blocked",   "#7A1F1F"],
];
const FONTSIZES = [
  ["font-size/xs", "12"], ["font-size/sm", "14"], ["font-size/base", "17"],
  ["font-size/md", "20"], ["font-size/lg", "28"], ["font-size/xl", "44"],
  ["font-size/2xl", "68"], ["font-size/3xl", "104"],
];
const SPACINGS = [
  ["spacing/xs", "8"], ["spacing/sm", "16"], ["spacing/md", "24"],
  ["spacing/lg", "32"], ["spacing/xl", "48"], ["spacing/2xl", "64"],
  ["spacing/3xl", "96"],
];
COLORS.forEach(([n, v]) => getOrCreateToken(ds, "color", n, v));
FONTSIZES.forEach(([n, v]) => getOrCreateToken(ds, "fontSizes", n, v));
SPACINGS.forEach(([n, v]) => getOrCreateToken(ds, "spacing", n, v));
getOrCreateToken(ds, "borderRadius", "border-radius/none", "0");
r.steps.push({ step: "tokens", total: COLORS.length + FONTSIZES.length + SPACINGS.length + 1 });

// ----- 2. 6 Pages -----
const PAGE_NAMES = [
  "01 — Design System",
  "02 — Components",
  "03 — Intake",
  "04 — Dashboard",
  "05 — Cover Exploration",
  "06 — Motif Library",
];
const pages = {};
for (const name of PAGE_NAMES) {
  let p = penpotUtils.getPages().find(pg => pg.name === name);
  if (!p) {
    p = penpot.createPage();
    p.name = name;
  }
  pages[name] = p;
}
r.steps.push({ step: "pages", count: PAGE_NAMES.length });

// ----- 3. Import the 6 PNGs into the right pages -----
// Images live in C:\Users\lion_\Documents\Projects\sonic-studio\site\penpot-pages\
// We need to read them via the local file system. The plugin sandbox has access.
const PNG_DIR = "C:\\Users\\lion_\\Documents\\Projects\\sonic-studio\\site\\penpot-pages\\";

const PAGE_TO_PNG = [
  ["01 — Design System",      "01-design-system.png"],
  ["02 — Components",         "02-components.png"],
  ["03 — Intake",             "03-intake.png"],
  ["04 — Dashboard",          "04-dashboard.png"],
  ["05 — Cover Exploration",  "05-cover-exploration.png"],
  ["06 — Motif Library",      "06-motif-library.png"],
];

async function importPagePng(pageName, pngFile) {
  const page = pages[pageName];
  penpot.openPage(page);
  // Wait briefly for the page to focus
  await new Promise(r => setTimeout(r, 200));

  const path = PNG_DIR + pngFile;

  // Read the file from disk using fetch with file:// (Penpot plugin sandbox)
  let imageData;
  try {
    const response = await fetch("file:///" + path.replace(/\\/g, "/"));
    const blob = await response.blob();
    const buffer = await blob.arrayBuffer();
    const data = new Uint8Array(buffer);
    imageData = await penpot.uploadMediaData(pngFile, data, "image/png");
  } catch (e) {
    return { page: pageName, file: pngFile, error: "fetch failed: " + e.message };
  }

  // Create a rectangle that uses the image as a fill
  const rect = penpot.createRectangle();
  rect.name = pngFile.replace(".png", "");
  rect.resize(imageData.width, imageData.height);
  rect.fills = [{
    fillImage: imageData,
    fillOpacity: 1,
  }];
  rect.x = 0;
  rect.y = 0;

  // Add to the page root
  page.root.appendChild(rect);

  return {
    page: pageName,
    file: pngFile,
    imageWidth: imageData.width,
    imageHeight: imageData.height,
    rectId: rect.id,
  };
}

for (const [pageName, pngFile] of PAGE_TO_PNG) {
  const result = await importPagePng(pageName, pngFile);
  r.created.push(result);
}

r.steps.push({ step: "png-imports", count: r.created.length, results: r.created });

// ----- 4. Final state -----
r.summary = {
  tokensCreated: COLORS.length + FONTSIZES.length + SPACINGS.length + 1,
  pagesCreated: PAGE_NAMES.length,
  pngsImported: r.created.length,
  errors: r.created.filter(c => c.error).length,
};

return r;
