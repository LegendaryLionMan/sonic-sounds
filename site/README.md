# sonic-sounds / site

This directory holds the two HTML pages that front the sonic-sounds project:

| File | Role | Reads from | Writes to |
|---|---|---|---|
| `intake.html` | 21-question interview form for a new album | localStorage (auto-save) | downloaded JSON file + cleared localStorage key |
| `dashboard.html` | 12-layer status board for an in-flight album | `state.json` (poll 30s) | nothing — read-only |

Both pages are self-contained single-file HTML — no build step, no server.
Open them directly with a browser, or serve them via `python -m http.server` from
this directory.

## Flow

```
intake.html  ────(downloads)───>  ~/Downloads/<slug>.json
        │                              │
        │ user drags/saves the file     │
        ▼                              ▼
<project root>/intake-data/<slug>.json   ←── agent watches this dir
                                              and runs the planning skill
                                              │
                                              ▼
                              <project root>/music/<slug>/
                              ├── README.md (artist brand)
                              ├── lyrics/
                              ├── music/
                              ├── state.json  ◄── dashboard reads this
                              └── ...
```

The dashboard reads `state.json` from any of:

1. `?state=…` URL override
2. `./state.json` (sibling to the page, useful for `site/state.json`)
3. `./music/<slug>/state.json` (most common — one per album)
4. `../.meta/state.json` (canonical build-skill output location)

## Design tokens

Both pages use the same brand palette (per `../DESIGN.md` §6):

- `--bg` / `--bg-soft` paper-white / parchment
- `--ink` / `--ink-soft` text / muted
- `--accent` / `--accent-soft` terracotta (CTA + active tier)
- `--rule` hairline divider
- `--status-done` / `--status-blocked` badges

Type stack:

- Display: Fraunces (serif)
- Sans: Inter
- Mono: JetBrains Mono

All values are HSL so the QA harness can verify contrast.

## Self-test

The Playwright smoke test lives at `tests/site-smoke.spec.ts` (TODO).
Manual checklist:

- [ ] intake.html renders without console errors
- [ ] typing into any field updates the `SAVED HH:MM:SS UTC` label after ~800ms
- [ ] all 8 mandatory fields filled → generate CTA enables
- [ ] clicking generate downloads `<slug>.json` matching `intake-data/schema.json`
- [ ] `state.json` not present → dashboard renders empty state with CTA to intake.html
- [ ] `state.json` present → dashboard renders 12 layer cards in 2-column grid
- [ ] progress bar matches layer statuses (done/in-progress/blocked/todo)