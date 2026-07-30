# album-studio · 11-template prototype gallery (2026-07-28)

> **TL;DR:** From 3 originals (editorial / studio / cinematic) → 11 templates. All built on the studio shell (your "B will be the initial template") but each with a distinct visual system. Inspired by awwwards (music+sound category), sitebuilderreport (musician website examples), and sonaar (waveform / spectrum / music player aesthetic). Live gallery at `~/Documents/Projects/album-studio/site/prototypes/`.

## The 11 templates

| # | Folder | Visual signature | Best for |
|---|---|---|---|
| **A** | `a-editorial/` | Cream paper, Fraunces serif, magazine issue feel | "the site should feel like opening an indie music magazine" (kept from the first round) |
| **1** | `1-studio/` | Dark mono, status-board chrome, controls-first, no hero art | **PARENT — your starting baseline** (kept from the first round, renamed from `b-studio/`) |
| **C** | `c-cinematic/` | Black + amber, Cormorant Garamond, breathing video-tile hero | "the site should feel like a movie trailer; the album IS the product, the chrome gets out of the way" (kept from the first round) |
| **2** | `2-wave/` | Live 15-bar waveform in hero. Neon-green (`#00f2b5`) accent on near-black. Translucent panels with white-text + border. **Music-oriented, but close to your studio baseline.** | "give me B but make it more music-y" |
| **3** | `3-vinyl/` | Spinning vinyl record hero (8s rotation). Tonearm. Gold + salmon-red. Tactile. Album covers feature a mini-disc that spins on hover. | "give it physical / retro / collector energy" |
| **4** | `4-cassette/` | Cassette tape hero (yellow tape + two reels + "SIDE A · DOLBY"). Album covers look like cassette labels. "SIDE A" appears in the topbar transport. Lo-fi warmth. | "lo-fi warmth, mixtape energy" |
| **5** | `5-equalizer/` | Live 16-band EQ in hero. Mini-EQ bars on every voice card. Topbar shows "32 BPM · 4/4 · ▷ LIVE" like a DAW transport. | "give it DAW-monitor energy — every voice should feel like it's running through a channel" |
| **6** | `6-spectrum/` | Full-bleed 24-band FFT background (cyan-on-black). Panels float as frosted cards over the spectrum. | "give it spectrum-analyzer energy — the whole page should look like a viz app" |
| **7** | `7-glasswave/` | Frosted glass + 3 drifting colored blobs (lavender / cyan / teal). Lavender accent. White CTA pill with backdrop-blur. | "give it frosted-glass / liquid-morph energy" |
| **8** | `8-mesh/` | 4-node aurora mesh gradient (hot-pink, blue, magenta, yellow). Vivid. The headline itself is gradient-text. Very slow breathing animation. | "give it vivid aurora-mesh energy" |
| **9** | `9-minimal/` | Hairline + content only. No panels, no cards, no chrome. Just text rows separated by 1px lines. The anti-dashboard. | "give me B minus every chrome element" |
| **10** | `10-cinematic/` | Studio shell + Cormorant Garamond italic + amber accent + hairline borders. Chat messages render as italic Cormorant (cinema subtitle feel). Slow fade transitions. | "give me B but as if every panel were a film chapter" |

## Why these 10 + 1

The brief was "B will be the initial template" + "more music oriented" + "darker backgrounds, white/clear buttons/menus, translucent elements, very nice animations, music-related icons with animation." The 8 new templates (2-10) were chosen as the strongest music-oriented variants across 8 distinct design directions:

| Direction | Inspiration | Template |
|---|---|---|
| **waveform-as-brand** | sonaar's sticky player waveform | **2 wave** |
| **physical / tactile** | vinyl-deck imagery | **3 vinyl** |
| **mixtape / lo-fi** | cassette-era musicians | **4 cassette** |
| **DAW-monitor energy** | music production software UIs | **5 equalizer** |
| **spectrum-analyzer viz** | sonaar's spectrum + awwwards music viz | **6 spectrum** |
| **liquid morph / glass** | awwwards modern glassmorphism | **7 glasswave** |
| **aurora / mesh gradients** | modern indie site trends | **8 mesh** |
| **subtraction** | what the chrome looks like when you remove it | **9 minimal** |
| **cinema over studio** | awwwards cinematic typography | **10 cinematic** |

## Design signals extracted from the inspiration URLs

| Source | What I took |
|---|---|
| awwwards.com/websites/music-sound | Inter Tight for tight mono; cream/white minimalism (templates A, 9-minimal); warm yellow accent (template 4-cassette) |
| sitebuilderreport.com/inspiration/musician-website-examples | Limited direct signal (page is JavaScript-rendered), but the album-cover-as-portal pattern informed templates 3, 4, 5 |
| sonaar.io/examples | Waveform-progress-color (`#00c78f` / `#00f2b5` neon-green on near-black); spectrum visualization; music-player-barwidth patterns (template 2-wave, 5-equalizer, 6-spectrum); dark-mode-first |

## What's still open

| # | Question |
|---|---|
| 1 | **Which template is the winner?** (or which blend of two) |
| 2 | After picking: which of the 8 mandatory intake questions do we want to answer now vs. defer to defaults? |
| 3 | After picking: do you want me to start wiring the real site (templated from the winner, with all 6 panels functional), or stay in planning mode and run the rest of the questionnaire (genres, references, vocal, language, runtime, artist)? |

## Files on disk

```
album-studio/site/prototypes/
├── index.html                (the 11-card gallery — open this first)
├── README.md                 (short overview)
├── a-editorial/index.html
├── 1-studio/index.html       (renamed from b-studio/)
├── c-cinematic/index.html
├── 2-wave/index.html
├── 3-vinyl/index.html
├── 4-cassette/index.html
├── 5-equalizer/index.html
├── 6-spectrum/index.html
├── 7-glasswave/index.html
├── 8-mesh/index.html
├── 9-minimal/index.html
├── 10-cinematic/index.html
└── screenshots/              (26 PNGs — top + full for each of 13 pages)
```

26 screenshots saved (top-of-page + full-page × 13 pages = 13 templates × 2 views). See `screenshots/template-{name}-{top,full}.png`.
