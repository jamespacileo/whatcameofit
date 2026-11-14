// The two notices that accompany every status, on the site's footer and in lookup.json.
export const NOTICES = [
  "This site gives no medical advice and recommends no treatment.",
  "A registered clinical trial is not a treatment option. Talk to a clinician about your own care.",
] as const;

// Shown on every page of a preview build. The pipeline no longer writes a preview
// export; an older export can still be one.
export const PREVIEW_NOTE =
  "Preview, not for publication. Some pages here were put together by software from public records and have not yet been checked by a person.";

// Shown with a claim no person checked: approved by rule, loaded from a seed file or
// decided by an AI assistant.
export const UNCHECKED_NOTE =
  "This page has not yet been checked by a person. It was put together by software from the public records it links to.";
