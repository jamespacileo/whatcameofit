// Mock behaviour only: icons, the band switch, the section list's current place,
// the timeline's tabs and the table filter. None of this is the site's script.
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

// Band switch: deep navy or the pale panel blue.
const hero = document.querySelector(".hero");
const store = { get: () => { try { return localStorage.getItem("mock-band"); } catch { return null; } }, set: (v) => { try { localStorage.setItem("mock-band", v); } catch {} } };
function band(value) {
  hero?.classList.toggle("navy", value === "navy");
  for (const b of document.querySelectorAll("[data-band]")) b.setAttribute("aria-pressed", String(b.dataset.band === value));
}
band(store.get() ?? "navy");
for (const b of document.querySelectorAll("[data-band]")) b.addEventListener("click", () => { band(b.dataset.band); store.set(b.dataset.band); });

// Section list: mark the section in view, and open a folded section when its link is pressed.
const links = [...document.querySelectorAll(".onpage a[href^='#']")];
const targets = links.map((a) => document.getElementById(a.getAttribute("href").slice(1))).filter(Boolean);
function mark() {
  let current = targets[0];
  for (const t of targets) if (t.getBoundingClientRect().top <= 140) current = t;
  for (const a of links) {
    if (current && a.getAttribute("href") === `#${current.id}`) a.setAttribute("aria-current", "true");
    else a.removeAttribute("aria-current");
  }
}
if (targets.length) { addEventListener("scroll", mark, { passive: true }); mark(); }
for (const a of document.querySelectorAll("a[href^='#']")) {
  a.addEventListener("click", () => {
    const t = document.getElementById(a.getAttribute("href").slice(1));
    if (t?.tagName === "DETAILS") t.open = true;
  });
}

// Timeline tabs.
for (const tab of document.querySelectorAll(".tab[data-kind]")) {
  tab.addEventListener("click", () => {
    for (const t of document.querySelectorAll(".tab[data-kind]")) t.setAttribute("aria-pressed", String(t === tab));
    const kind = tab.dataset.kind;
    for (const ev of document.querySelectorAll(".tl-ev")) ev.hidden = kind !== "all" && ev.dataset.kind !== kind;
    for (const year of document.querySelectorAll(".tl-year")) {
      let any = false;
      for (let n = year.nextElementSibling; n && !n.classList.contains("tl-year"); n = n.nextElementSibling) {
        if (n.classList.contains("tl-ev") && !n.hidden) any = true;
      }
      year.hidden = !any;
    }
    for (const gap of document.querySelectorAll(".tl-gap")) gap.hidden = kind !== "all";
  });
}

// Table filter: typed words and one status.
const rows = [...document.querySelectorAll("[data-row]")];
const input = document.querySelector("[data-filter]");
const count = document.querySelector("[data-count]");
let facet = "all";
function narrow() {
  const words = (input?.value ?? "").trim().toLowerCase();
  let shown = 0;
  for (const r of rows) {
    const ok = (facet === "all" || r.dataset.status === facet) && (!words || r.textContent.toLowerCase().includes(words));
    r.hidden = !ok;
    if (ok) shown += 1;
  }
  if (count) count.textContent = shown === rows.length ? `All ${rows.length} claims` : `${shown} of ${rows.length} claims`;
}
input?.addEventListener("input", narrow);
for (const f of document.querySelectorAll(".facet")) {
  f.addEventListener("click", () => {
    facet = f.getAttribute("aria-pressed") === "true" ? "all" : f.dataset.status;
    for (const g of document.querySelectorAll(".facet")) g.setAttribute("aria-pressed", String(g.dataset.status === facet));
    narrow();
  });
}
