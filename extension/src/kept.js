// What the reader's own browser keeps for them: the pages they checked most recently and
// the claims they follow. Pure: no browser, network or clock in here. None of this is
// ever sent anywhere; the popup reads and writes it in the browser's own storage.

/** How many checked pages are kept. An older one is dropped when a new one arrives. */
export const RECENT_CAP = 10;

/**
 * The list with `entry` at its head. A page already in the list is replaced by its
 * newest check, so one page never appears twice.
 * @param {object[]} list newest first
 * @param {{ key: string, url: string, title: string, outlet: string, at: number, answer: object }} entry
 */
export function addRecent(list, entry) {
  return [entry, ...(list ?? []).filter((kept) => kept.key !== entry.key)].slice(0, RECENT_CAP);
}

/** The name a page's address gives its outlet: the host, without a leading "www." */
export function outletOf(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "";
  }
}

/**
 * What one check found, in the little that the list needs to show it again.
 * @param {object} state the popup state that ended the check
 */
export function answerOf(state) {
  if (state.kind === "tracked") {
    return {
      kind: "tracked",
      claims: state.claims.map(({ headline, page, status }) => ({ headline, page, status })),
    };
  }
  if (state.kind === "answer") {
    const { shown } = state;
    return {
      kind: "searched",
      // An automatic search stays marked as unreviewed wherever it is shown again.
      unreviewed: shown.marked ?? null,
      lead: shown.lead ?? null,
      claims: (shown.tracked ?? []).map(({ headline, page }) => ({ headline, page })),
      records: (shown.likely ?? []).map(({ title, url }) => ({ title, url })),
    };
  }
  return { kind: "none" };
}

/** Everything an entry can open: tracked claim pages first, then registry records. */
export function candidatesOf(entry, site) {
  const { answer } = entry;
  return [
    ...(answer.claims ?? []).map((claim) => ({ title: claim.headline, url: site.url + claim.page, status: claim.status ?? null })),
    ...(answer.records ?? []).map((record) => ({ title: record.title, url: record.url, status: null })),
  ];
}

const sameClaim = (page) => (kept) => kept.page === page;

export function isFollowed(follows, page) {
  return (follows ?? []).some(sameClaim(page));
}

/** The followed list with this claim in it, remembered as it stands now. */
export function follow(follows, claim) {
  const { headline, page, status, place = null } = claim;
  return [{ headline, page, status, place }, ...(follows ?? []).filter((kept) => kept.page !== page)];
}

export function unfollow(follows, page) {
  return (follows ?? []).filter((kept) => kept.page !== page);
}

function claimAt(index, page) {
  return Object.values(index?.claims ?? {}).find((claim) => claim.page === page) ?? null;
}

/**
 * Each followed claim beside how it stands in the lookup file now.
 * `changed` is true when its status or its place differs from the one last seen;
 * `gone` when the claim is no longer published.
 */
export function followedNow(follows, index) {
  return (follows ?? []).map((kept) => {
    const now = claimAt(index, kept.page);
    if (!now) return { ...kept, gone: true, changed: false, was: null };
    const changed = now.status !== kept.status || (now.place ?? null) !== (kept.place ?? null);
    return {
      headline: now.headline,
      page: kept.page,
      status: now.status,
      place: now.place ?? null,
      gone: false,
      changed,
      was: changed ? kept.status : null,
    };
  });
}

/** The followed list once the reader has seen how one claim now stands. */
export function acknowledged(follows, index, page) {
  return (follows ?? []).map((kept) => {
    if (kept.page !== page) return kept;
    const now = claimAt(index, page);
    return now ? { headline: now.headline, page, status: now.status, place: now.place ?? null } : kept;
  });
}
