// Writes the extension to extension/dist: the popup, the address comparison shared
// with the site, the site's face and icon, and a manifest that names the site's address.
//
//   node extension/build.mjs          the extension as it is loaded or packaged
//   node extension/build.mjs --dev    also writes states.html, every popup state side by side
import fs from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const site = path.join(here, "..", "site");
const dist = path.join(here, "dist");
const fromSite = createRequire(path.join(site, "package.json"));

const { SITE } = await import(pathToFileURL(path.join(site, "site.config.mjs")).href);
const origin = new URL(SITE.url).origin;

fs.rmSync(dist, { recursive: true, force: true });
fs.mkdirSync(path.join(dist, "icons"), { recursive: true });

for (const name of fs.readdirSync(path.join(here, "src"))) {
  fs.copyFileSync(path.join(here, "src", name), path.join(dist, name));
}
// One comparison function for the site and the extension.
fs.copyFileSync(path.join(site, "src/lib/article-key.mjs"), path.join(dist, "article-key.js"));
// And the site's own readers and wording for a registry search of the open page: how an
// address is told from a post, how a page is read, and how an answer is worded. Each is
// copied with the names of the files it imports changed to the copies beside it.
const shared = [
  ["src/lib/lookup-match.mjs", "lookup-match.js", [["./article-key.mjs", "./article-key.js"]]],
  ["src/lib/live-lookup.mjs", "live-lookup.js", [["./notices.ts", "./notices.js"]]],
  ["worker/page.mjs", "page.js", []],
];
for (const [from, to, imports] of shared) {
  let source = fs.readFileSync(path.join(site, from), "utf8");
  for (const [theirs, ours] of imports) {
    if (!source.includes(`"${theirs}"`)) throw new Error(`${from} no longer imports ${theirs}`);
    source = source.replaceAll(`"${theirs}"`, `"${ours}"`);
  }
  fs.writeFileSync(path.join(dist, to), source);
}
const { NOTICES } = await import(pathToFileURL(path.join(site, "src/lib/notices.ts")).href);
fs.writeFileSync(
  path.join(dist, "notices.js"),
  `// Written by build.mjs from site/src/lib/notices.ts.\nexport const NOTICES = ${JSON.stringify(NOTICES)};\n`,
);

const face = path.dirname(fromSite.resolve("@fontsource-variable/figtree/package.json"));
fs.copyFileSync(path.join(face, "files/figtree-latin-wght-normal.woff2"), path.join(dist, "figtree.woff2"));
fs.copyFileSync(path.join(face, "LICENSE"), path.join(dist, "figtree-LICENSE.txt"));

fs.writeFileSync(
  path.join(dist, "config.js"),
  `// Written by build.mjs from site/site.config.mjs.\nexport const SITE = ${JSON.stringify({ name: SITE.name, url: origin })};\n`,
);

const { Resvg } = fromSite("@resvg/resvg-js");
const mark = fs.readFileSync(path.join(site, "public/favicon.svg"));
const sizes = [16, 32, 48, 96, 128, 256];
for (const size of sizes) {
  const image = new Resvg(mark, { fitTo: { mode: "width", value: size } }).render();
  fs.writeFileSync(path.join(dist, "icons", `${size}.png`), image.asPng());
}
const icons = Object.fromEntries(sizes.map((size) => [size, `icons/${size}.png`]));

const manifest = {
  manifest_version: 3,
  name: SITE.name,
  version: "0.1.0",
  description: "See what happened to the medical breakthrough in the article you are reading.",
  icons,
  action: {
    default_title: "What happened to this breakthrough?",
    default_popup: "popup.html",
    default_icon: icons,
  },
  // The current tab only, and only when the button is pressed. "scripting" lets the
  // popup read that tab's page when the reader asks for a registry search. The site's
  // own address is the one place the extension may fetch from or send to.
  permissions: ["activeTab", "scripting", "storage"],
  host_permissions: [`${origin}/*`],
};
fs.writeFileSync(path.join(dist, "manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);

if (process.argv.includes("--dev")) {
  fs.copyFileSync(path.join(here, "dev/states.html"), path.join(dist, "states.html"));
  fs.copyFileSync(path.join(here, "dev/states.js"), path.join(dist, "states.js"));
}

console.log(`Wrote ${path.relative(process.cwd(), dist)} for ${origin}.`);
