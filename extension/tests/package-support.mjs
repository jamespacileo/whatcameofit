import { readFile } from "node:fs/promises";

export const dist = new URL("../dist/", import.meta.url);
export const manifest = JSON.parse(await readFile(new URL("manifest.json", dist), "utf8"));
export const { SITE } = await import(new URL("config.js", dist));

let launch = 0;
export function launchEntry(url) {
  const entry = new URL(url);
  // Reopen the entry point while sharing the package's imported dependencies.
  entry.searchParams.set("launch", String(++launch));
  return import(entry.href);
}

export function installGlobals(t, globals) {
  for (const [name, value] of Object.entries(globals)) {
    const previous = Object.getOwnPropertyDescriptor(globalThis, name);
    Object.defineProperty(globalThis, name, { configurable: true, writable: true, value });
    t.after(() => {
      if (previous) Object.defineProperty(globalThis, name, previous);
      else delete globalThis[name];
    });
  }
}
