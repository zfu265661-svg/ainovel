# Story Bible And Agent State

## Purpose

The Story Bible and companion files hold long-term creative state that should not depend on prompt memory. Phase 3 MVP creates and loads these files, uses them in context assembly, and reports their health in status diagnostics.

## Files

- `story_bible.json`: world, era background, core settings, rules, themes, conflicts, taboos, and high-level style notes.
- `plot_threads.json`: main and side threads, active/resolved status, related characters and locations.
- `locations.json`: places, aliases, current state, rules, and related characters/organizations.
- `organizations.json`: factions, goals, members, relationships, and appearances.
- `style_guide.json`: voice, pacing, tone, forbidden patterns, and notes.
- `scenes.json`: planned scene interface; not the default writing unit yet.

## Loader Semantics

`core/story_bible_service.py` returns default empty structures when these files are missing, so old projects can still run. If a file exists but is not a JSON object, the loader raises a clear error.

## Commit Semantics

These enhanced files are not modified by `commit_suggestion()` in Phase 3 MVP. They can be read into context and inspected by status, but LLM output must not directly overwrite them until review/commit support is explicitly implemented and tested.

## Context Semantics

`build_chapter_context()` includes compact, targeted slices:

- Story Bible essentials
- active plot threads
- matching locations and organizations
- style guide
- scenes for the current chapter
- `context_audit`, which records why context was selected

