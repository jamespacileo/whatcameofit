# Design

The local page reader remains first. activeTab capture is guarded by exact tab/window/URL, before and after capture, and excludes private or editing-sensitive contexts. Selected text prevents automatic capture. Pixels are cropped to primary visible media, resized with bounded JPEG output, and held only in memory. One image enters the existing reading call; record scoring remains text-only. No inference may treat the image claim as verified fact.

Local storage keeps ten successful answers for 24h with content fingerprints and checked-at dates. Visual fingerprints include the actual resized pixels, so canvas changes and same-URL media updates invalidate reuse; a local capture may be needed even on a cache hit. Search again bypasses reuse. Shared Cloudflare KV entries are keyed by a hash of the cleaned source URL and expire after 24h. Shared caching requires independent public source reading; mere possession of a permalink or screenshot is not proof that content is public. Reddit and other browser-only screenshots therefore work through the visual path and local reuse without being republished. No credentials, screenshots or report text enter cache or logs.

The source URL is separate from the website's fetch-url input. Metadata validation and bounded streaming JSON reads precede paid calls. No new browser host permissions are needed.
