// Small line icons; the adjacent label always carries their meaning.
const paths = {
  search: "M21 21l-5-5 M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0",
  target: "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8 M12 2v3 M12 19v3 M2 12h3 M19 12h3 M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16",
  phase: "M9 3h6 M10 3v6L4 19q-1 2 2 2h12q3 0 2-2L14 9V3 M7 15h10",
  people: "M9 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8 M2 21v-3a6 6 0 0 1 12 0v3 M17 4a4 4 0 0 1 0 8 M17 15a5 5 0 0 1 5 5v1",
  info: "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20 M12 11v6 M12 7v.1",
  chevron: "M6 9l6 6 6-6",
  refresh: "M20 7a9 9 0 1 0 1 8 M20 2v5h-5",
  image: "M4 3h16q1 0 1 1v16q0 1-1 1H4q-1 0-1-1V4q0-1 1-1 M3 17l6-6 5 5 3-3 4 4 M16 7h.1",
  settings: "M4 7h16 M4 17h16 M8 4v6 M16 14v6",
  clock: "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20 M12 6v6l4 2",
  book: "M4 3h12q3 0 3 3v15H6a3 3 0 0 1 0-6h13 M4 3v15 M8 7h7 M8 11h7",
};

export function icon(name) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  for (const [key, value] of Object.entries({ viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", "stroke-width": "1.8", "stroke-linecap": "round", "stroke-linejoin": "round", "aria-hidden": "true", focusable: "false", class: "icon" })) svg.setAttribute(key, value);
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", paths[name]);
  svg.append(path);
  return svg;
}
