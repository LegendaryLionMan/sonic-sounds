# UX Research Memo — Album-Creator Studio Patterns

> Research date: 2026-07-30
> Audience: the sonic-studio project (editorial-zine aesthetic, Half-Light Hours / Maren Sol visual world).
> Goal: identify UI/UX patterns worth borrowing for an album-CREATOR interface (not a player).
> Method: `browser_navigate` was unavailable on this host (Chrome failed to launch with `--no-sandbox`); fell back to `web_search_plus` + `curl` extraction of 20+ sources, cross-referenced with the user's existing Half-Light Hours delivery package and the `sonic-studio/DESIGN.md` token system.

---

## 0. Ground rules (so "borrow" / "skip" decisions aren't arbitrary)

The sonic-studio's `DESIGN.md` already commits us to:

- **Editorial zine**, warm paper (`#F4EFE6`), ink (`#1B1714`), one terracotta accent (`#B8503A`).
- **Serif** display + body, mono for metadata.
- **No SaaS dashboard chrome** (no card grids, no gradient heroes, no green/black Spotify-isms).
- **Restrained motion**, hairline dividers, asymmetric 12-col grid with a "meta column" rail.
- **Status via text + icon**, never color alone.

So a "borrow" from Suno or DistroKid must survive translation into paper-and-ink language. Anything that needs neon, drop-shadows, modals on modals, or video autoplay is by definition out. This memo evaluates each platform with that filter applied.

---

## 1. Suno (suno.com) — the AI-music creator UX

**What it does well.** Suno's editor (v4.5) treats the song as a *timeline of named sections*, not a black box. Each generated clip has a sectioned view: verses, chorus, bridge get named labels and color-coded blocks. The "Quick Replace" button under any section triggers a fresh generation of that section only — the rest of the song stays put. Section boundaries are draggable so you can re-shape the structure (swap verse order, extend a chorus). Lyrics sit on the left as an editable text panel; clicking any word re-generates that moment. The "+ section" insertion point and "Fade In/Out" controls on the first/last section corners are small but crucial affordances for non-engineer creators.

**Pattern to borrow — sectioned audition.** The "create → audition → iterate" loop with per-section regeneration (not full-track regeneration) is the single most valuable UX lesson in this whole memo. The user spends most of their time auditioning variants of *one moment*, not regenerating whole songs. Our studio's "Layer 02 — Songwriting" and "Layer 04 — Music" should let the user audition variants per-line, per-section, or per-stem, rather than only whole-track.

**Pattern to borrow — fade corners.** Tiny triangles in the bottom corners of the first and last section. Quietly lets the user add fades without opening a modal. Very zine-friendly: a glyph, not a button.

**Pattern to borrow — section drag-to-reorder.** Sections are grabbable handles; re-ordering is direct manipulation. We're not building a DAW, but the *song-arrangement step* in Layer 03 (Tracklist) should support drag-to-reorder track sequences and drag-to-reorder sections within a track.

**Skip — Suno's overall chrome.** Suno uses a black background with neon-orange CTAs and dense toolbars. Doesn't translate. The section-block color-coding can be re-imagined as terracotta `--status-active` outlined blocks on warm paper, with section names in italic display serif.

**Skip — Suno's "stems export" paywall nag.** Anti-pattern; would jar against the editorial voice.

**Recommendation: Add to studio — "audition variants per section" + fade-corner glyph + drag-to-reorder. Skip the chrome. Investigate further the "Replace Lyrics Box" interaction for Layer 02 (lyrics editor).**

---

## 2. Udio (udio.com) — AI-music creator

**What it does well.** Udio's *remix and inpainting* tools let you punch in changes to specific sections (intro, outro, chorus) without regenerating the whole track. The interface "resembles a music player" rather than Suno's "creator console" — the generation entry point isn't a giant CTA, it's a transport-bar with record-in-place controls. Udio offers deeper per-section control: song length, instruments, tempo, and structure are adjustable post-generation. Reviews consistently credit Udio with "more direct control" and "more hands-on options beyond simple prompts."

