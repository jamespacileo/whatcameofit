// The digest of the code that writes what the Worker makes, as the build worked it out
// (scripts/renderer-digest.mjs, run by astro.config.mjs). A build without it stops: a frame
// with no digest would let a page keep its tag across a change to its words.
export function rendererDigest(): string {
  const digest = process.env.PAIRS_RENDERER_DIGEST;
  if (!digest) throw new Error("PAIRS_RENDERER_DIGEST is not set: astro.config.mjs works it out before any page is built.");
  return digest;
}
