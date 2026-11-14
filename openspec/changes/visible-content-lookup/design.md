# Design

The local page reader remains first. activeTab capture is guarded by exact tab/window/URL, before and after capture, and excludes private or editing-sensitive contexts. Selected text prevents automatic capture. Pixels are cropped to primary visible media, resized with bounded JPEG output, and held only in memory. One image enters the existing reading call; record scoring remains text-only. No inference may treat the image claim as verified fact.

Local storage keeps ten successful answers for 24h with content fingerprints and checked-at dates. Visual fingerprints include the actual resized pixels, so canvas changes and same-URL media updates invalidate reuse; a local capture may be needed even on a cache hit. Search again bypasses reuse. Shared Cloudflare KV entries are keyed by a hash of the cleaned source URL and expire after 24h. Shared caching requires independent public source reading; mere possession of a permalink or screenshot is not proof that content is public. Reddit and other browser-only screenshots therefore work through the visual path and local reuse without being republished. No credentials, screenshots or report text enter cache or logs.

The source URL is separate from the website's fetch-url input. Metadata validation and bounded streaming JSON reads precede paid calls. No new browser host permissions are needed.

## Slow article lookup correction (14 November 2026)

The ScienceAlert tinnitus report reproduced a 32.8-second production lookup. Removing only the public page URL while retaining its paper links still took 31.9 seconds; removing those paper links reduced the same text lookup to 2.7 seconds. The model identified the text as not reporting a specific treatment. A deterministic reproduction showed that `lookUp` nevertheless waited indefinitely for a linked-paper or stated-record request. The installed Safari app also has no overall search deadline.

Return a non-treatment identification as soon as it is available while preserving overlap of useful requests for treatment reports. Bound publisher reads at ten seconds total and optional independent proof at three seconds, paper requests at five seconds, and registry requests at ten seconds including bodies. A failed public proof retains browser text and never authorizes sharing. A failed registry request remains a failure rather than a successful empty result.

Give each popup lookup one 45-second attempt deadline, including automatic visual fallback. Use shorter deadlines for the index (five seconds) and shared-cache probe (1.5 seconds). Attempt cancellation must prevent stale rendering, storage writes and subsequent requests while allowing an explicit retry with a fresh signal. Existing consent and screenshot rules remain in force. Do not automatically retry paid requests.
