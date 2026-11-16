// The masthead's appearance control (layouts/Base.astro). With no choice stored the
// stylesheet follows the device, live; a press steps through the three choices, the
// first press always to the look the page is not showing.
type Choice = "device" | "light" | "dark";

const root = document.documentElement;
const device = matchMedia("(prefers-color-scheme: dark)");
const button = document.querySelector<HTMLButtonElement>(".masthead .theme");

const NAMES: Record<Choice, string> = { device: "as your device", light: "light", dark: "dark" };

const current = (): Choice =>
  root.dataset.theme === "light" || root.dataset.theme === "dark" ? root.dataset.theme : "device";

const order = (): Choice[] => (device.matches ? ["device", "light", "dark"] : ["device", "dark", "light"]);

const next = (): Choice => {
  const choices = order();
  return choices[(choices.indexOf(current()) + 1) % choices.length];
};

const label = () => {
  if (!button) return;
  const now = current();
  const showing = now === "device" ? ` (${device.matches ? "dark" : "light"})` : "";
  const text = `Appearance: ${NAMES[now]}${showing}. Change to ${NAMES[next()]}.`;
  button.setAttribute("aria-label", text);
  button.title = text;
};

const choose = (choice: Choice) => {
  if (choice === "device") delete root.dataset.theme;
  else root.dataset.theme = choice;
  try {
    if (choice === "device") localStorage.removeItem("theme");
    else localStorage.setItem("theme", choice);
  } catch {}
  label();
};

button?.addEventListener("click", () => choose(next()));
// The device's own change moves the page when no choice is stored, and the label with it.
device.addEventListener("change", label);
// A choice made in another tab of the site.
addEventListener("storage", (event) => {
  if (event.key !== "theme") return;
  const value = event.newValue;
  choose(value === "light" || value === "dark" ? value : "device");
});
label();
