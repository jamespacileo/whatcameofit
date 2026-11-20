// The section list (lib/blocks.ts, sectionList): the section in view is marked as the reader
// scrolls, and on a narrow screen its row moves so the marked name is in view and fades the end
// that has more. Without this script the list is a plain list of links.
for (const nav of document.querySelectorAll<HTMLElement>(".onpage")) {
  const list = nav.querySelector<HTMLElement>(".onpage-list");
  if (!list) continue;
  // Each link with the section it leads to, held together: a link's address is encoded
  // (sectionList), a section's id is not, so they are matched once, here.
  const sections = [...list.querySelectorAll<HTMLAnchorElement>('a[href^="#"]')]
    .map((link) => {
      let id: string;
      try {
        id = decodeURIComponent(link.hash.slice(1));
      } catch {
        return null;
      }
      const target = document.getElementById(id);
      return target ? { link, target } : null;
    })
    .filter((section): section is { link: HTMLAnchorElement; target: HTMLElement } => section !== null);
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
  // Where a heading lands when its link is followed: its own scroll margin, or below the row
  // when the row stays at the top. A section is reached once its heading is there.
  const landing = (target: HTMLElement) => {
    const margin = parseFloat(getComputedStyle(target).scrollMarginTop) || 0;
    const box = nav.getBoundingClientRect();
    // On a narrow screen the list is a row across the page, stuck at its top; on a wide one it
    // is a column beside the sheet and covers no heading.
    const isRow = box.width >= innerWidth / 2;
    const row = isRow && getComputedStyle(nav).position === "sticky" && box.top <= 0 ? box.bottom : 0;
    return Math.max(margin, row) + 2;
  };

  let marked: HTMLElement | null = null;
  const mark = (again = false) => {
    let current = sections[0];
    for (const section of sections) if (section.target.getBoundingClientRect().top <= landing(section.target)) current = section;
    if (!current || (current.link === marked && !again)) return;
    marked = current.link;
    for (const { link } of sections) {
      if (link === current.link) link.setAttribute("aria-current", "true");
      else link.removeAttribute("aria-current");
    }
    centre(current.link);
  };

  if (sections.length > 0) {
    addEventListener("scroll", () => mark(), { passive: true });
    mark();
  }
  list.addEventListener("scroll", ends, { passive: true });
  // A new width moves the headings and the row: what is in view and where its chip sits are
  // worked out again.
  addEventListener("resize", () => {
    if (sections.length > 0) mark(true);
    ends();
  });
  ends();
}