**Pattern to borrow — the audio-player-as-creation-console idea.** Udio's conceit — "the creation UI is just a player with extra modes" — is more on-aesthetic for our zine studio than Suno's creator-dashboard. Our studio's `Layer 04 — Music` should foreground the audio as the primary surface; controls (regenerate, fork, edit) should appear in a player-style transport bar, not as a separate toolbar above it.

**Pattern to borrow — section-based inpainting metaphor.** Even if we never expose real inpainting, the *vocabulary* is useful: "fork from intro," "regenerate from 1:24," "edit chorus only." This gives the user a sense of surgical control without an actual audio editor.

**Skip — Udio's "blending features" / collaboration-mode UI.** The cloud-collab session list and feedback threads are SaaS-y.

**Recommendation: Investigate further — Udio's player-as-studio framing aligns with editorial restraint. Borrow the "transport-bar with mode chips" pattern (Create / Remix / Extend modes sitting in the same strip).**

---

## 3. Bandcamp (bandcamp.com) — the indie-press gold standard

**What it does well.** Bandcamp's album page is one of the few player-UI artifacts that genuinely respects the album as an *object*. Key moves:

- **Square cover art front and center**, minimum 1400×1400, treated as the page's hero.
- **Custom header image** (1280×1440) gives the artist a chance to carry the album's visual identity into the chrome itself.
- **Tracklist with individual buy buttons**, not a single "buy album" — fans can pick tracks, and Bandcamp clearly tells the artist "people buy more music from cool-looking pages."
- **"More from this artist"** below the tracklist surfaces their other releases, merch, and follows — a natural secondary discovery rail.
- **Real-time color picker** in the Design Panel: page bg, text, and link colors update live. You match two of the colors from your cover art. The advice is explicit: *"don't obscure your link colors, don't set them to the same color as your text."* High-contrast is the unbreakable rule.
- **Discography ordering** is drag-reorderable from the artist dashboard.

**Pattern to borrow — cover-as-hero.** Our studio should treat the album cover as the literal hero of the dashboard (not a sidebar thumbnail). Layer 01 (Album concept) and Layer 06 (Cover art) should converge on this.

**Pattern to borrow — the "match 1–2 colors from your cover art" rule.** This is the exact instruction we should put in our `Layer 06 — Cover Art` UI: "Pick a primary and accent color by eyedropping the cover. Don't override them later."

**Pattern to borrow — tracklist with per-track affordances.** Our studio's Layer 03 (Tracklist) should let the user click any track and see its lyric snippet, length, mood, status. Not just "tracks 1–10 in a list."

**Pattern to borrow — drag-reorder discography.** Already noted from Suno; Bandcamp confirms it as the indie-press convention.

**Skip — Bandcamp's player-UI itself.** It's functional but visually plain — large play buttons, orange-on-blue gradients, dense "wishlist / share / buy" action stacks. Not editorial.

**Skip — Bandcamp's full-bleed custom background images.** Tempting, but risks competing with the cover. Our paper background is the whole point.

**Recommendation: Add to studio — cover-as-hero, "match 1–2 colors from your cover" prompt in Layer 06, drag-reorderable tracklist, per-track affordance rows. Skip the player chrome.**

---

## 4. DistroKid (distrokid.com) — release pipeline UX

**What it does well (and where it falls down).** DistroKid's "upload to release" pipeline is built for one task: get an independent artist's track to Spotify in under 5 minutes. The dashboard lists releases as cards with status (draft / scheduled / live), ISRC and UPC auto-assigned, cover art upload next to the track list. Approval is fast.

But — and this is why it matters — the *design* is widely criticized. Indie musician Richard Pryn's review is representative: *"I am not a huge fan of the Distrokid interface. I like clean and simple webpages but it feels like the type of HTML website I might have built when I was learning to code HTML. The Distrokid upload page looks a little underwhelming."* The upload page is form-on-form-on-form with no editorial structure.

