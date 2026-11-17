// The rows a list leaves out of the page as built (openspec landing-rows-on-demand).
// Runs in the browser. A list's holder names where the rest of its rows are, in
// "data-rest": one address, or several parted by spaces. They are fetched the first
// time something on the page needs them, and once. Nothing is remembered here: the
// holder's own attributes say where it stands, so every script on the page reads the
// same state.
//
// When the rows arrive, in this order:
// 1. "rows:arrive" on the document, with the rows not yet in the page: each filter
//    marks the rows it leaves out, as it has marked the rows already there;
// 2. the rows are put in the holder: before its "data-rest-before" element, or at the
//    end of its "data-rest-into" element, and a row marked "data-rest-first" first;
// 3. "rest:here" on the holder: what counts and pages its rows reads them again.
// When they do not arrive the holder says so, with a control to ask again, and
// "rest:failed" is sent to it. A list is never drawn as whole while it is not.

export interface Arrival {
  holder: HTMLElement;
  /** The arriving rows, before they are in the page. */
  rows: DocumentFragment;
}

/** True while the rest of the holder's rows are not in the page. */
export const waiting = (holder: Element | null | undefined): holder is HTMLElement =>
  holder?.hasAttribute("data-rest") ?? false;

/** Hears of rows before they are put in the page, to mark the ones a filter leaves out. */
export function onArrive(listen: (arrival: Arrival) => void) {
  document.addEventListener("rows:arrive", (event) => listen((event as CustomEvent<Arrival>).detail));
}

function say(holder: HTMLElement, state: "loading" | "failed" | null) {
  const said = holder.querySelector<HTMLElement>(":scope > [data-rest-said]");
  if (!said) return;
  said.querySelector<HTMLElement>("[data-rest-line]")!.textContent = state ? said.dataset[state]! : "";
  const again = said.querySelector<HTMLButtonElement>("[data-rest-again]")!;
  again.hidden = state !== "failed";
  again.onclick = () => void fetchRest(holder);
}

async function fetchRest(holder: HTMLElement) {
  holder.setAttribute("aria-busy", "true");
  say(holder, "loading");
  try {
    const parts = await Promise.all(
      holder.dataset.rest!.split(" ").map(async (address) => {
        const response = await fetch(address);
        // A deployment may have removed this page's edition of the rows. Only restart
        // when the current home page confirms a newer export; outages stay retryable.
        if (response.status === 404 || response.headers.get("content-type")?.includes("text/html")) {
          const home = await fetch("/", { cache: "no-cache" });
          if (home.ok) {
            const current = new DOMParser().parseFromString(await home.text(), "text/html");
            const version = current.querySelector<HTMLElement>("[data-export-version]")?.dataset.exportVersion;
            const held = document.querySelector<HTMLElement>("[data-export-version]")?.dataset.exportVersion;
            if (held && version && version !== held) location.reload();
          }
          throw new Error(`No rows at ${address}`);
        }
        if (!response.ok) throw new Error(`${address} answered ${response.status}`);
        return response.text();
      }),
    );
    // Parsed apart from the page, so a table's rows stay rows and nothing in them runs.
    const template = document.createElement("template");
    template.innerHTML = parts.join("");
    const rows = template.content;
    document.dispatchEvent(new CustomEvent<Arrival>("rows:arrive", { detail: { holder, rows } }));
    const firsts = [...rows.children].filter((row) => row.hasAttribute("data-rest-first"));
    for (const first of firsts.reverse()) holder.prepend(first);
    const before = holder.querySelector("[data-rest-before]");
    if (before) before.before(rows);
    else (holder.querySelector("[data-rest-into]") ?? holder).append(rows);
  } catch (error) {
    console.error("The rest of a list did not load.", error);
    holder.removeAttribute("aria-busy");
    say(holder, "failed");
    holder.dispatchEvent(new Event("rest:failed"));
    return;
  }
  holder.removeAttribute("data-rest");
  holder.removeAttribute("aria-busy");
  say(holder, null);
  holder.dispatchEvent(new Event("rest:here"));
}

/** Fetches the rest of the holder's rows unless they are here or on their way. Answers
 * true once they are in the page, false when they did not arrive. */
export function loadRest(holder: HTMLElement): Promise<boolean> {
  if (!waiting(holder)) return Promise.resolve(true);
  const settled = new Promise<boolean>((resolve) => {
    const done = (event: Event) => {
      holder.removeEventListener("rest:here", done);
      holder.removeEventListener("rest:failed", done);
      resolve(event.type === "rest:here");
    };
    holder.addEventListener("rest:here", done);
    holder.addEventListener("rest:failed", done);
  });
  if (holder.getAttribute("aria-busy") !== "true") void fetchRest(holder);
  return settled;
}
