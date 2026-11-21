// A long list of pairs, a page at a time (lib/blocks.ts, pager; the claims site's Pager script,
// on pairs). The page as sent holds every row and a hidden pager: here the pager is shown and
// the rows outside the page in view are hidden. The stage filter below marks the rows it leaves
// out ("data-out") and the pager pages the rest, from the first page again. Paper gets the
// whole list (pair.css shows the rows marked "data-paged" in print).
const repage = new Map<Element, (first: boolean) => void>();
for (const nav of document.querySelectorAll<HTMLElement>("nav[data-pager]")) {
  const frame = nav.previousElementSibling as HTMLElement | null;
  const table = frame?.querySelector("table");
  if (!frame || !table) continue;
  const rows = [...table.querySelectorAll<HTMLElement>("tbody tr")];
  const size = Number(nav.dataset.size);
  const line = nav.querySelector<HTMLElement>("[data-at]")!;
  const steps = [...nav.querySelectorAll<HTMLButtonElement>("button[data-step]")];
  const number = (n: number) => n.toLocaleString("en-GB");
  let page = Number(new URL(location.href).searchParams.get("page") ?? 1);

  const draw = () => {
    const listed = rows.filter((row) => !row.hasAttribute("data-out"));
    const pages = Math.max(1, Math.ceil(listed.length / size));
    // A page past the end, or no page at all, is the nearest page there is.
    page = Number.isInteger(page) ? Math.min(Math.max(page, 1), pages) : 1;
    const inView = new Set(listed.slice((page - 1) * size, page * size));
    for (const row of rows) {
      const out = row.hasAttribute("data-out");
      row.hidden = out || !inView.has(row);
      row.toggleAttribute("data-paged", !out && !inView.has(row));
    }
    nav.hidden = pages === 1;
    line.textContent = `${number((page - 1) * size + 1)}–${number(Math.min(page * size, listed.length))} of ${number(listed.length)}`;
    for (const step of steps) {
      const to = page + Number(step.dataset.step);
      const off = to < 1 || to > pages;
      step.setAttribute("aria-disabled", String(off));
      // A step that leads nowhere is passed over by the Tab key, and keeps the focus it has,
      // so pressing Next to the last page does not drop the reader.
      step.tabIndex = off ? -1 : 0;
    }
  };
  // The page stays in the address, so "back" from a pair's page returns to the same rows.
  const remember = () => {
    const url = new URL(location.href);
    if (page > 1) url.searchParams.set("page", String(page));
    else url.searchParams.delete("page");
    history.replaceState(history.state, "", url);
  };
  for (const step of steps) {
    step.addEventListener("click", () => {
      if (step.getAttribute("aria-disabled") === "true") return;
      page += Number(step.dataset.step);
      draw();
      remember();
      // The next page is read from its top.
      if (frame.getBoundingClientRect?.().top < 0) frame.scrollIntoView({ block: "start" });
    });
  }
  repage.set(table, (first) => {
    if (first) page = 1;
    draw();
    if (first) remember();
  });
  draw();
}

// The stage filter (lib/blocks.ts, stageFilter): picking a place on the path shows only the
// pairs there, picking it again shows all, and a typed word narrows the list to the rows that
// hold it. It narrows the first table after it. The claims site's StageFilter script, on pairs;
// without it the counts read as a summary and every row stays in view.
for (const filter of document.querySelectorAll<HTMLElement>(".stage-filter[data-stage-filter]")) {
  let next = filter.nextElementSibling;
  while (next && !next.matches("table") && !next.querySelector("table")) next = next.nextElementSibling;
  const table = next?.matches("table") ? (next as HTMLTableElement) : (next?.querySelector("table") ?? null);
  if (!table) continue;
  const frame = table.closest<HTMLElement>(".table-frame") ?? table;
  const rows = [...table.querySelectorAll<HTMLElement>("tbody tr[data-status]")];
  const buttons = [...filter.querySelectorAll<HTMLButtonElement>("button[data-status]")];
  const shown = filter.querySelector<HTMLElement>("[data-shown]")!;
  const shownText = filter.querySelector<HTMLElement>("[data-shown-text]")!;
  const input = filter.querySelector<HTMLInputElement>("[data-words]");
  const none = filter.querySelector<HTMLElement>("[data-none]")!;
  const noneWhat = filter.querySelector<HTMLElement>("[data-none-what]")!;
  // Each row's words, read once: a long list is narrowed on every key.
  const words = rows.map((row) => (row.querySelector("th")?.textContent ?? "").toLowerCase());
  let current: string | null = null;

  const apply = (picked: string | null, remember = true) => {
    current = picked;
    const typed = (input?.value ?? "").trim().toLowerCase();
    let label = "";
    for (const button of buttons) {
      const on = button.dataset.status === picked;
      button.setAttribute("aria-pressed", String(on));
      if (on) label = button.dataset.label!;
    }
    let visible = 0;
    // The counts follow the typed word, so each place says how many of the rows found stand there.
    const counts = new Map<string, number>();
    rows.forEach((row, index) => {
      const found = typed === "" || words[index].includes(typed);
      const status = row.dataset.status!;
      if (found) counts.set(status, (counts.get(status) ?? 0) + 1);
      const out = !found || (picked !== null && status !== picked);
      row.hidden = out;
      row.toggleAttribute("data-out", out);
      if (!out) visible += 1;
    });
    // A long list is paged: the rows left in begin again at their first page, unless this is
    // the filter the address asked for, which keeps the page the address names.
    repage.get(table)?.(remember);
    for (const button of buttons) {
      const count = counts.get(button.dataset.status!) ?? 0;
      button.querySelector("strong")!.textContent = String(count);
      // The picked place stays pressable, so it can always be let go.
      button.disabled = count === 0 && button.dataset.status !== picked;
    }
    shown.hidden = (picked === null && typed === "") || visible === 0;
    // Nothing left: the table gives way to a line that says so and names what was asked.
    none.hidden = visible > 0;
    frame.hidden = visible === 0;
    if (visible === 0) {
      const word = input?.value.trim() ?? "";
      noneWhat.textContent = picked === null ? `Nothing here contains “${word}”.` : `Nothing at “${label}” contains “${word}”.`;
    }
    shownText.textContent = `Showing ${visible} of ${rows.length}.`;
    if (remember) {
      // The picked status stays in the address, so a narrowed list can be passed on.
      const url = new URL(location.href);
      if (picked) url.searchParams.set("status", picked);
      else url.searchParams.delete("status");
      history.replaceState(history.state, "", url);
    }
  };

  for (const button of buttons) {
    button.addEventListener("click", () => apply(button.getAttribute("aria-pressed") === "true" ? null : button.dataset.status!));
  }
  for (const all of filter.querySelectorAll("[data-show-all]")) {
    all.addEventListener("click", () => {
      if (input) input.value = "";
      apply(null);
      input?.focus();
    });
  }
  input?.addEventListener("input", () => apply(current));

  const asked = new URL(location.href).searchParams.get("status");
  if (buttons.some((button) => button.dataset.status === asked && !button.disabled)) apply(asked, false);
}