**Pattern to borrow — the release-status card.** A "layer card" with: release name, target date, status badge, store-availability progress. Our existing `Layer card` component already copies this DNA (last-updated timestamp + status + "open layer →"). We should formalize it as a `Release card` and use it on the post-release dashboard too.

**Pattern to borrow — ISRC/UPC auto-assignment, hidden from user.** The user shouldn't see ISRC fields unless they opt into "advanced." This is a *progressive-disclosure* pattern worth borrowing for our studio's "Metadata" layer (Layer 05): show ISRC, UPC, copyright ℗, and release-territory defaults only in an "advanced" disclosure, surfaced by a hairline-bordered "advanced settings" toggle.

**Skip — DistroKid's form-stacking UI.** Pure SaaS — every field visible at once, no grouping, no narrative. Everything we *don't* want.

**Skip — DistroKid's "Boost" / "Spotify Verified Checkmark" upsell modal.** Anti-pattern, would shatter the zine voice.

**Recommendation: Add to studio — release-status card as the dashboard's primary atom, progressive-disclosure for metadata fields, "stores" status (draft / pending / live) as a footer row. Skip the form stacks.**

---

## 5. TuneCore (tunecore.com) — release pipeline, different style

**What it does well.** TuneCore's review process is more thorough than DistroKid's — and the UI reflects that: the dashboard leans into a *release-calendar* view, with each release as a scheduled event on a timeline. The release flow has clearer "approval gates" (cover art check, audio quality check, metadata review) before submission. For studios that want fewer surprises on release day, this is the better reference.

**Pattern to borrow — approval gates as visible checkpoints.** DistroKid hides approval behind the curtain; TuneCore shows you a 3–4-step checklist ("Audio ✓ · Cover ✓ · Metadata ✓ · Stores ✓") before letting you submit. Our studio's `Layer 05 — Metadata` should have a similar visible checklist, but in editorial language: not "✓ Audio uploaded," but "**AUDIO QUALITY** — `M·05` ready · `R·07` needs re-export." Each line is a layer question (see DESIGN.md §6 "Question row") with a tier tag.

**Pattern to borrow — release calendar.** TuneCore's calendar view of upcoming, current, and past releases is exactly the right shape for our `Layer 09 — Pre-save & Pitch` (the pitch-a-song timeline). A vertical timeline on paper, with weeks laid out as 88px-tall rows.

**Skip — TuneCore's pricing-tier upsell matrix.** Eight plan cards with green/orange/red highlights. Avoid at all costs.

**Recommendation: Add to studio — visible "checkpoints" between layers (the cross-layer handoff is currently abstract), release-calendar view for the post-tracklist phase. Skip the tier-pricing layouts.**

---

## 6. Spotify for Artists (artists.spotify.com)

**What it does well.** Spotify for Artists segments its dashboard into three clearly-named jobs:

1. **Amplify your music** — campaigns, marquees, pitch-a-song.
2. **Connect with fans** — profile, Canvas, Clips, Countdown Pages.
3. **Understand your audience** — analytics, listener demographics, super-listeners.

The post-release analytics page is a master-class in storytelling-with-data: it leads with the most-shareable number ("42,103 first-month listeners") and buries the breakdowns underneath. The pitch-a-song flow is a *structured text form* with tier fields (genre, mood, instruments, release story) and a hard pitch date.

**Pattern to borrow — the three-pillar framing.** "Amplify · Connect · Understand" maps cleanly to our studio's post-release state: **Distribute · Pitch · Measure.** We should label our dashboard columns/tiles this way once an album goes live.

**Pattern to borrow — the lead-with-one-number analytics.** Don't show a fan with 14 graphs. Show one big serif number ("3,412 first-week listeners"), then a hairline, then 4–5 drilldowns. The Spotify Wrapped-style packaging of analytics is a known conversion tactic; even if we won't run an annual campaign, the *format* (one number, then a paragraph of context, then drilldowns) is editorial-friendly.

**Pattern to borrow — pitch-a-song structured form.** Tier-tagged fields (genre, mood, story, "what would you say to a listener who's never heard of you?"). Maps directly to the `Question row` component in DESIGN.md §6.

