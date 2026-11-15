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

// A link to a folded section, or to something inside one, opens it.
const reveal = (hash: string) => {
  if (hash.length < 2) return;
  const target = document.getElementById(decodeURIComponent(hash.slice(1)));
  if (!target) return;
  const head =
    target.closest<HTMLElement>(".fold-head") ??
    heads.find((candidate) => candidate.parentElement?.contains(target));
  if (!head || isOpen(head)) return;
  set(head, true);
  target.scrollIntoView();
};
reveal(location.hash);
addEventListener("hashchange", () => reveal(location.hash));
document.addEventListener("click", (event) => {
  const link = (event.target as Element).closest<HTMLAnchorElement>('a[href^="#"]');
  if (link) reveal(link.getAttribute("href")!);
});
