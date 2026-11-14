// The site's wording for the organisations a claim names, checked against openspec
// site-publishing: codes are worded here, a code with no wording is named, and the
// wording states a role and a location, never a judgement.
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  NOT_IDENTIFIED,
  ORGANISATIONS_NOTE,
  assertNoStandingWords,
  identifiedText,
  kindsText,
  orderOrganisations,
  publisherOf,
  publisherText,
  roleText,
  unwordedOrganisationCodes,
  websiteHost,
} from "../src/lib/organisations.ts";

const organisation = (name, roles, record = null) => ({
  name,
  identified: record !== null,
  record,
  roles: roles.map((role) => ({ article_urls: [], trial_ids: [], ...role })),
});

const record = (extra = {}) => ({
  source: "ror",
  external_id: "00example1",
  url: "https://ror.org/00example1",
  name: "Example University",
  kinds: ["education"],
  country: "United Kingdom",
  website: "https://www.example.ac.uk/",
  score: 0.97,
  read_at: "2026-11-14T09:00:00Z",
  ...extra,
});

test("a role says what the source states, with how many reports or trials", () => {
  assert.equal(roleText({ role: "named_in_report", article_urls: ["a"], trial_ids: [] }), "Named in the report");
  assert.equal(roleText({ role: "named_in_report", article_urls: ["a", "b"], trial_ids: [] }), "Named in 2 reports");
  // Which report named it was not recorded: the page says so rather than guess one.
  assert.equal(
    roleText({ role: "named_in_report", article_urls: [], trial_ids: [] }),
    "Named in one of this claim’s reports",
  );
  assert.equal(roleText({ role: "sponsor", article_urls: [], trial_ids: ["N1"] }), "Sponsor of 1 trial");
  assert.equal(roleText({ role: "sponsor", article_urls: [], trial_ids: ["N1", "N2", "N3"] }), "Sponsor of 3 trials");
});

test("kinds, the website and the identification are worded from the record", () => {
  assert.equal(kindsText(["education", "funder"]), "Education, Funder");
  assert.equal(websiteHost("https://www.example.ac.uk/"), "example.ac.uk");
  assert.equal(
    identifiedText(record()),
    "Identified in the Research Organization Registry (ROR), which scores the name match 97%.",
  );
});

test("Scenario: Well-known and unknown organisations together", () => {
  const ordered = orderOrganisations([
    organisation("Zed Clinic", [{ role: "sponsor", trial_ids: ["N1"] }]),
    organisation("a large university", [{ role: "sponsor", trial_ids: ["N2"] }], record()),
    organisation("Small Lab", [{ role: "named_in_report", article_urls: ["u"] }]),
    organisation("Big Hospital", [{ role: "sponsor" }, { role: "named_in_report" }]),
  ]);
  // By role, then by name: reports first, sponsors second, nothing ranked by size.
  assert.deepEqual(
    ordered.map((o) => o.name),
    ["Big Hospital", "Small Lab", "a large university", "Zed Clinic"],
  );
});

test("Scenario: University press release", () => {
  const university = organisation("Kyoto University", [{ role: "named_in_report" }], record({ url: "https://ror.org/02kpeqv85" }));
  assert.equal(publisherOf([university], "https://ror.org/02kpeqv85"), university);
  assert.equal(publisherText("Kyoto University"), "This report is on Kyoto University’s website.");
});

test("Scenario: Newspaper report", () => {
  const university = organisation("Kyoto University", [{ role: "named_in_report" }], record());
  assert.equal(publisherOf([university], null), null);
  assert.equal(publisherOf([university], undefined), null);
  assert.equal(publisherOf([university], "https://ror.org/somewhere-else"), null);
});

test("Scenario: Kind code without site wording", () => {
  assert.deepEqual(
    unwordedOrganisationCodes([
      organisation("A", [{ role: "named_in_report" }], record({ kinds: ["education"] })),
      organisation("B", [{ role: "sponsor" }]),
    ]),
    [],
  );
  assert.deepEqual(
    unwordedOrganisationCodes([
      organisation("A", [{ role: "funded_it" }], record({ kinds: ["think_tank"], source: "elsewhere" })),
    ]),
    ["organisation kind: think_tank", "organisation registry: elsewhere", "organisation role: funded_it"],
  );
});

test("wording that vouches for or judges an organisation stops the build", () => {
  assert.throws(() => assertNoStandingWords(["The university endorses this treatment."]), /endorses/);
  assert.throws(() => assertNoStandingWords(["This report is promotional."]), /promotional/);
  assert.throws(() => assertNoStandingWords(["A trusted sponsor."]), /trusted/);
  assert.doesNotThrow(() => assertNoStandingWords([publisherText("Example University"), NOT_IDENTIFIED]));
});

test("the section says the registry identifies an organisation and does not verify its part", () => {
  assert.match(ORGANISATIONS_NOTE, /identifies an organisation from its name; it does not verify the organisation’s part in this claim/);
  assert.match(NOT_IDENTIFIED, /Not matched to a registry record/);
});
