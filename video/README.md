# Video

Remotion project for explainer videos about the site and its browser extension. One project, one folder per video under `videos/<name>/`.

## The explainer

`videos/what-came-of-it-explainer/`, about 1 min 52 s, seven scenes: the headlines, a claim page, its records, how a status is set, the link lookup, the extension, the close.

| Composition | Size | For |
|---|---|---|
| `WhatCameOfItExplainer` | 3840 × 2160 | YouTube, the site's docs |
| `WhatCameOfItExplainerVertical` | 2160 × 3840 | Social posts |
| `Thumbnail16x9`, `Thumbnail4x3`, `Thumbnail9x16` | stills | Covers |

## Run

```sh
cd video
npm ci
uv run --with edge-tts python3 scripts/narrate.py videos/what-came-of-it-explainer   # narration audio, not committed
uv run --with numpy python3 scripts/music.py videos/what-came-of-it-explainer        # background track, not committed
npm run studio                                                                        # preview at http://localhost:3123
```

Render (add `--scale=0.5` for 1080p):

```sh
V=videos/what-came-of-it-explainer
npx remotion render src/remotion/index.ts WhatCameOfItExplainer $V/output.mp4 --public-dir $V/ --video-bitrate 16M
npx remotion render src/remotion/index.ts WhatCameOfItExplainerVertical $V/output_vertical.mp4 --public-dir $V/ --video-bitrate 16M
npx remotion still src/remotion/index.ts Thumbnail16x9 $V/thumbnail_remotion_16x9.png --public-dir $V/
```

The render carries narration only. Lay the music under it afterwards:

```sh
ffmpeg -i $V/output.mp4 -i $V/bgm.wav -filter_complex "[0:a]volume=1.5[a1];[1:a]volume=0.11[a2];[a1][a2]amix=inputs=2:duration=first:normalize=0[aout]" -map 0:v -map "[aout]" -c:v copy -c:a aac -b:a 192k $V/final_video.mp4
```

The method page shows a 1080p copy, which is committed. After a new final render, replace it:

```sh
ffmpeg -i $V/final_video.mp4 -vf scale=1920:1080:flags=lanczos -c:v libx264 -preset slow -crf 25 -pix_fmt yuv420p -c:a aac -b:a 128k -movflags +faststart ../site/public/video/explainer.mp4
```

Captions are drawn into the picture. To leave them out and upload `podcast_audio.srt` beside the video instead, add `--props='{"showCaptions":false}'`.

## How it is put together

- `videos/<name>/podcast.txt` is the script. `[SECTION:name]` starts a scene; `{spoken|shown}` says one thing and captions another.
- `scripts/narrate.py` speaks it with Edge TTS and writes `podcast_audio.wav`, `timing.json`, `captions.json` and `podcast_audio.srt`. The script's text is sent to Microsoft's speech service; it holds nothing private.
- `scripts/music.py` writes `bgm.wav`. The track is synthesised note by note in that script: no recording, sample or library is behind it, so it has no licence to check and belongs to the project.
- Scenes time themselves by the words: `at("a trial registered")` is the frame where the narrator says it. A changed script needs a new narration and no new numbers; a phrase that is no longer spoken fails the render by name.
- `src/remotion/brand/` restates the site's visual system (`DESIGN.md`): tokens, the wordmark, the stage track, motion. `src/remotion/scenes/` holds one file per scene.

## Rules for a video

The site's guardrails hold here too.

- Every record shown is copied from the published export and the site's own wording, in `src/remotion/scenes/claim-data.ts`, with the date the registries were checked. Update it when those claims change.
- A headline is the outlet's own title, in quotation marks with the outlet named. Article text is never shown; an article is drawn as bars.
- No verdict wording, no colour for a status, no medical advice. "Not medical advice" stays on screen.
- The registry-search result in the extension scene is a drawing of the layout, with bars for record titles: the video names no record it did not look up.
- No user numbers, press or testimonials, and no store listing for the extension until one exists.