**Skip — Spotify's green-on-black.** Doesn't translate.

**Skip — Spotify's chart visualizations.** Pie charts, sparkline mountains, gradient bubbles. We can do this with horizontal hairline bars in serif numerals and one accent color. No SVG donuts.

**Recommendation: Add to studio — three-pillar post-release dashboard (Distribute / Pitch / Measure), pitch-a-song structured form with tier-tagged fields, "lead with one big number" analytics pattern. Investigate further: how Spotify Wrapped packages personality into data (potentially a model for our own "album wrap").**

---

## 7. LANDR (landr.com) — AI mastering interface

**What it does well.** LANDR's plugin (Sound on Sound review, 2024–26) presents AI mastering with *restraint*: "you don't have to choose any sort of target profile. In fact, you don't even need to pigeonhole it into a genre — while messages suggest it is determining the genre for your track, LANDR tells me the plug-in creates an individual 'target' profile, based on a comparison of your track's characteristics with its massive library of references." The on-screen messages during processing say things like *"measuring frequency response"* and *"determining genre"* — visible, in plain language, not jargon.

The CDM review (2023) is more candid about earlier versions: *"the black-box results just tended to squash the sound … Sure, it sounded louder, but not with any particular regard for the source material."* This is the trap to avoid.

**Pattern to borrow — plain-language AI status messages.** During a generation or mastering pass in our studio, the *progress panel* should narrate what the AI is doing in human terms: "**ANALYZING TONE** — measuring frequency response," "**MATCHING GENRE** — comparing to ~3,200 references," "**APPLYING EQ** — softening 2.4 kHz to balance the vocal." One accent color, mono font, ALL CAPS, like an old studio console's status LED row.

**Pattern to borrow — confidence / honest uncertainty.** LANDR's newer versions explicitly tell the user when they're inferring ("messages suggest it is determining the genre"). We should do the same: when our studio's audit tools flag something as "needs review," they should say *why* in one sentence, not just mark it red.

**Pattern to borrow — before/after A/B.** The mastering workflow is essentially "here's where you were, here's where you are, here's what changed." Our studio's `Layer 08 — Mastering` (or wherever the AI audio tools land) should have a clean A/B switch with three lines underneath: "**+1.4 dB** · high-shelf lift on vocals," "**−0.6 dB** · 200 Hz mud cut," "**+0.3 dB** · stereo width on chorus." Three lines, max.

**Skip — LANDR's knobs-and-meters plugin GUI.** Looks like every other VST — virtual analog hardware, knobs, level meters. Doesn't fit zine.

**Recommendation: Add to studio — plain-language AI status messages (ALL CAPS, mono), explicit "why this needs review" explanations on flagged items, A/B before-after with three-bullet change list. Skip the analog-knob aesthetic.**

---

## 8. Splice (splice.com) — sample library

**What it does well.** Splice is *the* reference for "search → audition → drag-to-project." The site is a sample marketplace, but the workflow is: search by text or "Search with Sound" (drag an audio clip → AI finds similar samples), audition in a mini-player, drag-and-drop directly into Ableton / Logic / FL Studio. The cloud DAW, BandLab Studio, plus every major DAW now has Splice integration — "search with sound" surfaces samples that match the BPM, key, and texture of what's already on your timeline.

**Pattern to borrow — Search with Sound.** The user drops in a lyric line or a mood word; the studio returns candidate sounds. This is the right shape for our `Layer 04 — Music`: drop a one-line mood brief, get back auditions.

