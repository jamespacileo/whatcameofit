// Draws the site's raster icons from the mark, so a change to it reaches every size.
// public/mark.svg is the mark: the glass is one outline (ring, handle, and a small arc
// in each corner where they meet) over a white lens, on the tile. public/favicon.svg is
// the same mark drawn for a browser tab, where it is 16 to 32 pixels: the glass runs to
// the tile's edges, and the capsule's seam and flat edges fall on whole pixels at 32.
// Run after editing either:
//   node site/scripts/brand-icons.mjs
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { Resvg } from "@resvg/resvg-js";
import satori from "satori";
import { SITE } from "../site.config.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const pub = path.join(here, "..", "public");
const mark = fs.readFileSync(path.join(pub, "mark.svg"), "utf8");
const small = fs.readFileSync(path.join(pub, "favicon.svg"), "utf8");
// A phone or a launcher cuts its own corners, so it is given the tile with none cut:
// the same drawing on a square of the tile's colour.
const square = mark.replace('rx="16"', 'rx="0"');
if (square === mark) throw new Error("mark.svg no longer has the rounded tile this script squares off");

const png = (svg, size) => new Resvg(svg, { fitTo: { mode: "width", value: size } }).render().asPng();
// Keep the entire symbol inside a launcher's central 80% safe circle.
const maskable = square.replace('<g id="symbol">', '<g id="symbol" transform="translate(7.68 7.68) scale(0.76)">');
const files = {
  "favicon-48.png": png(small, 48),
  "icon-192.png": png(mark, 192),
  "icon-512.png": png(mark, 512),
  "icon-maskable-512.png": png(maskable, 512),
  "apple-touch-icon.png": png(square, 180),
};
for (const [name, bytes] of Object.entries(files)) {
  fs.writeFileSync(path.join(pub, name), bytes);
  console.log(`${name} ${bytes.length} bytes`);
}

// Conventional browser/bookmark fallback, with a crisp image at each tab size.
const sizes = [16, 32, 48];
const frames = sizes.map((size) => png(small, size));
const header = Buffer.alloc(6 + sizes.length * 16);
header.writeUInt16LE(1, 2);
header.writeUInt16LE(sizes.length, 4);
let offset = header.length;
frames.forEach((frame, i) => {
  const entry = 6 + i * 16;
  header[entry] = header[entry + 1] = sizes[i];
  header.writeUInt16LE(1, entry + 4);
  header.writeUInt16LE(32, entry + 6);
  header.writeUInt32LE(frame.length, entry + 8);
  header.writeUInt32LE(offset, entry + 12);
  offset += frame.length;
});
fs.writeFileSync(path.join(pub, "favicon.ico"), Buffer.concat([header, ...frames]));

// Vector variants for print, external branding and operating-system masking.
fs.writeFileSync(path.join(pub, "mark-square.svg"), square);
const symbol = mark.replace(/  <rect id="tile"[^>]+\/>\n/, "");
fs.writeFileSync(path.join(pub, "mark-symbol.svg"), symbol);
// For the navy masthead: no tile, the glass in white with the navy showing through the
// lens, the capsule in its own colours. Cropped to the drawing, so it sits at the size
// the tile did.
const reverse = symbol
  .replace('viewBox="0 0 64 64"', 'viewBox="8 8 48 48"')
  .replace(/    <circle id="lens"[^>]+\/>\n/, "")
  .replaceAll("#16477d", "#ffffff");
if (reverse.includes('id="lens"') || !reverse.includes('<path id="glass" fill="#ffffff"')) throw new Error("mark.svg no longer has the lens and glass this script reverses");
fs.writeFileSync(path.join(pub, "mark-reverse.svg"), reverse);
fs.writeFileSync(path.join(pub, "mark-monochrome.svg"), symbol.replaceAll("#16477d", "#152d49").replaceAll("#f28a62", "#152d49").replaceAll("#1687da", "#152d49"));

// Satori embeds the Figtree lettering as vector paths, so exported logos need no fonts.
const fonts = [400, 700].map((weight) => ({
  name: "Figtree", weight, style: "normal",
  data: fs.readFileSync(path.join(here, `../node_modules/@fontsource/figtree/files/figtree-latin-${weight}-normal.woff`)),
}));
const lockup = await satori({ type: "div", props: {
  style: { display: "flex", alignItems: "center", width: 1200, height: 280, fontFamily: "Figtree", color: "#152d49" },
  children: [
    { type: "img", props: { src: `data:image/svg+xml;base64,${Buffer.from(mark).toString("base64")}`, width: 240, height: 240 } },
    { type: "div", props: { style: { display: "flex", flexDirection: "column", marginLeft: 28 }, children: [
      { type: "div", props: { style: { display: "flex", fontSize: 76 }, children: [
        { type: "span", props: { children: SITE.wordmark[0] + " " } },
        { type: "span", props: { style: { fontWeight: 700, marginLeft: 18 }, children: SITE.wordmark[1] + "?" } },
      ] } },
      { type: "div", props: { style: { fontSize: 33, color: "#586778", marginTop: 16 }, children: SITE.tagline } },
    ] } },
  ],
} }, { width: 1200, height: 280, fonts });
fs.writeFileSync(path.join(pub, "brand-lockup.svg"), lockup);
fs.writeFileSync(path.join(pub, "brand-lockup.png"), png(lockup, 1200));
