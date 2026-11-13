// Capture runs only while the popup is open. Images remain in memory.
import { publicWebUrl, sourceUrl } from "../../site/src/lib/source-url.mjs";
export { publicWebUrl, sourceUrl as publicPageUrl };
export function inspectVisible() {
  const roots = [document];
  for (let i = 0; i < roots.length && i < 40; i++) {
    for (const node of [...roots[i].querySelectorAll("*")].slice(0, 3000)) {
      if (node.shadowRoot) roots.push(node.shadowRoot);
    }
  }
  const visible = node => {
    const r = node.getBoundingClientRect();
    const style = getComputedStyle(node);
    return r.width > 0 && r.height > 0 && r.bottom > 0 && r.right > 0 && r.top < innerHeight && r.left < innerWidth && style.visibility !== "hidden" && style.display !== "none";
  };
  const sensitive = roots.some(root => [...root.querySelectorAll('input, textarea, [contenteditable]')]
    .some(node => visible(node) && (node.type === "password" ||
      !["checkbox", "radio", "range", "button", "submit", "reset", "search", "hidden"].includes(node.type) && node.value ||
      node.isContentEditable && (node.innerText.trim() || node.matches(":focus-within")))));
  const focus = document.querySelector('shreddit-post, article, [role="article"], main') ?? document.body;
  const media = roots.flatMap(root => [...root.querySelectorAll("img, video, canvas")])
    .filter(node => visible(node) && (focus.contains(node) || node.getRootNode() !== document))
    .map(node => {
      const r = node.getBoundingClientRect();
      const left = Math.max(0, r.left), top = Math.max(0, r.top);
      return { left, top, width: Math.min(innerWidth, r.right) - left, height: Math.min(innerHeight, r.bottom) - top,
        kind: node.tagName.toLowerCase(), identity: node.currentSrc || node.src || "", time: node.currentTime ?? null };
    }).filter(r => r.width >= 120 && r.height >= 80).sort((a, b) => b.width * b.height - a.width * a.height);
  // An embedded document may contain credentials that this document cannot inspect.
  // Refuse only frames overlapping the pixels we would send, not unrelated adverts.
  const crop = media[0] ?? { left: 0, top: 0, width: innerWidth, height: innerHeight };
  const embedded = roots.some(root => [...root.querySelectorAll("iframe")].some(frame => {
    if (!visible(frame)) return false;
    const r = frame.getBoundingClientRect();
    return r.left < crop.left + crop.width && r.right > crop.left && r.top < crop.top + crop.height && r.bottom > crop.top;
  }));
  return { address: location.href, sensitive, embedded, hidden: document.hidden,
    width: innerWidth, height: innerHeight, crop: media[0] ?? null,
    media: media.slice(0, 5), selectionOnly: String(getSelection() ?? "").trim().length >= 20 };
}

const failure = code => Object.assign(new Error(code), { code });

/** Guard active-tab capture: captureVisibleTab takes a window, not a tab ID. */
export async function capturePage(api, tab, signal, encode = resizeCapture) {
  if (!publicWebUrl(tab.url) || tab.incognito || !api.tabs.captureVisibleTab) throw failure("capture_unavailable");
  let changed = false;
  const activated = info => { if (info.windowId === tab.windowId && info.tabId !== tab.id) changed = true; };
  const updated = (id, info) => { if (id === tab.id && (info.url || info.status === "loading")) changed = true; };
  api.tabs.onActivated?.addListener(activated);
  api.tabs.onUpdated?.addListener(updated);
  async function check() {
    if (signal?.aborted || changed) throw failure("page_changed");
    const [active] = await api.tabs.query({ active: true, windowId: tab.windowId });
    if (!active || active.id !== tab.id || active.windowId !== tab.windowId || active.url !== tab.url || active.incognito) throw failure("page_changed");
  }
  async function inspect() {
    const [{ result }] = await api.scripting.executeScript({ target: { tabId: tab.id }, func: inspectVisible });
    if (result.address !== tab.url || result.hidden) throw failure("page_changed");
    if (result.sensitive) throw failure("capture_sensitive");
    if (result.embedded) throw failure("capture_embedded");
    return result;
  }
  try {
    await check();
    const before = await inspect();
    const dataUrl = await api.tabs.captureVisibleTab(tab.windowId, { format: "jpeg", quality: 85 });
    await check();
    const after = await inspect();
    const bounds = crop => crop && [crop.left, crop.top, crop.width, crop.height, crop.kind, crop.identity];
    if (JSON.stringify(bounds(before.crop)) !== JSON.stringify(bounds(after.crop)) || before.width !== after.width || before.height !== after.height) throw failure("page_changed");
    const image = await encode(dataUrl, before);
    await check();
    return { image, pageUrl: sourceUrl(tab.url) };
  } finally {
    api.tabs.onActivated?.removeListener(activated);
    api.tabs.onUpdated?.removeListener(updated);
  }
}

export async function resizeCapture(dataUrl, visible) {
  const image = new Image();
  image.src = dataUrl;
  await image.decode();
  const sx = image.naturalWidth / visible.width, sy = image.naturalHeight / visible.height;
  const crop = visible.crop ?? { left: 0, top: 0, width: visible.width, height: visible.height };
  const width = Math.min(image.naturalWidth, crop.width * sx), height = Math.min(image.naturalHeight, crop.height * sy);
  const scale = Math.min(1, 1600 / Math.max(width, height), Math.sqrt(1_000_000 / (width * height)));
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.floor(width * scale));
  canvas.height = Math.max(1, Math.floor(height * scale));
  canvas.getContext("2d").drawImage(image, crop.left * sx, crop.top * sy, width, height, 0, 0, canvas.width, canvas.height);
  const result = canvas.toDataURL("image/jpeg", 0.82);
  if (result.length > 1_000_000) throw failure("image_too_large");
  return { dataUrl: result, width: canvas.width, height: canvas.height };
}

/** Only a digest of reading inputs is retained, never their text or pixels. */
export async function fingerprint(value) {
  const hash = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(JSON.stringify(value)));
  return [...new Uint8Array(hash)].map(byte => byte.toString(16).padStart(2, "0")).join("");
}