**Pattern to borrow — audition preview that doesn't commit.** Click a sample → it plays in a small player; nothing is added to the project until you drag. Our studio's generation cards should preview audio inline (a play button that doesn't navigate away).

**Pattern to borrow — drag-to-project.** Splice's drag handle works in any DAW. Our studio should support drag-to-reorder within the tracklist (already noted) and possibly drag-to-include-into-a-mix.

**Skip — Splice's subscription/credit math.** "9 credits per pack, 2 credits per loop" — the UI is full of credit counters and "you have 14 credits" popovers. Too commerce-y for our voice. If we ever gate features, use *named tiers* (e.g. "STUDIO TIER") not credit counters.

**Skip — Splice's pack-artwork-heavy tile grid.** Tiles-as-cards is the SaaS pattern we're avoiding. Our versions should be hairline-bordered rows with text-forward content.

**Recommendation: Add to studio — "search with sound" pattern (mood brief → auditions), inline preview without commit, drag-to-reorder. Skip the credit-counter UI.**

---

## 9. SoundCloud (soundcloud.com) — waveform player

**What it does well.** SoundCloud's *waveform with timestamped comments* is one of the most-copied audio-UI patterns on the web. A horizontal waveform; dots underneath mark where listeners have commented; click a dot → seek + open the comment thread. The waveform itself is the navigation. SoundCloud also pioneered the "Stations" auto-play queue — when a track ends, a related track plays, and the queue is visible.

The academic literature on SoundCloud's UX (Hesmondhalgh, Jones, Rauh, *Social Media + Society*, 2019) describes the waveform-and-comment-timeline as the platform's signature: *"a profile page from SoundCloud, showing the waveform and timestamped comments."*

**Pattern to borrow — the waveform as navigation surface.** Our studio's `Layer 04 — Music` track view should let the user click anywhere on the waveform to seek, and (optionally) place hairline-marked notes at specific timestamps ("fix this vocal at 1:24"). This becomes a comment-timeline *for the artist to themselves*.

**Pattern to borrow — what's-coming-next queue.** When a track ends, the next audition plays. The mini-queue at the bottom is three entries deep, with cover thumbnails and titles. This is the right shape for our "Variants" panel in `Layer 04`: when auditioning a generated track, show 2-3 sibling takes in a hairline-bordered "next" strip.

**Skip — SoundCloud's neon-orange waveform.** Replace with ink-on-paper monochrome waveform, terracotta `--accent` for the played-progress portion. (See §11 below for implementation library.)

**Skip — SoundCloud's autoplay-with-no-quit UI.** The forced autoplay is widely disliked.

**Skip — SoundCloud's cluttered track-page chrome.** Buy, like, repost, share, comment, stations, related, more-by — 14 actions stacked.

**Recommendation: Add to studio — click-to-seek waveform with timestamped artist notes (the self-comment pattern), 3-deep "next auditions" queue strip. Skip the neon and the action-stack chrome.**

---

## 10. Half-Light Hours album page (existing)

**What's there.** The existing delivery package at `OneDrive/Hermes/albums/Half-Light-Hours/` is a *file structure*, not a rendered page. README.md, 10 MP3s, 10 lyrics .md files, cover art, posters, merch designs, press kit, social rollout plan, podcast interview script + audio, storyboard frames. The README is the closest thing to an "album page" — it has the 10-track table, visual identity section (palette + typography + motif), budget, deliverables count, and next-steps.

**What's missing (and what the studio can fix).**

- **No unified web page.** There's no actual `index.html` for the album. The README is the closest analog.
- **No cross-linked navigation.** Press kit, lyrics, social rollout, Spotify pitch — each is its own .md with no links to the others except via the README's folder tree.
- **No player.** The 10 MP3s sit in `music/` but there's no in-repo HTML player. Listeners would go to a streaming platform.
- **No "this is what the studio produced" lineage.** There's no link between `OneDrive/albums/Half-Light-Hours/` (the artifact) and `Documents/Projects/sonic-studio/` (the studio). For someone using the studio, it should be obvious: "the studio created this album, here are the layers it went through."

**Pattern to establish — the studio's "Output" pane.** When the studio produces an album, the output side should show:

- Cover art (hero, ~300×300 thumb → click for full size).
- Tracklist (10 rows, each linking to the lyric file, the MP3, and the storyboard).
- "Made with" sidebar listing the 12 layers with statuses (e.g. "Layer 01 — Concept · DONE," "Layer 02 — Lyrics · DONE (10/10)," "Layer 09 — Distribution · IN-PROGRESS").
- Visual identity (palette swatches, type sample, motif mark).
- Export buttons (download zip, copy landing-page markdown, open in Spotify for Artists).

This is what the sonic-studio *delivers*. The README.md is a great reference; the studio should render it.

**Skip — the README's emoji section markers (📀 🎬 🎤).** The README uses 📀/🎬/🎤/⭐/📋 etc. as section icons. Cute but not editorial — should be hairline rules + italic display serif section labels in the rendered version.

**Recommendation: Add to studio — an "Album Output" pane that renders an existing README-style album page as a paper-and-ink page, with cover hero + tracklist rows + "Made with" sidebar showing the layer states. Skip the emoji section markers.**

---

## 11. Cross-cutting technical research

### Web audio waveform libraries

| Library | Strengths | Weaknesses | Recommendation |
|---|---|---|---|
| **wavesurfer.js v7** | TypeScript rewrite, Shadow-DOM isolation, plugin system (Regions, Timeline, Spectrogram, Minimap, Hover, Record, Envelope). 4-line "hello world." Easy click-to-seek, regions for selecting ranges. | Decoding in browser is slow for long files; need pre-decoded peaks for big tracks. | **Primary choice** — covers click-to-seek, regions (per-section edits), and timeline. Use regions plugin for our "section blocks" pattern. |
| **peaks.js** | BBC-maintained, designed for broadcast-audio (long-form, multitrack). Cue points, segments, zoom. Robust on very long files. | Heavier API, more opinionated UI chrome. | **Investigate further** — overkill for single-track auditions, but the right choice if we add multitrack. |
| **Howler.js** | Lightweight, great for simple playback. | No waveform rendering. | Skip — we need visual audition. |
| **Tone.js** | Synth-level Web Audio framework. | Not a player — too low-level. | Skip for the player; consider only if we add synth features. |
| **Web Audio API directly** | Total control. | Reinvents the wheel. | Skip — let wavesurfer handle it. |

**Decision: wavesurfer.js v7 with the regions and timeline plugins.** Style the waveform as ink (`#1B1714`) with a terracotta (`#B8503A`) progress overlay. Mono waveform, no neon.

### Drag-and-drop multi-track layouts (DAW web)

| Product | Pattern | Borrow? |
|---|---|---|
| **BandLab Studio** | Free, browser DAW. Drag samples from "Sounds" library into the timeline. Loop/region drag. Auto-bpm-sync. | Yes — drag-to-timeline is the right metaphor for `Layer 04` and `Layer 03`. |
| **Soundtrap** | Clean web DAW, the closest competitor to BandLab. | Investigate — reportedly better UI polish. |
| **BandLab Sounds** | Royalty-free sample library with search + drag. | Yes — search + audition + drag is exactly the Splice pattern. |
| **Ableton Live 12.3 + Splice** | Splice's "search with sound" integrates into the DAW timeline via drag. | Yes — this is the future we want. |
| **Audacity** | Desktop-only, dense UI, not a web pattern. | Skip. |

**Decision: the drag-to-timeline + drag-from-library pattern is universal and worth lifting whole.** Our studio's tracklist view should accept drops (a generated audition, an MP3 from the user's OneDrive) onto a row, and the row should reorder on drag.

