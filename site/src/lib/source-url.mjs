// A source address is context, not permission to fetch or publish browser content.
export function publicWebUrl(value) {
  try {
    const url = new URL(value);
    if (!/^https?:$/.test(url.protocol) || url.username || url.password || url.port ||
        !url.hostname.includes(".") || /(^|\.)(localhost|local|internal|test)$/.test(url.hostname) ||
        /^[\d.]+$/.test(url.hostname) || url.hostname.includes(":")) return null;
    return url;
  } catch { return null; }
}

export function sourceUrl(value) {
  const url = publicWebUrl(value);
  if (!url) return null;
  // Do not collapse distinct query-addressed pages into the same cached answer.
  // Unknown parameters may also be private tokens: omit this URL entirely.
  for (const [key, value] of [...url.searchParams]) {
    if (/^(utm_.+|fbclid|gclid|ref|ref_src|share_id)$/i.test(key)) url.searchParams.delete(key);
    else if (!/^(id|p|article|story)$/.test(key) || !/^\d+$/.test(value)) return null;
  }
  url.searchParams.sort();
  url.hash = "";
  return url.href.length <= 1000 ? url.href : null;
}
