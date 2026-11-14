# Preserve extension corpus lookup history

## Why

Removing the corpus worktree deleted its local lookup cache. Historical paid responses survived in temporary files, but rebuilding the shared worksheet required recovering them manually.

## What changes

- Keep URL checks and complete lookup responses in a persistent user-data directory outside worktrees.
- Import surviving legacy cache files and reuse responses by page URL and reading mode.
- Use locked, atomic updates so concurrent worktrees preserve each other's results.
- Keep generated workbook files local and preserve the existing explicit opt-in for paid lookups.

## Impact

The corpus check, assembly and lookup scripts share the durable cache.
