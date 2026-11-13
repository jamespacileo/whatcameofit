// Outlet icons. The pipeline fetched each one from the outlet's own site and the
// export carries the image itself, so the build writes it as a file of this site
// and no page asks another host for anything.
import { data } from "./export";

const EXTENSIONS: Record<string, string> = {
  "image/png": "png",
  "image/x-icon": "ico",
  "image/gif": "gif",
  "image/jpeg": "jpg",
  "image/webp": "webp",
};

export interface OutletIcon {
  /** File name under /outlet-icons/. */
  file: string;
  mediaType: string;
  bytes: Buffer;
}

/** An article's host without a leading www: what the page shows and the export keys icons by. */
export function outletDomain(url: string): string {
  return URL.canParse(url) ? new URL(url).hostname.replace(/^www\./, "") : "";
}

const icons = new Map<string, OutletIcon>();
for (const outlet of data.outlets) {
  const [, mediaType, encoded] = outlet.icon.match(/^data:([^;]+);base64,(.+)$/) ?? [];
  const extension = EXTENSIONS[mediaType ?? ""];
  if (!extension || !encoded) continue;
  icons.set(outlet.domain, {
    file: `${outlet.domain}.${extension}`,
    mediaType,
    bytes: Buffer.from(encoded, "base64"),
  });
}

export const outletIcons = [...icons.values()];

/**
 * This site's own address of an outlet's icon, when the export has one. A subdomain
 * with none of its own shows its nearest parent's: ca.news.example.com falls back
 * to news.example.com, then example.com.
 */
export function outletIconPath(domain: string): string | undefined {
  const labels = domain.split(".");
  for (let start = 0; labels.length - start >= 2; start++) {
    const icon = icons.get(labels.slice(start).join("."));
    if (icon) return `/outlet-icons/${icon.file}`;
  }
  return undefined;
}
