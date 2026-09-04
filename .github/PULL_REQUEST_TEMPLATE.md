## What does this PR do?

A 1-2 sentence summary. The diff will tell the rest.

## Type of change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would change existing behavior)
- [ ] Documentation update
- [ ] Refactor (no functional change)
- [ ] Theme / visual change

## How did you verify it?

- [ ] Manual visual check (CDP + screenshot)
- [ ] Tests pass (`python -m pytest`)
- [ ] E2E pass (`python e2e/run_all.py`)
- [ ] No new warnings / console errors
- [ ] Theme switching still works (6 themes verified)
- [ ] Keyboard shortcuts still work (15 shortcuts verified)

## Screenshots / recordings

If this is visual, attach before/after. **Required** for any UI change.

## CATCH-UP.md update

If you added/changed a behavior, did you also update [CATCH-UP.md](./CATCH-UP.md)? It is the source of truth for future LLM sessions.

## Breaking changes

If you checked "Breaking change" above, describe:
- What breaks
- Migration path
- Why it's necessary

## Related issues

Link any related issues with `Closes #123` or `Refs #456`.

## Self-review checklist

- [ ] I tested my changes in at least one theme (default: Mixtape '85)
- [ ] I did not introduce any secrets (API keys, tokens, etc.)
- [ ] I did not break the cassette visual (no overlays on the sticker image)
- [ ] I did not put `shuffle` before play controls
- [ ] I did not use text labels for ±15s buttons (use `⟲`/`⟳` glyphs)
- [ ] I did not use a square cassette slot (78×46 ratio)
- [ ] I did not change the sleep-timer icon to a number
