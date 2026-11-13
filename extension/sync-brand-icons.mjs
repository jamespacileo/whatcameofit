// Refresh only generated Safari artwork; never regenerate signing or project settings.
// Run after Apple's converter, or independently after a brand update.
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const fromSite = createRequire(path.join(here, "../site/package.json"));
const { Resvg } = fromSite("@resvg/resvg-js");
const mark = fs.readFileSync(path.join(here, "../site/public/mark.svg"), "utf8");
const small = fs.readFileSync(path.join(here, "../site/public/favicon.svg"), "utf8");
const project = path.resolve(process.argv[2] || path.join(here, "safari/WhatCameOfIt"));
const png = (size) => new Resvg(size <= 32 ? small : mark, {
  fitTo: { mode: "width", value: size },
}).render().asPng();
let count = 0;
function walk(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const file = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walk(file);
    } else if (entry.name === "Contents.json" && path.basename(dir) === "AppIcon.appiconset") {
      const { images } = JSON.parse(fs.readFileSync(file, "utf8"));
      for (const image of images) {
        if (!image.filename) continue;
        const size = parseFloat(image.size) * parseFloat(image.scale || "1x");
        if (!Number.isFinite(size) || size <= 0) throw new Error(`Invalid icon size in ${file}`);
        fs.writeFileSync(path.join(dir, image.filename), png(size));
        count++;
      }
    } else if (entry.name === "Icon.png" && path.basename(dir) === "Resources") {
      fs.writeFileSync(file, png(512));
      count++;
    } else if (/^\d+\.png$/.test(entry.name) && path.basename(dir) === "icons") {
      fs.writeFileSync(file, png(parseInt(entry.name, 10)));
      count++;
    }
  }
}
walk(project);
console.log(`Updated ${count} Safari artwork files in ${project}`);