### Lyrics display patterns (Genius, Musixmatch)

- **Genius** is the annotation-first model: lyrics on the left, annotations on the right, line-by-line. The annotation is the *product*. Anyone can propose lyric edits; artists can verify. The formatting rules are explicit: "Use song part headers above different song parts," "type out all lyrics, even when a section is repeated," "break transcriptions up into individual lines." This is editorial-document DNA.
- **Musixmatch** is the synced-lyrics model: lyrics timestamped to the audio, displayed in Spotify, Apple Music, Instagram Stories. The 2026 update: Google Search now displays verified synced lyrics in organic search results. This makes synced lyrics a *discovery* feature.
- **Apple Music / Spotify karaoke mode**: synced lyrics now scroll in time with playback. The lyric line currently being sung is highlighted in a different weight or color.

**Pattern to borrow — section headers + line breaks.** Use `[Verse 1]`, `[Chorus]`, `[Bridge]` as italicized mono headers. Break lyrics into individual lines (no wrapping). Genius's discipline here is correct.

**Pattern to borrow — time-aligned lyric display (LRC).** The Half-Light Hours folder already has `lyrics-lrc/03-half-light-hours.lrc` — synced-lyrics files exist. Our studio's lyric editor should preview the LRC alongside the lyrics and let the user click any line to seek the audio there.

