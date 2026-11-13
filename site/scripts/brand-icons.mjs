// Draws the site's raster icons from the mark, so a change to it reaches every size.
// public/mark.svg is the mark; public/favicon.svg is the same mark drawn for a browser
// tab, where it is 16 to 32 pixels: the glass runs to the tile's edges and the capsule
// has no gap between its halves. Run after editing either:
//   node site/scripts/brand-icons.mjs
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { Resvg } from "@resvg/resvg-js";

const here = path.dirname(fileURLToPath(import.meta.url));
const pub = path.join(here, "..", "public");
const mark = fs.readFileSync(path.join(pub, "mark.svg"), "utf8");
// A phone or a launcher cuts its own corners, so it is given the tile with none cut:
// the same drawing on a square of the tile's colour.
const square = mark.replace('rx="14"', 'rx="0"');
if (square === mark) throw new Error("mark.svg no longer has the rounded tile this script squares off");

const png = (svg, size) => new Resvg(svg, { fitTo: { mode: "width", value: size } }).render().asPng();
const files = {
  "favicon-48.png": png(mark, 48),
  "icon-192.png": png(mark, 192),
  "icon-512.png": png(mark, 512),
  "icon-maskable-512.png": png(square, 512),
  "apple-touch-icon.png": png(square, 180),
};
for (const [name, bytes] of Object.entries(files)) {
  fs.writeFileSync(path.join(pub, name), bytes);
  console.log(`${name} ${bytes.length} bytes`);
}
