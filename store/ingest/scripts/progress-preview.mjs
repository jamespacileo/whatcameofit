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
const slices = Array.from({ length: 52 }, (_, i) => {
  const trials = i === 51 ? 679 : 2000, reached = (ahead) => Math.round(trials * Math.max(0, Math.min(1, (ahead - i) / 6)));
  return { slice: `s${String(i + 1).padStart(3, "0")}`, position: i + 1, trials, updated_at: at,
    stages: { record: reached(40), registry_papers: reached(30), pubmed_papers: reached(24), in_store: reached(14), page: reached(8) } };
});
await service.ask("PUT", "/progress/slices", { token: TOKEN, body: { set: "active-or-ended-this-year", total_trials: 102679, total_slices: 52, slices } });
// One origin for the page and its requests: every request is handed to the Worker.
http.createServer(async (request, response) => {
  const chunks = [];
  for await (const chunk of request) chunks.push(chunk);
  const answer = await service.mf.dispatchFetch(`http://ingest.test${request.url}`, { method: request.method, headers: request.headers, body: chunks.length ? Buffer.concat(chunks) : undefined });
  response.writeHead(answer.status, Object.fromEntries(answer.headers));
  response.end(Buffer.from(await answer.arrayBuffer()));
}).listen(port, "127.0.0.1", () => console.log(`http://127.0.0.1:${port}/progress/page   token for this preview: ${TOKEN}`));
process.on("SIGINT", async () => { await service.close(); process.exit(0); });
