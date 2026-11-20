// Dates as the site writes them.

const NBSP = "\u00a0";
/** The months as the site's dates and the status card write them. */
export const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function formatDate(isoDate: string | null): string {
  if (!isoDate) return "";
  const [year, month, day] = isoDate.slice(0, 10).split("-").map(Number);
  return `${day}${NBSP}${MONTHS[month - 1]}${NBSP}${year}`;
}
