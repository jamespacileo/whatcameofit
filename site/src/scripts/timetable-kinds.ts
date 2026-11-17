// Narrowing the claim page's timetable to one kind of entry (openspec site-publishing:
// "The timetable can be narrowed to one kind of entry"). The controls are shown by this
// script, so with none every entry is simply there. Counts are read from the entries
// shown, promises and records apart, and never added together.
// A long record's older years are folded (openspec sheet-cohesion). While the table is
// narrowed to one kind, and on paper, the folded years are opened so that what is left
// is in sight; afterwards the years this script opened fold again.
const yearFolds = [...document.querySelectorAll<HTMLDetailsElement>("details.year-rest")];
const opened = new Set<HTMLDetailsElement>();
let printing = false;
let kindShown = "all";
const syncYears = () => {
  if (printing || kindShown !== "all") {
    for (const year of yearFolds) {
      if (!year.open) {
        opened.add(year);
        year.open = true;
      }
    }
  } else {
    for (const year of opened) year.open = false;
    opened.clear();
  }
};
if (yearFolds.length > 0) {
  addEventListener("beforeprint", () => {
    printing = true;
    syncYears();
  });
  addEventListener("afterprint", () => {
    printing = false;
    syncYears();
  });
}

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
    kindShown = kind;
    syncYears();
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
