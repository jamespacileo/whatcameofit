import { createHash } from "node:crypto";
import fs from "node:fs";

// Replacing the artwork must also change the URLs browsers cache for tabs,
// bookmarks, home-screen icons and shared cards. All remain first-party assets.
const revision = createHash("sha256")
  .update(fs.readFileSync("public/mark.svg"))
  .update(fs.readFileSync("public/favicon.svg"))
  .update(fs.readFileSync("scripts/brand-icons.mjs"))
  .digest("hex").slice(0, 12);

export const brandAsset = (file: string) => `${file}?v=${revision}`;

// The masthead's deep navy, which a browser or launcher may colour its own frame with.
export const THEME_COLOR = "#0b2545";
