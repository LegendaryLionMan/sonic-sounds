# Penpot Fix Log — 2026-08-05

## What was broken

When I committed `35ab3ae` (cassette-mesh rebuild), I thought the 6 PNGs were uploaded to Penpot. **They weren't.** The plugin's `penpotUtils.importImage()` calls returned `ok: true` with what looked like the cassette-mesh dimensions, but the rectangles in Penpot were still showing the OLD Editorial Zine PNGs.

## Root cause

Two bugs compounding:

1. **nginx response cache.** Penpot's plugin iframe fetched `/album-studio-b64/01-design-system.b64` but nginx was returning the OLD Editorial Zine b64 (582,260 chars) instead of the cassette-mesh b64 (1,728,540 chars). Even after `nginx -s reload`, the cache persisted. **Solution: append a unique `?v=N` cache-buster to every fetch URL.**

2. **Penpot v2.16 plugin API doesn't expose shape mutability.** Setting `rect.x`, `rect.y`, `rect.hidden`, `rect.opacity`, `rect.fills`, `rect.parentIndex` are all silently ignored — only `rect.resize()` works. There's no `removeShape`, no `appendChild` (for reordering), no delete. **Solution: create new shapes with unique names so Penpot treats them as new, and accept that old shapes remain stacked underneath.**

## What I did

1. Re-encoded the 6 cassette-mesh PNGs into b64 (correct sizes: 1,728,540 / 1,169,820 / 857,916 / 1,676,180 / 1,860,060 / 3,619,384).
2. Copied to nginx `/tmp/album-studio-b64/` and reloaded nginx.
3. Re-imported all 6 PNGs via MCP with `?v={nonce}` cache-buster. **Each now has the correct cassette-mesh dimensions** (2850×3690, 2880×2544, 2880×3368, 2850×3500, 2880×1664, 2850×3362).
4. Created a new design token set `album-studio/cassette-mesh` with 24 tokens (10 colors in hex, 6 font sizes, 5 spacings, 2 border radii). Used hex instead of hsl because Penpot tokens reject hsl format.
5. Tried to clean up duplicates via `rect.x = -50000` — but that setter is silently ignored.

## Current Penpot state (after fix)

```
01 — Design System:    4 rects total.  2 cassette-mesh at z-top, 2 Editorial Zine stacked under.
02 — Components:       4 rects total.  2 cassette-mesh at z-top, 2 Editorial Zine stacked under.
03 — Intake:           6 rects total.  3 cassette-mesh at z-top, 3 Editorial Zine/test-artifacts under.
04 — Dashboard:        4 rects total.  2 cassette-mesh at z-top, 2 Editorial Zine stacked under.
05 — Cover Exploration: 5 rects total. 2 cassette-mesh at z-top, 3 Editorial Zine/test under.
06 — Motif Library:    5 rects total.  2 cassette-mesh at z-top, 3 Editorial Zine under.
```

The cassette-mesh is the TOP-most rectangle on every page, so visually the user sees cassette-mesh. But the OLD rectangles still exist underneath in case the user undoes or the z-order changes.

## Lessons captured

- **Always append `?v=N` to nginx-fetch URLs in the plugin** — nginx has a response cache that survives reloads.
- **Penpot v2.16 plugin API: `resize()` is the only mutator that works.** Everything else is silently ignored.
- **Penpot tokens: hex/rgb only, no hsl.**
- **To delete shapes in Penpot via plugin: not possible.** User must do it manually in browser, OR rebuild the page from scratch.

## What's still manual in the browser

1. Open the file `album-studio-design` in Penpot.
2. For each of the 6 pages, delete the Editorial Zine rectangles (they're underneath the cassette-mesh; if user undoes, the OLD layer appears).
3. The duplicate cassette-mesh rectangles can be deleted too.
4. Delete the old `album-studio/design-system` token set (the new `album-studio/cassette-mesh` set is the one to use).

Alternatively, the user can also accept the layered state — visually it looks correct because cassette-mesh is on top.
