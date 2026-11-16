## Preview lifecycle

- [x] Add `site/wrangler.preview.jsonc`: workers.dev only, no saved-results namespace, no lookup limits, no secrets.
- [x] Add `site/scripts/pr-preview.mjs` and `make pr-preview` / `make pr-preview-check`; refuse anything but a pull request number.
- [x] Add the `Pull request preview` workflow: publish on open and push, delete on close, one comment edited in place.
- [x] Describe previews in `docs/deploy.md`.
- [x] Open a pull request and confirm the preview is published, answers with `X-Robots-Tag: noindex`, and that `/api/lookup` answers "not set up".
- [x] Push to it and confirm the same Worker is replaced and the comment edited.
- [ ] Close it and confirm the Worker is deleted and the comment says so.
- [ ] Sync the `deployment` spec and archive this change.
