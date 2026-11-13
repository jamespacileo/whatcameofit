# Extension test corpus

Real pages a reader might open the extension on, with what the popup should do on each, and what the lookup service answered when last tested. The Google Sheet "Extension test URLs" (Drive folder `thenwhat`) is built from this folder and is read-only in practice: the next sync replaces it.

## Add rows

Append rows to `urls.csv`. Leave `id` empty: the next sync gives the row the next number in its group.

| Column | What to write |
| --- | --- |
| `group` | `Social` (a post), `Article`, `Negative` (a page that should not be read as a treatment report, or an edge case), or `Tracked` (an article the site already tracks) |
| `page_type` | The kind of page, e.g. `Threads post`, `Paywalled news (FT)`, `Regulator press release (FDA)` |
| `url` | The page's address, without tracking parameters. Only addresses you have seen on the live web. |
| `outlet` | Platform or publisher |
| `intervention_condition` | Treatment and condition, short |
| `expected_answer` | Start with `claim found -> registry search`, `no claim`, or `edge:` plus a few words. `no claim` and `edge` rows are judged differently. |
| `source_of_row` | `web research, page opened`, `web research, not opened`, or `repo seed / test brief` |
| `notes` | Anything a tester should know |

Multiple plausible trial candidates with confidence scores and reasons are a valid registry-search result.

Never paste article text into any file here. A per-row observation goes in `notes.json`, keyed by id. A verdict a person decided goes in `verdicts.json` as `[result, reason]`.

## Sync

```sh
sh extension/test-corpus/sync.sh
```

This checks new addresses once, matches every address against the public `lookup.json`, rebuilds the workbook in `.work/`, and replaces the Google Sheet through the `gdrive` rclone remote. `UPLOAD=0` skips the upload.

To fill in lookup answers for new rows, start the service in another terminal and run with `LOOKUPS=1`:

```sh
make lookup-dev
```

```sh
LOOKUPS=1 sh extension/test-corpus/sync.sh
```

Each search is a paid model call, capped by the service's monthly budget, and the service allows five a minute, so new rows take about 13 seconds each. Answers are kept in `.work/results.json` and never asked again.

## Posts and refused pages

The service cannot read posts on X, Reddit, LinkedIn, TikTok, YouTube, Threads, Facebook or Instagram by address, and some sites refuse it. The extension reads those pages in the reader's browser. To test one, open it in a browser, read it as `extension/src/open-page.js` does, and save `{id: {text, links, platform, pageUrl}}` to a file outside the repository (it holds page text). Then:

```sh
node extension/test-corpus/lookups.mjs --browser /path/to/inputs.json
```

Delete the inputs file afterwards.
