// Retain the existing list addresses if a generated list outgrows a static asset.
export const RELEASE_SLUG = "[a-z0-9]+(?:-[a-z0-9]+)*";
export const RELEASE_ROWS = /^rows\/(?:on-this-day\/)?[a-z0-9.-]+\.txt$/;
const topicPage = new RegExp(`^topic/${RELEASE_SLUG}/index\\.html$`);
export const canMoveLargeReleaseFile = (name) => RELEASE_ROWS.test(name) || topicPage.test(name);
