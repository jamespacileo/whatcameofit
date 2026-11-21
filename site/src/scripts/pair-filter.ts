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
      if (!out) visible += 1;
    });
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