**Skip — Genius's annotation/community chrome.** Annotation by fans is not what our user is building.

**Skip — Musixmatch's Instagram Stories lyric-sticker generation.** Clever but not on-aesthetic.

**Recommendation: Add to studio — section headers as italic mono labels, one lyric per line, click-to-seek against synced LRC for the LRC file the user provides or that we auto-generate. Skip the annotation chrome.**

### Vintage cassette-deck / "now playing" UI inspiration

The aesthetic pool to draw from:

- **Cassette deck UI**: physical transport buttons (play / pause / stop / rewind / ff / record), two reels visible, window into moving tape. The "moving reels" animation is unnecessary but the *typographic* signal — chunky mechanical buttons, all-caps labels, mono numerals — translates beautifully to paper-and-ink.
- **Walkman-era orange LCD**: warm amber on dark; we have `--highlight: #E8D9A8` (warm amber paper) which is the inverse. Our "now playing" panel can be an amber-tinted rectangle with mono amber numerals for time-elapsed and time-remaining.
- **Vinyl-era turntable**: the spindle, the tonearm, the album-art-sized platter. Same idea — the artifact itself is the visual.
- **Notebook margin scribbles**: timestamps in handwriting-style italics, small annotations in the margin. The self-comment pattern from SoundCloud maps naturally here.

**Recommendation: the studio's `Now Playing` panel (when previewing a generated track) should be a warm-amber rectangle with mono numerals, an italic serif "track NN — title" caption, and a hairline-bordered transport row. No animated reels, no spinning vinyl — the artifact metaphor is enough.**

---

## 12. Synthesis: what goes in the studio

Pulling the patterns together, here's the prioritized short-list of *additions* (in order of likely ROI):

| # | Pattern | Source | Where it lands in the studio | Effort |
|---|---|---|---|---|
| 1 | **Sectioned audition** with per-section regenerate | Suno | Layer 04 — Music | M |
| 2 | **Drag-to-reorder tracklist** | Suno, Bandcamp | Layer 03 — Tracklist | S |
| 3 | **Cover-as-hero** + "match 2 colors from cover" prompt | Bandcamp | Layer 01 + Layer 06 | S |
| 4 | **Approval-gate checklist** between layers | TuneCore | Cross-layer handoff UI | M |
| 5 | **Plain-language AI status messages** | LANDR | All generation steps | S |
| 6 | **Three-pillar post-release dashboard** (Distribute / Pitch / Measure) | Spotify for Artists | Post-tracklist view | M |
| 7 | **Click-to-seek waveform with timestamped artist notes** | SoundCloud | Layer 04 — Music player | M |
| 8 | **Section headers + line-broken lyrics + LRC sync** | Genius, Musixmatch | Layer 02 — Lyrics | S |
| 9 | **"Album Output" pane** (renders the README as a paper-and-ink page) | Half-Light Hours own README | Output tab | L |
| 10 | **Release-status card** as dashboard atom | DistroKid, TuneCore | Dashboard home | S |
| 11 | **Search-with-sound / mood-brief → auditions** | Splice, BandLab | Layer 04 — Music entry | L |
| 12 | **Vintage "now playing" panel** (amber rectangle, mono numerals) | Cassette-era aesthetic | Every player surface | S |
| 13 | **Lead-with-one-number analytics** | Spotify Wrapped | Layer 12 — Post-release | M |
| 14 | **Pitch-a-song structured form with tier tags** | Spotify for Artists | Layer 09 — Pitch | S |
| 15 | **A/B before-after with three-bullet change list** | LANDR mastering | Layer 08 — Mastering | S |

