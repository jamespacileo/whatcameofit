const hex = (buffer) => [...new Uint8Array(buffer)].map((b) => b.toString(16).padStart(2, "0")).join("");

// SHA-256 of bytes or of a string's UTF-8, in lower-case hex.
export const sha256 = async (bytes) => hex(await crypto.subtle.digest("SHA-256", typeof bytes === "string" ? new TextEncoder().encode(bytes) : bytes));

// A run's checksum: the SHA-256 of its chunks' checksums, sorted and joined by a line
// feed. It does not depend on the order the chunks arrive in, and a chunk sent twice
// counts once.
export const runChecksum = (chunks) => sha256([...new Set(chunks)].sort().join("\n"));
