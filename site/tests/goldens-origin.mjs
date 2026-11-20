// The site's own origin for the goldens (tests/goldens.mjs), set before any renderer reads the
// site's configuration: an embed's links and a listing's trail carry it, so a build for another
// address (a preview's SITE_URL) neither fails nor rewrites them. Imported first.
process.env.SITE_URL = "https://whatcameofit.com";
