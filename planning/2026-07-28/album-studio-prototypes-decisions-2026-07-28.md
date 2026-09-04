# 2026-07-28 sonic-studio prototype decisions

## The brief (verbatim from the user)

> "we are planning to create a website that will serve as the platform/UI/UX for me to use the skills and tools to create new albums. Instead of initiating the process exclusively through the chat here, we can still have a session chat, but i want a section for the questions, a nice media rendering and play tool, i want as well to be able to choose between different layout prototypes, i want as well a voices portfolio already pregenerated so i can try them out and choose which one i want, things like that. and at the end, we can have the collection of generated albums and i can hear them."

## Scope picked: single (option B), engineered to migrate to C

| Now | Later (option C) | Migration cost |
|---|---|---|
| Static multi-page HTML (`intake.html` / `dashboard.html` / `voices.html` / `collection.html` / ...) | Full self-hosted platform with thin Express backend | swap localStorage for `lib/store.js` backed by `better-sqlite3` |
| All state in localStorage | Persistent across sessions, server-rendered entry form | one `lib/store.js` swap, per-panel code unchanged |
| 3 voice samples inline as gradient swatches | Real voice samples served from `/voices/` directory | swap gradient blocks for `<audio src=…>` |
| Python http.server (any static host) | Same Express server (or stand-alone static + API) | `lib/server.js` rewrite |
| Album-collection reads `state.json` from disk | Album-collection indexes `state.json` rows | unchanged |

## The single rule that makes migration cheap

**No panel is allowed to talk to the filesystem, the daemon, or other panels directly.**
All cross-cutting concerns go through three thin modules:

- `lib/store.js` — `get/set/del/list` interface over localStorage (now) / SQLite (later)
- `lib/od-client.js` — daemon HTTP bridge (`getProjects`, `startRun`, `getMediaConfig`, etc.)
- `lib/media-base64.js` — audio/playback helpers, server-agnostic

## The 3 prototypes (rendered at /site/prototypes/...)

| # | Path | Visual system | When to pick it |
|---|---|---|---|
| A | `/site/prototypes/a-editorial/` | Cream paper, Fraunces serif, large hero article, voice portraits in 4-column gallery, intake as numbered list, dashboard as 12-cell strip, collection as magazine grid | wants the site to feel like an indie music magazine; opening the site should feel like opening an issue, not opening a tool |
| B | `/site/prototypes/b-studio/` | Dark Mono, Linear/Vercel feel, status-board chrome with `$ voices --audition` style headers, voice list as dense inline list with play button on the right, intake as 8-row checkbox checklist, dashboard as 12-cell matrix, chat transcript with timestamps | wants the site to feel like a workbench; every panel should look like it's a terminal pane; status-first, no hero art |
| C | `/site/prototypes/c-cinematic/` | Black + amber, Cormorant Garamond serif, full-bleed video-tile hero with breathing radial-gradient animation, voices as 6-cell colored "actor on a stage" gallery, intake as 4-up storyboard panels, dashboard as 12 cinematic frames with status badges, collection as full-bleed album covers with floating play buttons | wants the site to feel like a movie trailer; slow + dark + immersive; the album IS the product, the chrome gets out of the way |

## What's still open / what to decide next

| # | Question | Why it matters |
|---|---|---|
| 1 | Which prototype (A / B / C) is closest? | drives the design tokens for the whole site |
| 2 | Are the 8 capabilities I parsed from your brief complete? | I might have missed (or invented) one |
| 3 | Is the auto-save + JSON-export still the right intake-format, or should the intake live entirely inside the site (no JSON download step)? | the question step explicitly assumed the form exports JSON; if C (self-hosted) is the future, the JSON step is unnecessary friction |
| 4 | What voice portfolio size? (6 voices felt right for variety; could be 4 / 8 / 12) | affects layout density and pre-generation cost |
| 5 | How many layout prototypes should ship? (3 felt right for variety; could be 4 / 5 / 6 — the page you saw only shows 3, but adding more is trivial) | affects the layout-picker panel width |

