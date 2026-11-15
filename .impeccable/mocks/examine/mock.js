// Mock behaviour only: icons, folds, the section list's current place,
// the timeline's tabs, the table filter and printing. None of this is the site's script.
const ICONS = {
  chev: '<path d="m6 9 6 6 6-6"/>',
  brief: '<path d="m3 17 2 2 4-4"/><path d="m3 7 2 2 4-4"/><path d="M13 6h8"/><path d="M13 12h8"/><path d="M13 18h8"/>',
  news: '<path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"/><path d="M18 14h-8"/><path d="M15 18h-5"/><path d="M10 6h8v4h-8V6Z"/>',
  clock: '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
  flask: '<path d="M10 2v7.527a2 2 0 0 1-.211.896L4.72 20.55a1 1 0 0 0 .9 1.45h12.76a1 1 0 0 0 .9-1.45l-5.069-10.127A2 2 0 0 1 14 9.527V2"/><path d="M8.5 2h7"/><path d="M7 16h10"/>',
  paper: '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/>',
  org: '<path d="M3 22h18"/><path d="M6 18v-7"/><path d="M10 18v-7"/><path d="M14 18v-7"/><path d="M18 18v-7"/><path d="m12 2 8 5H4z"/>',
  book: '<path d="M12 7v14"/><path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z"/>',
  share: '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="m8.59 13.51 6.83 3.98"/><path d="m15.41 6.51-6.82 3.98"/>',
  follow: '<path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z"/>',
  flag: '<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><path d="M4 22v-7"/>',
  out: '<path d="M7 7h10v10"/><path d="M7 17 17 7"/>',
  search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
  feed: '<path d="M4 11a9 9 0 0 1 9 9"/><path d="M4 4a16 16 0 0 1 16 16"/><circle cx="5" cy="19" r="1"/>',
  copy: '<rect x="8" y="8" width="14" height="14" rx="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>',
  list: '<path d="M3 6h18"/><path d="M7 12h10"/><path d="M10 18h4"/>',
  topics: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/>',
  change: '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/>',
  others: '<path d="M8 6h13"/><path d="M8 12h13"/><path d="M8 18h13"/><path d="M3 6h.01"/><path d="M3 12h.01"/><path d="M3 18h.01"/>',
};
for (const el of document.querySelectorAll("[data-i]")) {
  el.outerHTML = `<svg class="i" viewBox="0 0 24 24" aria-hidden="true">${ICONS[el.dataset.i] ?? ""}</svg>`;
}

const MARK = `<svg viewBox="8 8 48 48" width="30" height="30" aria-hidden="true"><path fill="#fff" fill-rule="evenodd" d="M42.38 49.02A22 22 0 1 1 49.02 42.38A1.2 1.2 0 0 0 49.18 43.88L54.36 49.06A3.75 3.75 0 0 1 49.06 54.36L43.88 49.18A1.2 1.2 0 0 0 42.38 49.02ZM47 30.5A16.5 16.5 0 1 0 14 30.5A16.5 16.5 0 1 0 47 30.5Z"/><path d="M29.7 23.75h-6.2a6.75 6.75 0 0 0 0 13.5h6.2z" fill="#f28a62"/><path d="M31.3 23.75h6.2a6.75 6.75 0 0 1 0 13.5h-6.2z" fill="#1687da"/></svg>`;
for (const el of document.querySelectorAll("[data-mark]")) el.innerHTML = MARK;

// Small stage tracks: one place marked, never filled up to it.
for (const el of document.querySelectorAll("[data-track]")) {
  const place = Number(el.dataset.track);
  el.className = "track mini";
  el.innerHTML = `<span class="steps" role="img" aria-label="Place ${place} of 6 on the path from preclinical to approved">${[1, 2, 3, 4, 5, 6].map((n) => `<span class="step${n === place ? " here" : ""}"></span>`).join("")}</span>`;
}

// Folds: a button in a heading (or in a table row) shows and hides the block it names.
const phone = matchMedia("(max-width: 48rem)");
function setFold(button, open) {
  button.setAttribute("aria-expanded", String(open));
  document.getElementById(button.getAttribute("aria-controls")).hidden = !open;
}
function foldOf(target) {
  return target?.matches(".sec") ? target.querySelector(":scope > .sec-head .fold") : null;
}
for (const b of document.querySelectorAll(".fold")) {
  b.addEventListener("click", () => setFold(b, b.getAttribute("aria-expanded") !== "true"));
}
// On a phone only the record in brief and the timeline start open.
if (phone.matches) {
  for (const sec of document.querySelectorAll('.sec[data-phone="folded"]')) {
    if (`#${sec.id}` !== location.hash) setFold(foldOf(sec), false);
  }
}
function openTarget(hash) {
  const t = hash.length > 1 ? document.getElementById(hash.slice(1)) : null;
  const b = foldOf(t?.closest(".sec"));
  if (b) setFold(b, true);
  return t;
}
openTarget(location.hash);
for (const a of document.querySelectorAll("a[href^='#']")) {
  a.addEventListener("click", () => openTarget(a.getAttribute("href")));
}

