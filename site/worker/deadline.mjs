// One deadline over a whole piece of outside work: the request, its headers and the
// reading of its body. When it passes the work's signal is aborted and the caller is
// answered at once, even by a fetch or a body that does not listen to its signal.

/** The error a passed deadline rejects with. It quotes nothing that was sent. */
export function timedOut(label = "deadline") {
  const error = new Error(`${label} timeout`);
  error.code = "timeout";
  return error;
}

/**
 * Runs `work(signal)` within `timeoutMs`. Rejects with timedOut() when the deadline
 * passes, or when `parent` is aborted first; the timer and listeners are always cleared.
 * @param {number} timeoutMs
 * @param {(signal: AbortSignal) => Promise<any>} work
 * @param {{ label?: string, parent?: AbortSignal }} [options]
 */
export async function withDeadline(timeoutMs, work, { label, parent } = {}) {
  const controller = new AbortController();
  let timer;
  let stop;
  const ended = new Promise((_resolve, reject) => {
    stop = (reason) => {
      reject(reason);
      controller.abort(reason);
    };
    timer = setTimeout(() => stop(timedOut(label)), timeoutMs);
  });
  const fromParent = () => stop(parent.reason ?? timedOut(label));
  if (parent?.aborted) fromParent();
  else parent?.addEventListener("abort", fromParent, { once: true });
  try {
    return await Promise.race([Promise.resolve().then(() => work(controller.signal)), ended]);
  } finally {
    clearTimeout(timer);
    parent?.removeEventListener("abort", fromParent);
    // A late rejection of the race's loser is expected and handled here.
    ended.catch(() => {});
  }
}
