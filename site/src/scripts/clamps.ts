// Clamped text: a summary or a section's note held to a few lines, with "More" after it
// when it runs over. The clamp is the stylesheet's, from the first paint; this only adds
// the control where there is more to show, and takes it away when the text fits again.
// With no script, and on paper, the text is whole. Openspec quiet-sheet.
const boxes = [...document.querySelectorAll<HTMLElement>("[data-clamp]")];

function control(box: HTMLElement): HTMLButtonElement | null {
  const next = box.nextElementSibling;
  return next instanceof HTMLButtonElement && next.classList.contains("clamp-more") ? next : null;
}

function check(box: HTMLElement) {
  if (box.classList.contains("unclamped")) return;
  const over = box.scrollHeight > box.clientHeight + 1;
  const more = control(box);
  if (over && !more) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "text-control clamp-more";
    button.textContent = "More";
    button.setAttribute("aria-expanded", "false");
    button.setAttribute("aria-controls", box.id);
    button.addEventListener("click", () => {
      const open = box.classList.toggle("unclamped");
      button.setAttribute("aria-expanded", String(open));
      button.textContent = open ? "Less" : "More";
    });
    box.after(button);
  } else if (!over && more && box.clientHeight > 0) {
    more.remove();
  }
}

if (boxes.length > 0 && "ResizeObserver" in window) {
  // A box in a folded section has no height until its section opens; a turned phone
  // changes how many lines the words take. Both are a change of size.
  const sizes = new ResizeObserver((entries) => entries.forEach((entry) => check(entry.target as HTMLElement)));
  boxes.forEach((box, index) => {
    box.id ||= `clamp-${index + 1}`;
    sizes.observe(box);
  });
}
