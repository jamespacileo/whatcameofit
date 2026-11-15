// Narrowing the claim page's timetable to one kind of entry (openspec site-publishing:
// "The timetable can be narrowed to one kind of entry"). The controls are shown by this
// script, so with none every entry is simply there. Counts are read from the entries
// shown, promises and records apart, and never added together.
const controls = document.querySelector<HTMLElement>("[data-kinds]");
const table = document.querySelector<HTMLElement>(".timetable");
if (controls && table) {
  const tabs = [...controls.querySelectorAll<HTMLButtonElement>("[data-kind]")];
  const said = document.querySelector<HTMLElement>("[data-kinds-said]");
  const undated = document.querySelector<HTMLElement>("[data-undated]");
  const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? "" : "s"}`;

  const show = (kind: string) => {
    for (const tab of tabs) tab.setAttribute("aria-pressed", String(tab.dataset.kind === kind));
    let promises = 0;
    let records = 0;
    for (const row of table.querySelectorAll<HTMLElement>("[data-year-row]")) {
      let left = 0;
      for (const list of row.querySelectorAll<HTMLElement>("[data-promises]")) {
        list.hidden = kind !== "all" && kind !== "promise";
        if (!list.hidden) {
          left += 1;
          promises += list.children.length;
        }
      }
      for (const entry of row.querySelectorAll<HTMLElement>("li[data-kind]")) {
        entry.hidden = kind !== "all" && entry.dataset.kind !== kind;
        if (!entry.hidden) {
          left += 1;
          records += Number(entry.dataset.n ?? 1);
        }
      }
      row.hidden = kind !== "all" && left === 0;
    }
    for (const gap of table.querySelectorAll<HTMLElement>("tr.quiet")) gap.hidden = kind !== "all";
    if (undated) {
      undated.hidden = kind !== "all" && kind !== "promise";
      if (!undated.hidden) promises += undated.querySelectorAll("li").length;
    }
    const parts = [
      ...(promises > 0 ? [plural(promises, "promise")] : []),
      ...(records > 0 ? [plural(records, "record")] : []),
    ];
    if (said) said.textContent = `Showing ${parts.join(" and ")}.`;
  };

  for (const tab of tabs) tab.addEventListener("click", () => show(tab.dataset.kind!));
  controls.hidden = false;

  // On paper every entry is shown, whatever was narrowed on screen.
  let narrowed: string | null = null;
  addEventListener("beforeprint", () => {
    narrowed = tabs.find((tab) => tab.getAttribute("aria-pressed") === "true")?.dataset.kind ?? null;
    if (narrowed && narrowed !== "all") show("all");
  });
  addEventListener("afterprint", () => {
    if (narrowed && narrowed !== "all") show(narrowed);
  });
}
