# album-studio · prototype gallery

Three visual systems, same six panels. Pick one (or none).

## The gallery

Open `index.html` to see all three side-by-side. Each card is an iframe preview of the full prototype.

```
album-studio/site/prototypes/
├── index.html           # this gallery
├── a-editorial/index.html
├── b-studio/index.html
└── c-cinematic/index.html
```

Each is one self-contained HTML file. No build step. No JavaScript that talks to anything.

## The 3 systems

| File | System | Best for |
|---|---|---|
| `a-editorial/` | Editorial magazine — Fraunces serif, cream paper, dense voice portraits, intake as numbered list, dashboard as 12-cell strip, collection as magazine grid | "the site should feel like opening an issue of an indie music magazine" |
| `b-studio/` | Studio tool — JetBrains Mono, dark grid, `$ voices --audition` style headers, voice list with right-side play, intake as 8-row checkbox checklist, dashboard as 12-cell matrix, chat transcript with timestamps | "the site should feel like a workbench — every panel is a terminal pane" |
| `c-cinematic/` | Cinematic — Cormorant Garamond serif on black, breathing radial-gradient video-tile hero, voices as 6 colored "actors on a stage", intake as 4-up storyboard, dashboard as 12 cinematic frames with status badges, collection as full-bleed album covers with floating play buttons | "the site should feel like a movie trailer; the album IS the product, the chrome gets out of the way" |

## How to compare

Each prototype renders all six panels (concept / voices / intake / dashboard / collection / chat) with the same content (Maren Sol · dream-folk · Half-Light Hours). Open them in three tabs side-by-side.

## How to decide

Tell me which one (A / B / C / none of these / blend of two) and I'll build the real site on top of it.

## Self-test checklist

- [ ] gallery index renders all 3 iframes
- [ ] each prototype top-of-page matches the description above
- [ ] the three panels feel distinct at first glance
- [ ] the same content (Maren Sol / Half-Light Hours / 6 voices) is present in all three

Screenshots of all 4 pages at desktop (1440×900) live at `screenshots/prototype-{A,B,C,gallery}-{top,full}.png`.
