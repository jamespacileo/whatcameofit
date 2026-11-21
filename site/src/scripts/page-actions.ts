// The pills that pass a page on (lib/blocks.ts, pageActions; the claims site's SharePill and
// CopyButton scripts, on pairs). Each appears only where it can work. A copy is confirmed as
// everywhere on the site: the label changes and the blue dot lands in place of the icon.
const address = () => location.origin + location.pathname;
const confirm = (button: HTMLElement, label: HTMLElement, words: string) => {
  const idle = label.textContent;
  label.textContent = words;
  button.classList.add("done");
  setTimeout(() => {
    label.textContent = idle;
    button.classList.remove("done");
  }, 2000);
};
for (const actions of document.querySelectorAll<HTMLElement>("[data-page-actions]")) {
  const share = actions.querySelector<HTMLButtonElement>("[data-share]");
  const shareText = share?.querySelector<HTMLElement>("[data-share-text]");
  if (share && shareText && (navigator.share || navigator.clipboard)) {
    share.hidden = false;
    share.addEventListener("click", async () => {
      try {
        if (navigator.share) await navigator.share({ title: document.title, url: address() });
        else {
          await navigator.clipboard.writeText(address());
          confirm(share, shareText, "Link copied");
        }
      } catch {
        // The reader closed the share sheet, or copying was refused: nothing to do.
      }
    });
  }
  const copy = actions.querySelector<HTMLButtonElement>("[data-copy]");
  const copyText = copy?.querySelector<HTMLElement>("[data-copy-text]");
  const sentence = actions.querySelector<HTMLElement>("[data-share-sentence]");
  if (copy && copyText && sentence && navigator.clipboard) {
    copy.hidden = false;
    copy.addEventListener("click", async () => {
      try {
        // The address is the one the reader is at, so the sentence leads back to this page.
        await navigator.clipboard.writeText(`${sentence.textContent!.trim()} ${address()}`);
        confirm(copy, copyText, "Copied");
      } catch {
        // Copying was refused: nothing to do.
      }
    });
  }
}
