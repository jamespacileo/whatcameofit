// The records the video shows. Every value is copied from the site's published
// export (site/data/published-export.json, registries checked 13 November 2026) and
// from the site's own wording (site/src/lib/status.ts). Nothing here is invented:
// a headline is the outlet's own title, shown in quotation marks with the outlet named.

/** Claim `tooth-regrowth-usag1`. */
export const USAG1 = {
  headline: "Antibody against USAG-1 regrows teeth in mice",
  topic: "Mouth and teeth",
  intervention: "Anti-USAG-1 antibody",
  alsoCalled: "TRG035",
  indication: "Congenital tooth agenesis",
  firstReported: "31 March 2021",
  evidenceAtFirst: "Animal study",
  article: {
    title: "New drug to regenerate lost teeth",
    outlet: "Kyoto University",
    date: "31 March 2021",
    address: "kyoto-u.ac.jp/en/research-news/2021-03-31",
  },
  status: "Phase 1 trial",
  gloss: "Early trial in people, checking safety",
  meaning: "The furthest trial that has started is a Phase 1 trial.",
  place: 2,
  latestRecord: "3 October 2025",
  promise: "Tests in other animals such as pigs and dogs next.",
  records: [
    {
      year: "2024",
      day: "8 Oct",
      what: "Trial registered",
      detail: "Phase 1: a single dose of TRG035 in healthy adults",
      source: "jRCT",
    },
    {
      year: "2025",
      day: "3 Oct",
      what: "Trial completed",
      detail: "Shown as complete in the registry",
      source: "jRCT",
    },
  ],
} as const;

/** Claim `whole-tooth-germ-splitting`. */
export const GERM_SPLITTING = {
  article: { title: "Multiplying teeth", outlet: "RIKEN", date: "18 December 2015" },
  status: "Preclinical only",
  gloss: "No trial in people on record",
  meaning: "No clinical trial was found in the registries checked.",
  place: 0,
  note: "No signal for 10 years",
  firstYear: 2015,
  lastYear: 2025,
} as const;

/** Claim `whole-tooth-pulp-cell-tooth-germ`: its report's title, for the opening. */
export const PULP_GERM = {
  article: { title: "Regrowing Teeth", outlet: "Technische Universität Berlin (via idw)", date: "24 July 2019" },
} as const;

export const CHECKED = "Registries checked November 2026";
export const SOURCES = ["ClinicalTrials.gov", "Europe PMC", "Crossref"] as const;
export const NOTICES = [
  "This site gives no medical advice and recommends no treatment.",
  "A registered clinical trial is not a treatment option.",
] as const;
export const HOST = "whatcameofit.com";
