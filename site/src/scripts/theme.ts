// The masthead's appearance switch (layouts/Base.astro). With no choice stored the
// stylesheet follows the device, live. A press always changes the look: to the device's
// own look clears the stored choice, so the page follows the device again; to the other
// look stores it in this browser.
type Look = "light" | "dark";

const root = document.documentElement;
const device = matchMedia("(prefers-color-scheme: dark)");
const button = document.querySelector<HTMLButtonElement>(".masthead .theme");
const status = document.querySelector<HTMLElement>(".masthead .theme-status");

const stored = (): Look | null =>
  root.dataset.theme === "light" || root.dataset.theme === "dark" ? root.dataset.theme : null;
const deviceLook = (): Look => (device.matches ? "dark" : "light");
const showing = (): Look => stored() ?? deviceLook();
const other = (look: Look): Look => (look === "dark" ? "light" : "dark");

const label = () => {
  if (!button) return;
  // A kept look says so, because it is why the page differs from the device; the press
  // then returns to the device.
  const kept = stored();
  const text = kept && kept !== deviceLook()
    ? `Switch to ${other(kept)} appearance, as your device. ${kept === "dark" ? "Dark" : "Light"} is kept in this browser.`
    : `Switch to ${other(showing())} appearance`;
  button.setAttribute("aria-label", text);
  button.title = text;
};

// Colours that ease on hover would ease through a theme change at different speeds.
const withoutTransitions = (change: () => void) => {
  root.classList.add("theme-switching");
  change();
  requestAnimationFrame(() => requestAnimationFrame(() => root.classList.remove("theme-switching")));
};

// Draws a look on this page only. Never writes storage: another tab's change arrives
// here, and writing it back would echo between tabs.
const apply = (look: Look | null) =>
  withoutTransitions(() => {
    if (look) root.dataset.theme = look;
    else delete root.dataset.theme;
    label();
  });

button?.addEventListener("click", () => {
  const next = other(showing());
  const keep = next === deviceLook() ? null : next;
  try {
    if (keep) localStorage.setItem("theme", keep);
    else localStorage.removeItem("theme");
  } catch {}
  apply(keep);
  if (status) {
    status.textContent = keep
      ? `${next === "dark" ? "Dark" : "Light"} appearance, kept in this browser.`
      : `${next === "dark" ? "Dark" : "Light"} appearance, as your device.`;
  }
});

device.addEventListener("change", label);
addEventListener("storage", (event) => {
  if (event.key !== "theme" && event.key !== null) return;
  const value = event.key === null ? null : event.newValue;
  apply(value === "light" || value === "dark" ? value : null);
});
label();
