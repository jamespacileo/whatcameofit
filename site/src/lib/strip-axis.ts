// The one time scale every record strip on the site is drawn on (openspec
// record-strip), fixed at build from the export. Null when the export holds no day the
// registries were last checked: with no end there is no axis, and no strip is drawn.
import { data } from "./export";
import { axisStart, notches } from "./record-strip.ts";

const lastChecked = data.last_checked_at?.slice(0, 10) ?? null;

export const STRIP_AXIS =
  lastChecked && data.claims.length > 0
    ? (() => {
        const startYear = axisStart(data.claims);
        return { startYear, lastChecked, notches: notches(startYear, lastChecked) };
      })()
    : null;
