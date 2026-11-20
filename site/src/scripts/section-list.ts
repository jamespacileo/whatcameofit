// The section list (lib/blocks.ts, sectionList): the section in view is marked as the reader
// scrolls, and on a narrow screen its row moves so the marked name is in view and fades the end
// that has more. Without this script the list is a plain list of links.
for (const nav of document.querySelectorAll<HTMLElement>(".onpage")) {
  const list = nav.querySelector<HTMLElement>(".onpage-list");
  if (!list) continue;
  const links = [...list.querySelectorAll<HTMLAnchorElement>('a[href^="#"]')];
  const targets = links
    .map((link) => document.getElementById(decodeURIComponent(link.getAttribute("href")!.slice(1))))
    .filter((target): target is HTMLElement => target !== null);
  const still = matchMedia("(prefers-reduced-motion: reduce)");

  // The row moves so that the marked name is in view. Only the row scrolls.
  const centre = (link: HTMLElement) => {
    if (list.scrollWidth <= list.clientWidth) return;
    list.scrollTo({ left: link.offsetLeft - (list.clientWidth - link.offsetWidth) / 2, behavior: still.matches ? "auto" : "smooth" });
  };
  // Which end has more beyond it: the stylesheet fades that end.
  const ends = () => {
    const more = [];
    if (list.scrollLeft > 4) more.push("start");
    if (list.scrollLeft + list.clientWidth < list.scrollWidth - 4) more.push("end");
    nav.dataset.more = more.join(" ");
  };

  let marked: HTMLElement | null = null;
  const mark = () => {
    let current = targets[0];
    for (const target of targets) if (target.getBoundingClientRect().top <= 140) current = target;
    if (!current || current === marked) return;
    marked = current;
    for (const link of links) {
      if (link.getAttribute("href") === `#${current.id}`) {
        link.setAttribute("aria-current", "true");
        centre(link);
      } else link.removeAttribute("aria-current");
    }
  };

  if (targets.length > 0) {
    addEventListener("scroll", mark, { passive: true });
    mark();
  }
  list.addEventListener("scroll", ends, { passive: true });
  addEventListener("resize", ends);
  ends();
}
