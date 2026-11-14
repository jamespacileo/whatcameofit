// An opted-in lookup answered in stages, one JSON event per line: the completed clinical
// answer ("core"), then the answer with optional research enrichment ("complete"), or an
// explicit "error". Nothing here is logged or kept; a reader who leaves ends the stream.

export const STREAM_TYPE = "application/x-ndjson; charset=utf-8";

/**
 * A response whose body carries what `run(send)` sends. `send` returns false once the
 * reader has gone. A failure of `run` itself ends the stream with an error event.
 * @param {(send: (event: object) => boolean) => Promise<void>} run
 */
export function eventStream(run) {
  const encoder = new TextEncoder();
  let open = true;
  let sink;
  const body = new ReadableStream({
    start(controller) { sink = controller; },
    cancel() { open = false; },
  });
  const send = (event) => {
    if (!open) return false;
    try {
      sink.enqueue(encoder.encode(`${JSON.stringify(event)}\n`));
      return true;
    } catch {
      open = false;
      return false;
    }
  };
  Promise.resolve()
    .then(() => run(send))
    // What failed may quote what was sent, so only the code is given.
    .catch(() => { send({ type: "error", error: "failed" }); })
    .finally(() => {
      if (!open) return;
      open = false;
      try { sink.close(); } catch { /* Already closed by the reader. */ }
    });
  return new Response(body, {
    headers: { "Content-Type": STREAM_TYPE, "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" },
  });
}

/** Stage durations as a Server-Timing header: names and whole milliseconds only. */
export function serverTiming(timings) {
  return Object.entries(timings ?? {})
    .filter(([name, value]) => /^[a-z_]+$/.test(name) && Number.isFinite(value))
    .map(([name, value]) => `${name.replace(/_ms$/, "")};dur=${Math.round(value)}`)
    .join(", ");
}

/** The same durations, as numbers only, for an event. */
export function stageTimes(timings) {
  return Object.fromEntries(Object.entries(timings ?? {})
    .filter(([name, value]) => /^[a-z_]+$/.test(name) && Number.isFinite(value))
    .map(([name, value]) => [name, Math.round(value)]));
}