### What we explicitly skip

- SaaS dashboard chrome (card grids, gradient heroes, modals-on-modals, credit counters).
- Spotify's green-on-black, SoundCloud's neon-orange.
- Knob-and-meter plugin GUIs.
- Genius annotation chrome, SoundCloud's autoplay-with-no-quit.
- DistroKid / TuneCore pricing-tier upsell matrices.
- Splice's tile-pack grid.

---

## 13. Open questions to investigate further

These came up repeatedly and deserve a follow-up research pass before implementation:

1. **Wavesurfer regions → our section blocks.** Can regions be styled with terracotta and renamed? How does it interact with the timeline plugin?
2. **LRC auto-generation.** Musixmatch / lyric.ai can generate synced lyrics from audio. Do we want this as a Layer 02 affordance, or is the user always providing LRC manually?
3. **Search-with-sound for our generation pipeline.** What's the minimum implementation that gets the *feel* of Splice's drop-an-audio-get-back-similar-results without building a real ML pipeline?
4. **Cassette-deck "Now Playing" panel — exact composition.** Is the amber rectangle too on-the-nose for editorial, or does it work as a callback to the Half-Light Hours "warm amber accent (`#D4A574`)" already in the album's palette?
5. **Album Output page — single static HTML or a renderer?** Should the studio *generate* the output page from layer state (JSON → HTML), or should the user maintain it like a README?

---

## 14. Sources

- Suno Song Editor docs — `help.suno.com/en/articles/6141505`
- Musicful AI comparison — `musicful.ai/vs/suno-vs-udio/`
- AIFlowReview Suno vs Udio 2025 — `aiflowreview.com/udio-vs-suno-2025/`
- Familypro Suno vs Udio 2025 — `familypro.io/en/blog/udio-vs-suno`
- Bandcamp Design Tutorial — `get.bandcamp.help/en/articles/15263106-bandcamp-design-tutorial`
- Jazzfuel Bandcamp case study — `jazzfuel.com/bandcamp-pages-case-study/`
- DontSleepGFX Bandcamp customization — `dontsleepgfx.com/blogs/marketing/bandcamp-customization-guide-headers-backgrounds-layouts`
- DistroKid indie review — `richardpryn.com/distrokid-review-an-honest-take-from-an-indie-musician/`
- Sound on Sound LANDR review — `soundonsound.com/reviews/landr-mastering-plugin`
- CDM LANDR review — `cdm.link/landr-ai-test/`
- Recording Magazine LANDR review — `recordingmag.com/landr-an-all-in-one-music-ecosystem/`
- Splice platform (Wikipedia) — `en.wikipedia.org/wiki/Splice_(platform)`
- wavesurfer.js docs — `wavesurfer.xyz/docs/`
- wavesurfer.js examples — `wavesurfer.xyz/examples/`
- BBC peaks.js — `github.com/bbc/peaks.js`
- Hesmondhalgh, Jones, Rauh (2019) — *SoundCloud and Bandcamp as Alternative Music Platforms*, Social Media + Society
- Spotify for Artists — `artists.spotify.com/en/home`
- Genius editing guide — `genius.com/Genius-how-to-add-songs-to-genius-annotated`
- LANDR blog lyrics on Spotify — `blog.landr.com/how-to-get-lyrics-on-spotify/`
- Spotify Wrapped design analysis — `uxchrisnguyen.medium.com/inside-spotify-wrapped-2025-data-culture-and-emotional-design-fdd18605c237`
- BandLab Sounds browse — `bandlab.com/sounds/browse`
- Suno creator's release cheat sheet (Matkowski, 2025) — `medium.com/@J.S.Matkowski/...`
- Local: `OneDrive/Hermes/albums/Half-Light-Hours/README.md` (the existing album delivery package).
- Local: `Documents/Projects/sonic-studio/DESIGN.md` (the design token system this memo defers to).
