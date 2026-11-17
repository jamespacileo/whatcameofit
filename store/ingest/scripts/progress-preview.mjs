// The progress page on this machine, with made-up counts, for looking at it while
// changing it. A local Worker on D1's local engine; nothing is sent anywhere and no real
// token is used: the page takes the token below, which exists only in this script.
//
//   node store/ingest/scripts/progress-preview.mjs [port]     then open /progress/page
import { createHash } from "node:crypto";
import http from "node:http";
import { Service, engineUnavailable } from "../tests/harness.mjs";

const TOKEN = "local-preview-token-not-a-secret";
const port = Number(process.argv[2]) || 8791;
const unavailable = await engineUnavailable();
if (unavailable) { console.error(unavailable); process.exit(1); }
const service = await Service.open({ entries: [{ name: "preview", role: "operator", sha256: createHash("sha256").update(TOKEN).digest("hex") }] });
const at = "2026-11-17T10:00:00.000000+00:00";
const groups = ["ended with results", "ended", "active with results", "active updated", "active not updated"];
const slices = Array.from({ length: 52 }, (_, i) => {
  const trials = i === 51 ? 679 : 2000;
  const body = { rule: "active-or-ended-this-year", year: 2026, number: i + 1, grp: groups[Math.floor(i / 11)], trials, with_results: i < 22 ? trials : 0, in_store: i < 14 ? trials : i === 14 ? 900 : 0,
    ...(i < 40 ? { record_at: at } : {}), ...(i < 30 ? { registry_papers_at: at, registry_papers: Math.round(trials * 0.4) } : {}),
    ...(i < 24 ? { pubmed_papers_at: at, pubmed_asked: trials, pubmed_found: Math.round(trials * 0.3) } : {}), ...(i < 14 ? { in_store_at: at } : {}), ...(i < 8 ? { page_at: at } : {}) };
  return ["trial_slice", `${body.rule}|${body.year}|${body.number}`, body];
});
// A slice's state is a record like any other: handed over and merged.
if (await service.hand("preview-slices", slices, { token: TOKEN, as: "operator", writer: "operator", steps: {} })) throw new Error("the made-up slices were refused");
if ((await service.ask("POST", "/runs/preview-slices/merge", { token: TOKEN })).body.status !== "merged") throw new Error("the made-up slices were not merged");
// One origin for the page and its requests: every request is handed to the Worker.
http.createServer(async (request, response) => {
  const chunks = [];
  for await (const chunk of request) chunks.push(chunk);
  const answer = await service.mf.dispatchFetch(`http://ingest.test${request.url}`, { method: request.method, headers: request.headers, body: chunks.length ? Buffer.concat(chunks) : undefined });
  response.writeHead(answer.status, Object.fromEntries(answer.headers));
  response.end(Buffer.from(await answer.arrayBuffer()));
}).listen(port, "127.0.0.1", () => console.log(`http://127.0.0.1:${port}/progress/page   token for this preview: ${TOKEN}`));
process.on("SIGINT", async () => { await service.close(); process.exit(0); });
