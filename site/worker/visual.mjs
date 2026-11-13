// Bounded visual input. No remote image fetches, files, persistence or diagnostics.
export const MAX_IMAGE_BYTES = 750_000;
const MAX_BODY_BYTES = 1_100_000;
const invalid = (code = "image_invalid", status = 400) => Object.assign(new Error(code), { code, status });

export async function readBody(request) {
  if (Number(request.headers.get("content-length")) > MAX_BODY_BYTES) throw invalid("too_long", 413);
  const reader = request.body?.getReader();
  if (!reader) return null;
  const chunks = [];
  let length = 0;
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      length += value.byteLength;
      if (length > MAX_BODY_BYTES) { await reader.cancel(); throw invalid("too_long", 413); }
      chunks.push(value);
    }
  } finally { reader.releaseLock(); }
  const bytes = new Uint8Array(length);
  let at = 0;
  for (const chunk of chunks) { bytes.set(chunk, at); at += chunk.length; }
  try { return JSON.parse(new TextDecoder().decode(bytes)); } catch { return null; }
}

function dimensions(bytes, type) {
  const view = new DataView(bytes.buffer);
  if (type === "png") {
    const magic = [137, 80, 78, 71, 13, 10, 26, 10];
    if (bytes.length < 33 || !magic.every((v, i) => bytes[i] === v) ||
        view.getUint32(8) !== 13 || String.fromCharCode(...bytes.slice(12, 16)) !== "IHDR") throw invalid();
    return [view.getUint32(16), view.getUint32(20)];
  }
  if (bytes[0] !== 255 || bytes[1] !== 216 || bytes.at(-2) !== 255 || bytes.at(-1) !== 217) throw invalid();
  let offset = 2;
  while (offset + 4 <= bytes.length) {
    if (bytes[offset++] !== 255) throw invalid();
    while (bytes[offset] === 255) offset++;
    const marker = bytes[offset++];
    if (marker === 218 || marker === 217) break;
    const length = view.getUint16(offset);
    if (length < 2 || offset + length > bytes.length) throw invalid();
    if ([192, 193, 194].includes(marker)) {
      if (length < 8) throw invalid();
      return [view.getUint16(offset + 5), view.getUint16(offset + 3)];
    }
    offset += length;
  }
  throw invalid();
}

export function validateImage(image) {
  if (image === undefined) return null;
  if (!image || typeof image.dataUrl !== "string") throw invalid();
  if (image.dataUrl.length > MAX_IMAGE_BYTES * 4 / 3 + 40) throw invalid("image_too_large", 413);
  const match = image.dataUrl.match(/^data:image\/(png|jpeg);base64,([A-Za-z0-9+/]+={0,2})$/);
  if (!match || match[2].length % 4 !== 0) throw invalid();
  let raw;
  try { raw = atob(match[2]); } catch { throw invalid(); }
  if (raw.length > MAX_IMAGE_BYTES) throw invalid("image_too_large", 413);
  const [width, height] = dimensions(Uint8Array.from(raw, c => c.charCodeAt(0)), match[1]);
  if (width < 1 || height < 1 || width > 1600 || height > 1600 || width * height > 1_000_000) throw invalid("image_too_large", 413);
  if (width !== image.width || height !== image.height) throw invalid();
  return { dataUrl: image.dataUrl, width, height };
}

export { sourceUrl } from "../src/lib/source-url.mjs";
