// Brand strings in one place. "thenwhat" remains the repo and package codename.
const env = globalThis.process?.env ?? {};

export const SITE = {
  name: "What came of it?",
  // The name as the wordmark sets it: a light lead and a heavy tail, where speech
  // puts the stress. Joined by a space they spell the name without its question
  // mark, which the wordmark draws itself so that its dot can be the blue marker.
  wordmark: ["What came", "of it"],
  // Where the built site is served: the one source for canonical addresses, the
  // sitemap, link previews and the browser extension's lookup. The local preview
  // until a domain is chosen; SITE_URL sets it at deployment.
  url: env.SITE_URL || "http://localhost:4321",
  tagline: "What happened to reported medical breakthroughs",
  description:
    "Each reported breakthrough gets a page showing where it stands now and the dated, sourced records that say so.",
  // Where a reader suggests a headline to track, and where they report an error on a
  // claim page. Each may be a `mailto:` address or the address of a public issue form,
  // and is chosen at deployment. Unset (null), no link to it is drawn. The environment
  // variables SUGGEST_URL and CORRECTIONS_URL override them, for tests and deployment.
  suggestUrl: env.SUGGEST_URL || null,
  correctionsUrl: env.CORRECTIONS_URL || null,
};
