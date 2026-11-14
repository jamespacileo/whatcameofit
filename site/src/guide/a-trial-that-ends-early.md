---
shelf: research
order: 6
title: A trial that ends early
answer: A trial has ended early when its registry record is marked terminated, meaning it stopped after it began and will not start again, or withdrawn, meaning it stopped before anyone was enrolled.
rule: how-a-status-is-set
on_site: A trial that was terminated or withdrawn does not count toward a status. If every registered trial of the treatment for the condition is in one of those two states, the status is “Trials ended early”.
applies: ended-early
sources:
  - name: "ClinicalTrials.gov, Glossary Terms"
    url: https://clinicaltrials.gov/study-basics/glossary
    checked: "2026-11-14"
  - name: "ClinicalTrials.gov, Protocol Registration Data Element Definitions"
    url: https://clinicaltrials.gov/policy/protocol-definitions
    checked: "2026-11-14"
  - name: "International Council for Harmonisation, E9: Statistical Principles for Clinical Trials"
    url: https://database.ich.org/sites/default/files/E9_Guideline.pdf
    checked: "2026-11-14"
  - name: "U.S. Food and Drug Administration, The Drug Development Process, Step 3: Clinical Research"
    url: https://www.fda.gov/patients/drug-development-process/step-3-clinical-research
    checked: "2026-11-14"
related: [trials-ended-early, trial-registry, primary-endpoint, no-signal]
checked: false
---

## In the records

ClinicalTrials.gov gives each study a recruitment status. Terminated: the study stopped early and will not start again. Withdrawn: it stopped early, before enrolling its first participant. Suspended: it stopped early but may start again. Completed: it ended normally.

For a study that stopped before its planned end, the sponsor can fill in a field named “Why Study Stopped”: a short explanation in the sponsor's own words, with no fixed list of reasons.

The guideline ICH E9 describes planned looks at the data while a trial runs. A trial may be stopped at one if the treatment's superiority is clearly established, if showing a relevant difference has become unlikely, or if unacceptable adverse effects are apparent. The United States regulator can also place a hold that delays or stops a study.

## What it does not tell you

The status describes the trial, not the treatment. On the grounds above, a trial can stop early because the treatment was doing clearly better as well as because it was not.

It does not give the reason unless the sponsor wrote one, and that note is the sponsor's own.

“Withdrawn” here is about a study. It does not mean a medicine was taken off the market.

A status of “Unknown” is different again: the registry assigns it when a record has gone unverified for two years.
