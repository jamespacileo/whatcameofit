// Folding sections (components/FoldHead.astro). The first state is the stylesheet's;
// this only records a press, keeps the button's state in step, and opens a section
// that a link leads into.
const phone = matchMedia("(max-width: 40rem)");
const heads = [...document.querySelectorAll<HTMLElement>(".fold-head")];
const button = (head: HTMLElement) => head.querySelector<HTMLButtonElement>(".fold")!;
const isOpen = (head: HTMLElement) =>
  head.dataset.state
    ? head.dataset.state === "open"
    : (phone.matches ? head.dataset.foldPhone : head.dataset.fold) !== "folded";
const show = (head: HTMLElement) => button(head).setAttribute("aria-expanded", String(isOpen(head)));
const set = (head: HTMLElement, open: boolean) => {
  head.dataset.state = open ? "open" : "closed";
  show(head);
};

for (const head of heads) {
  show(head);
  button(head).addEventListener("click", () => set(head, !isOpen(head)));
}
// A section nobody has pressed follows the screen's width.
phone.addEventListener("change", () => heads.forEach(show));

// A trial's row opens to the rest of its record. With no script it is simply open.
const rows = [...document.querySelectorAll<HTMLButtonElement>(".trial-open")];
const openRow = (row: HTMLButtonElement, open: boolean) => {
  row.setAttribute("aria-expanded", String(open));
  row.closest<HTMLElement>(".trial-group")!.toggleAttribute("data-open", open);
};
for (const row of rows) {
  openRow(row, false);
  row.addEventListener("click", () => openRow(row, row.getAttribute("aria-expanded") !== "true"));
}

// A fact row that opens (components/Fact.astro), such as a term in "At a glance". The
// stylesheet draws it closed from the first paint; with no script it is simply open.
const terms = [...document.querySelectorAll<HTMLButtonElement>(".fact-open")];
const openTerm = (term: HTMLButtonElement, open: boolean) => {
  term.setAttribute("aria-expanded", String(open));
  term.closest<HTMLElement>(".fact-sheet > div, .entry-rows > li")!.toggleAttribute("data-open", open);
};
for (const term of terms) {
  openTerm(term, false);
  term.addEventListener("click", () => openTerm(term, term.getAttribute("aria-expanded") !== "true"));
}

// Paper has no press: why each term matched prints open, then goes back as it was.
const whys = [...document.querySelectorAll<HTMLDetailsElement>(".fact-more .match-why")];
addEventListener("beforeprint", () => {
  for (const why of whys) {
    why.toggleAttribute("data-was-open", why.open);
    why.open = true;
  }
});
addEventListener("afterprint", () => {
  for (const why of whys) why.open = why.hasAttribute("data-was-open");
});

// A link to a folded section, or to something inside one, opens it.
const reveal = (hash: string) => {
  if (hash.length < 2) return;
  const target = document.getElementById(decodeURIComponent(hash.slice(1)));
  if (!target) return;
  // A link to a trial opens its row, and the rest of the trials if it is among them.
  const group = target.closest<HTMLElement>(".trial-group");
  const row = group?.querySelector<HTMLButtonElement>(".trial-open");
  if (row) openRow(row, true);
  // A link to a fact row that opens, or to something inside it, opens it.
  const term = target.closest<HTMLElement>(".fact-sheet > div, .entry-rows > li")?.querySelector<HTMLButtonElement>(".fact-open");
  if (term) openTerm(term, true);
  const rest = target.closest<HTMLDetailsElement>("details");
  if (rest) rest.open = true;
  const head =
    target.closest<HTMLElement>(".fold-head") ??
    heads.find((candidate) => candidate.parentElement?.contains(target));
  if (head && !isOpen(head)) set(head, true);
  if (row || rest || head) target.scrollIntoView();
};
reveal(location.hash);
addEventListener("hashchange", () => reveal(location.hash));
document.addEventListener("click", (event) => {
  const link = (event.target as Element).closest<HTMLAnchorElement>('a[href^="#"]');
  if (link) reveal(link.getAttribute("href")!);
});