// Section list: mark the section in view. On a narrow screen the list is a strip of chips:
// keep the current chip in view and fade whichever end has more chips.
const nav = document.querySelector(".onpage");
const strip = nav?.querySelector(".strip");
const links = [...document.querySelectorAll(".onpage a[href^='#']")].filter((a) => a.getAttribute("href").length > 1);
const targets = links.map((a) => document.getElementById(a.getAttribute("href").slice(1))).filter(Boolean);
function centre(chip, behavior) {
  if (!strip || strip.scrollWidth <= strip.clientWidth) return;
  strip.scrollTo({ left: chip.offsetLeft - (strip.clientWidth - chip.offsetWidth) / 2, behavior });
}
function ends() {
  if (!strip) return;
  const more = [];
  if (strip.scrollLeft > 4) more.push("start");
  if (strip.scrollLeft + strip.clientWidth < strip.scrollWidth - 4) more.push("end");
  nav.dataset.more = more.join(" ");
}
let marked = null;
function mark() {
  let current = targets[0];
  for (const t of targets) if (t.getBoundingClientRect().top <= 140) current = t;
  if (current === marked) return;
  marked = current;
  for (const a of links) {
    if (a.getAttribute("href") === `#${current.id}`) {
      a.setAttribute("aria-current", "true");
      centre(a, matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth");
    } else a.removeAttribute("aria-current");
  }
}
if (targets.length) { addEventListener("scroll", mark, { passive: true }); mark(); }
else if (nav?.querySelector("[aria-current]")) centre(nav.querySelector("[aria-current]"), "auto");
strip?.addEventListener("scroll", ends, { passive: true });
addEventListener("resize", ends);
ends();

// Timeline tabs.
const tlStatus = document.querySelector("[data-tl-status]");
for (const tab of document.querySelectorAll(".tab[data-kind]")) {
  tab.addEventListener("click", () => {
    for (const t of document.querySelectorAll(".tab[data-kind]")) t.setAttribute("aria-pressed", String(t === tab));
    const kind = tab.dataset.kind;
    let shown = 0;
    for (const ev of document.querySelectorAll(".tl-ev")) {
      ev.hidden = kind !== "all" && ev.dataset.kind !== kind;
      if (!ev.hidden) shown += 1;
    }
    for (const year of document.querySelectorAll(".tl-year")) {
      let any = false;
      for (let n = year.nextElementSibling; n && !n.classList.contains("tl-year"); n = n.nextElementSibling) {
        if (n.classList.contains("tl-ev") && !n.hidden) any = true;
      }
      year.hidden = !any;
    }
    for (const gap of document.querySelectorAll(".tl-gap")) gap.hidden = kind !== "all";
    if (tlStatus) tlStatus.textContent = kind === "all" ? "Showing every entry." : `Showing ${shown} of ${document.querySelectorAll(".tl-ev").length} entries: ${tab.firstChild.textContent.trim()}.`;
  });
}

// Table filter: typed words and one status. No match shows a message with a way back.
const rows = [...document.querySelectorAll("[data-row]")];
const input = document.querySelector("[data-filter]");
const count = document.querySelector("[data-count]");
const empty = document.querySelector("[data-empty]");
const chips = [...document.querySelectorAll(".tab[data-status]")];
let status = "all";
function narrow() {
  const words = (input?.value ?? "").trim().toLowerCase();
  let shown = 0;
  for (const r of rows) {
    const ok = (status === "all" || r.dataset.status === status) && (!words || r.textContent.toLowerCase().includes(words));
    r.hidden = !ok;
    if (ok) shown += 1;
  }
  const filtered = status !== "all" || words !== "";
  if (count) count.textContent = filtered ? `${shown} of ${rows.length} claims` : `All ${rows.length} claims`;
  for (const c of chips) c.setAttribute("aria-pressed", String(c.dataset.status === status));
  for (const b of document.querySelectorAll(".filterbar [data-clear]")) b.hidden = !filtered || shown === 0;
  if (empty) {
    empty.hidden = shown > 0;
    document.querySelector("[data-row]").closest(".grid").hidden = shown === 0;
  }
}
input?.addEventListener("input", narrow);
for (const c of chips) c.addEventListener("click", () => { status = c.dataset.status; narrow(); });
for (const b of document.querySelectorAll("[data-clear]")) {
  b.addEventListener("click", () => { status = "all"; input.value = ""; narrow(); input.focus(); });
}

// Printing: every fold opens, and closes again afterwards.
let closed = [];
addEventListener("beforeprint", () => {
  closed = [...document.querySelectorAll('.fold[aria-expanded="false"], details:not([open])')];
  for (const el of closed) el.matches("details") ? (el.open = true) : setFold(el, true);
});
addEventListener("afterprint", () => {
  for (const el of closed) el.matches("details") ? (el.open = false) : setFold(el, false);
});
