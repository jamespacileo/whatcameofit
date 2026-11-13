// What the extension's background check decides: which followed claims to tell the
// reader about, and which reminders are due. Pure: no browser, network or clock in
// here. Behaviour: openspec reader-follow-up, "Notification of a change" and
// "Reminder in the extension".
import { followedNow } from "./kept.js";

/** How often the background check refreshes the lookup file, in minutes. */
export const REFRESH_MINUTES = 12 * 60;

const REMIND = "remind:";

/** What a change notification says. Plain words, never a verdict. */
export function changeMessage(change) {
  return { title: change.headline, message: `Was: ${change.was}. Now: ${change.status}.` };
}

/** What a reminder notification says, with the status as last fetched. */
export function reminderMessage(reminder, status) {
  return {
    title: reminder.headline,
    message: status ? `Time to look again. Now: ${status}.` : "Time to look again.",
  };
}

/**
 * The followed claims whose change the reader has not yet been told about, and the
 * record of what has been told. A change is told once: the same claim moving to the
 * same status and place is not told again, though the popup keeps marking it until
 * the reader opens it. A claim no longer published is not notified; the popup says so.
 * @param {object[]} follows the followed list as kept
 * @param {object} index the lookup file
 * @param {Record<string, string>} told page to the status and place last told
 */
export function changesToTell(follows, index, told = {}) {
  const now = followedNow(follows, index);
  const tell = [];
  const record = {};
  for (const claim of now) {
    if (claim.gone || !claim.changed) continue;
    const mark = `${claim.status}|${claim.place ?? ""}`;
    record[claim.page] = mark;
    if (told[claim.page] !== mark) tell.push(claim);
  }
  return { tell, told: record };
}

/** The alarm name for a reminder, and the reminder an alarm name stands for. */
export function alarmName(reminder) {
  return `${REMIND}${reminder.page}|${reminder.date}`;
}

export function reminderOf(name, reminders) {
  if (!name.startsWith(REMIND)) return null;
  return (reminders ?? []).find((reminder) => alarmName(reminder) === name) ?? null;
}

/** When a reminder falls due, as a time: nine in the morning, local, on its day. */
export function dueAt(reminder) {
  const [year, month, day] = reminder.date.split("-").map(Number);
  return new Date(year, month - 1, day, 9).getTime();
}

/**
 * The alarms to add and to clear so that exactly the kept reminders have one each.
 * @param {object[]} reminders as kept
 * @param {string[]} existing names of the reminder alarms already set
 */
export function alarmsFor(reminders, existing) {
  const wanted = new Map((reminders ?? []).map((reminder) => [alarmName(reminder), reminder]));
  const have = new Set(existing.filter((name) => name.startsWith(REMIND)));
  return {
    add: [...wanted].filter(([name]) => !have.has(name)).map(([name, reminder]) => ({ name, when: dueAt(reminder) })),
    clear: [...have].filter((name) => !wanted.has(name)),
  };
}

/** The reminders kept with this claim's set for `date`; one per claim. */
export function remind(reminders, claim, date) {
  const { headline, page } = claim;
  return [...(reminders ?? []).filter((kept) => kept.page !== page), { headline, page, date }];
}

export function unremind(reminders, page) {
  return (reminders ?? []).filter((kept) => kept.page !== page);
}

/** Six months or a year from `today` (YYYY-MM-DD), clamped to the month's last day. */
export function reminderDay(choice, today) {
  const months = choice === "year" ? 12 : 6;
  const [year, month, day] = today.split("-").map(Number);
  const target = new Date(Date.UTC(year, month - 1 + months, 1));
  const last = new Date(Date.UTC(target.getUTCFullYear(), target.getUTCMonth() + 1, 0)).getUTCDate();
  target.setUTCDate(Math.min(day, last));
  return target.toISOString().slice(0, 10);
}
