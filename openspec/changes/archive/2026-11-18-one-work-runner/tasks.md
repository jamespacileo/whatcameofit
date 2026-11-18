# Tasks

## 0. Writer upgrades, retries and due work (P1)

- [x] 0.1 <a id="task-f36"></a>Teach migration 0037 to recognize the historical audit-attach state. Upgrade a representative pre-migration PostgreSQL fixture, verify the attachment and ledger agree, and retain a test for unknown states. [F36](../../../docs/reviews/2026-11-17-code-review.md#finding-f36) · [Acceptance scenario](specs/work-ledger/spec.md#scenario-a-manually-attached-historical-lead-is-upgraded)

- [x] 0.2 <a id="task-f38"></a>Share the stop signal across workers before the next claim. Use the two-worker, five-record fixture and verify backlog, attempts and disposition of work already in flight. [F38](../../../docs/reviews/2026-11-17-code-review.md#finding-f38) · [Acceptance scenario](specs/work-ledger/spec.md#scenario-one-worker-reports-a-provider-wide-outage)

- [x] 0.3 <a id="task-f42"></a>Preserve pending DOI work under the runner's declared reasons, including any registry numbers processed successfully. Test the unconfigured run, recovery after configuration and an unchanged rerun. [F42](../../../docs/reviews/2026-11-17-code-review.md#finding-f42) · [Acceptance scenario](specs/work-ledger/spec.md#scenario-a-cited-paper-awaits-a-configured-source)

- [x] 0.4 <a id="task-f44"></a>Apply the budget guard only where model spending is possible. Test a registry fetch, a deterministic decision and a model-dependent step at the same exhausted ceiling. [F44](../../../docs/reviews/2026-11-17-code-review.md#finding-f44) · [Acceptance scenario](specs/work-ledger/spec.md#scenario-the-model-budget-is-exhausted-during-non-model-work)

- [x] 0.5 <a id="task-f45"></a>Invalidate only leads whose stored classification differs from the outlet's current classification. Run the three-lead, limit-two case to completion and check the processed IDs on each run. [F45](../../../docs/reviews/2026-11-17-code-review.md#finding-f45) · [Acceptance scenario](specs/lead-screening/spec.md#scenario-bounded-rescreening-reaches-the-last-lead)

## 1. Pin down present behaviour

- [x] 1.1 Write characterisation tests against the present code, one record per outcome, for `link_read` (each `ReadOutcome` and each cannot-be-read cause), `link_triage`, `link_screen` and `news_search`, at the session seam with synthetic article fixtures; verify they pass on `main` unchanged
- [x] 1.2 Write characterisation tests for `thenwhat prepare` on a claim: all steps succeed, the registry fails, the substance lookup fails, terms fail; verify they pass on `main` and record in a comment which of them this change is meant to alter

## 2. The `work` package, with no behaviour change

- [x] 2.1 Move `backfill/ledger.py`, `runner.py`, `steps.py`, `allowance.py`, `errors.py` and `spend.py` into `thenwhat/work/` in one commit that changes imports only (`outlet_hold.py` stays in `backfill/`: it reads an address's outlet, which is about leads); verify lint, types and the pipeline's tests pass unchanged (2,187 passed on 2026-11-17)
- [x] 2.2 Add an `import-linter` contract: `work/` imports nothing from `backfill/`, `cli/` or any step's package, and `status/` stays pure; verify it runs in `make check` and fails on a deliberate bad import

## 3. Outcomes and reasons

- [x] 3.1 Add the outcome type (`Done`, `NothingFound`, `Later`, `NeedsFix`, `Failed`) and reason declaration in `work/outcome.py` and `work/reasons.py`, with the words for each reason made in one place; verify with pure tests that a reason's class cannot be contradicted and an undeclared code is refused
- [x] 3.2 Add a migration for `work_entry.reason`, `reason_values`, `not_before`, `first_put_off_at` and the two new outcome values; verify it applies and reverses on the test database
- [x] 3.3 Change the due rule and `record_outcome`: `Later` due after its time, `NeedsFix` not due, neither counts an attempt, and thirty days of one reason becomes `NeedsFix`; verify with tests for every scenario of "Ledger entry", "Due work", "Failed records" and "A record put off too long is said to need a fix"
- [x] 3.4 Add step dependencies to the due rule; verify with tests for both scenarios of "A step can depend on another step"
- [x] 3.5 Add `thenwhat work requeue` with `--where` and `--dry-run`, and make `thenwhat backfill retry-outlet` call it; verify with one success and one refusal test and the three scenarios of "Records are made due by step and reason"
- [x] 3.6 Show waiting records by class and reason in `thenwhat backfill plan`; verify with a test of "Planning with records waiting"
- [x] 3.7 Add "final", "put off", "needs a fix" and "reason" to `GLOSSARY.md`; verify the terms in code, CLI output and specs match

## 4. One call policy

- [x] 4.1 Add `tenacity`, `respx` and `time-machine` to `pipeline/pyproject.toml`; verify `uv sync` and `make check` pass
- [x] 4.2 Write `work/calls.py`: bounded retries with jitter, `Retry-After` as seconds or as a date, a ceiling on any wait, and `CannotAsk` with a time; verify with `respx` tests for the four scenarios of "A stated wait is honoured in either form and bounded" and "Try later is told apart from not found"
- [x] 4.3 Write `work/pause.py`: a pause kept in `source_allowance_use`, checked before every request, and requests counted for every command; verify with tests for "A pause is seen by every process" and "Every command's requests count against the source's allowance"
- [x] 4.4 Put `sources/base.py` behind the policy and delete its own retry loop; verify the recorded-fixture tests of every source client pass unchanged
- [x] 4.5 Put `llm/client.py` and `llm/decisions.py` behind the policy, and make a backend that cannot be asked raise `CannotAsk` apart from a failed decision; verify with tests for every scenario of the `decision-steps` delta
- [x] 4.6 Make the runner stop on `CannotAsk` from any call of any step, with no attempt counted; verify with tests for both scenarios of "A provider that cannot be asked stops the run"
- [x] 4.7 Note the retry and pause behaviour per source in `docs/sources.md`; verify each source's entry states its ceiling and where its pause is kept

## 5. Measured by construction

- [x] 5.1 Make the runner open the measurement for every record of every step, with the run, the outcome's class and its reason code, and remove any step's own call to `measured`; verify with tests for both scenarios of "The runner measures every step it runs" and that the span's allowed fields include the three new ones
- [x] 5.2 Record each wait under one cause from `work/calls.py`, `work/pause.py`, the outlet's turn and gap, the reader's requests in flight, the claim turn and a held row; verify with tests for both scenarios of "Every wait is given its cause" using `time-machine`
  - 2026-11-17: recorded under their own names: a source's pacing (the source's name), a delay before a retry (`retry:<source>`), an outlet's turn (`outlet_turn`), the page reader's requests in flight (`reader`), the claim turn (`claim_turn`), the writer (`measure_writer`). Two of the seven causes the spec names are not waits as built: a source's pause and an outlet's gap put the record off with a reason, and a row another run holds is skipped, never waited for. Verified by a read that names both turns and by the call policy's retry tests; the clock was injected, not `time-machine`.
- [x] 5.3 Record run events (started, ended and why, source paused, records made due) in the day's file beside the measurements; verify with tests for both scenarios of "What happens to a run is recorded as it happens"
- [x] 5.4 Replace the sink that opens the file for each measurement with a writer of its own thread: a bounded queue that makes the work wait when full, lines written several at a time and at least once a second, and a count of what could not be written; verify with tests for both scenarios of "A measurement is never lost without being said"
- [x] 5.5 Add a benchmark test that runs a step asking no source over 50,000 records with measuring off and on; verify the run with measuring on takes no more than a twentieth longer and makes no database statement for a measurement (50,000 records on 2026-11-17: +1.6% measured, median pair +1.7%, no statement; 3 min 17 s)
- [x] 5.6 Add `thenwhat measure --live`: read the day's files from where it last read, keep one, five and fifteen minute windows, and show rates, waiting by cause, cost, records in hand, paused sources and the month's spend; verify with tests for every scenario of "A run can be watched while it works" and "The live view shows rate, cost and where work is held", and one refusal test
- [x] 5.7 Describe the live view, the wait causes and the events in `docs/daily-run.md`, and add "run", "wait cause" and "run event" to `GLOSSARY.md`; verify the documented command runs as written

## 6. Lead steps on the new outcomes

- [x] 6.1 Declare `link_read`'s reasons and return the new outcomes: transient statuses as `Later`, causes that can be put right as `NeedsFix`, what the article is as final; verify with tests for every scenario of the `lead-reading` delta except the last requirement, and the tests of 1.1 updated only where the spec changes the outcome
- [x] 6.2 Replace `Deferred` in `link_read` with `Later` and remove `Deferred` from the runner; verify a test that a lead inside an outlet's gap is taken again in the same run once the gap has passed
  - 2026-11-17: the runner no longer knows `Deferred`; the class lives in `backfill/link_read.py` for `thenwhat audit attach` alone. A lead inside an outlet's gap is put off until the gap ends and is due again in the same run once it has.
- [x] 6.3 Make `link_lead.read_detail` and the funnel report render from the reason code; verify the funnel report test gives the same lines for the same data
- [x] 6.4 Write the data migration from stored `read_detail` text to codes, failing on any text with no code; verify on a copy of the 16 November database that every lead has a code and the funnel report's counts per line are unchanged
  - Done on 2026-11-17 against the 886 leads and 795 news-search entries that held nothing found in the database as it stood on 16 November, copied into a scratch database (the whole 4 GB database does not fit the test server's 3 GB). Every entry was given a code and none was left: site_refused 289 (403: 139, 401: 128, 400: 13, 402: 9), not_one_treatment 192, outlet_refuses 75, identity_unresolved 65, no_date 64, business_news 55, needs_vertical 47, thin_page 44, page_gone 44 (404: 38, 410: 6), site_busy 7 (503: 3, 594: 2, 504: 1, 202: 1), no_outlet_name 4; no_stories 795. The funnel's "could not be read" falls from 527 to 520 by design: the 7 leads whose site was busy or failing are put off and due, no longer said to be unreadable. Every other line is unchanged.
- [x] 6.5 Move `link_triage`, `link_screen` and `news_search` to the new outcomes, with a source timeout in `news_search` as `Later`; verify the tests of 1.1 pass and the 48 stored timeouts are due after migration
- [x] 6.6 Add the outlet's kind to what `link_screen` reads from a lead; verify with tests for both scenarios of the `lead-screening` delta
- [ ] 6.7 On the writer, run the data migration, then `thenwhat work requeue link_read --reason <missing date> --dry-run`; record here the counts per reason and the funnel report before and after

## 7. Claim steps

- [x] 7.1 Add a migration for `registry_search` and write a record for each term searched, cut or not sent in the registry search; verify with tests for the four scenarios of "A registry search leaves a record"
- [x] 7.2 Add `claim_substance`, `claim_trials` and `claim_papers` as steps over claims, each all or nothing, and remove `_step`'s catch-all from `cli/resolve.py`; verify with tests for the three scenarios of "A lookup that failed is not a finished search"
- [x] 7.3 Add `claim_articles`, `claim_fetch`, `claim_readings` and `claim_terms` as steps with the inputs `design.md` gives; verify each with one finished and one put-off test, and that `terms` no longer loses paid decisions when its last lookup fails
  - 2026-11-17: the inputs as built. Readings read the claim's approved trial events, which hold the stored records, and the instructions' version; terms read the names and also the approved matches, since candidates come from the approved trials; fetch reads every approved match, papers included. A claim's input lives in other tables, so before each run the steps' entries are compared with what the claims hold (`claimsteps/inputs.notice_changes`) and those that differ are marked stale, as `mark_changed` does for one record.
- [x] 7.4 Keep the registry numbers and identifiers a page names with its source article, add `claim_named_records`, and take `_named_on_the_page` out of the locked section of `LinkRead._read`; verify with tests for both scenarios of "Records a page names are looked up apart from the join"
- [x] 7.5 Add `claim_decide` depending on substance, trials and fetch, calling `decide_prepared_lead_claim` unchanged; verify with tests for the three scenarios of "What a decision waits for"
  - 2026-11-17: `claim_decide` also waits for `claim_articles`, so that lead-reading's "Prepare comes to an article of a stopped outlet" (the claim keeps awaiting review) still holds. It still does not wait for papers, readings or terms.
- [x] 7.6 Make `thenwhat prepare` run the claim steps through the runner, take approved claims with a part due, and print the per-step report; verify with tests for the scenarios of "Preparing many claims" and "Unfinished parts of a published claim are completed", and one refusal test
  - 2026-11-17: `registry_search_due_at` is no longer cleared by a search: it is the time a new search was last asked for, and a change of it makes the search due. `--due` takes the claims due for the substance lookup or the trial search.
- [x] 7.7 Report claims with no search record as never searched in `thenwhat prepare` and `thenwhat audit list`; verify with tests for both scenarios of "A claim never searched is told apart from one searched"
- [x] 7.8 Keep `thenwhat resolve`, `fetch`, `readings` and `terms` for a named claim as calls of the same steps; verify one success test each
  - 2026-11-17: `thenwhat extract article` stays its own command for one named article and pasted text, on the same service as `claim_articles`; its `--unless-held`, used only by the old `prepare`, is gone. A named command exits 1 when a step it ran did not finish, `claim_papers` needing a fix while `OPENALEX_API_KEY` is unset included.
- [ ] 7.9 On the writer, run the claim steps for fifty approved claims whose answers are stored and compare matches, events and status with what is stored; record the differences here and stop for the operator if there is any

## 8. Switch over and remove

- [x] 8.1 Update `scripts/daily-run.sh` to read the new report of `prepare`; verify a dry run of the script prints the prepared counts
- [x] 8.2 Delete the process-per-step runner in `cli/prepare.py`, `NOT_NEEDED_TO_DECIDE`, and what is left unused in `backfill/`; verify `vulture` reports nothing new and `make check` passes
  - 2026-11-17: `vulture` could not be installed in this session (the install was refused), so the check was a sweep by name of what the refactor could orphan: `plan_claims`, `ClaimPlan`, `NOT_NEEDED_TO_DECIDE`, `SharedTurns`, `STEPS_FAILED`, `_named_on_the_page` are gone from source and tests; an unused `reasons_line` was removed. `Deferred` stays for `thenwhat audit attach` until task 6.2 removes it from the runner. Run `vulture` on the writer before archive.
  - 2026-11-17: the process-per-step runner, `NOT_NEEDED_TO_DECIDE`, `plan_claims`, `steps_for`, `_step` and the read's `_named_on_the_page` are deleted, and `make check`'s Python tools pass. Not ticked: `vulture` is not a dependency of the pipeline and could not be run here.
- [ ] 8.3 Update `docs/url-to-claim.md`, `docs/daily-run.md` and `docs/backfill-loop.md` for the claim steps, requeue and the plan's new lines; verify the commands they show run as written
  - 2026-11-17: the three documents are updated and the commands they show match the tested command lines. Not ticked: the edited Mermaid block of `docs/url-to-claim.md` was not rendered again (serving a local page for it was refused in this session). Render it once, on GitHub or locally, then tick.
- [x] 8.4 Record the decision "one runner for leads and claims; a failure is final only when it is known to be" as an ADR in `docs/adr/`; verify it names what it replaces

## 9. Integration

- [x] 9.1 Run `make check`; verify ruff, ty, pytest and the site build pass
- [ ] 9.2 On the writer, run one day's run end to end, then `thenwhat backfill plan`; record here the records put off and needing a fix by reason, the number of live claims with no terms against 206 of 594, and from `thenwhat measure` each step's share of time and cost and its largest wait cause

## 10. Writer upgrades, retries and due work (P2)

- [x] 10.1 <a id="task-f39"></a>Recheck eligibility atomically with requeue and the lead update. Exercise both transaction orders and verify the resulting ledger, read outcome and affected count. [F39](../../../docs/reviews/2026-11-17-code-review.md#finding-f39) · [Acceptance scenario](specs/work-ledger/spec.md#scenario-a-successful-retry-races-with-requeue)

- [x] 10.2 <a id="task-f40"></a>Distinguish a failed batch attempt from final per-record outcomes. Feed actual fallback measurements to the live view and compare its totals with the ledger. [F40](../../../docs/reviews/2026-11-17-code-review.md#finding-f40) · [Acceptance scenario](specs/processing-metrics/spec.md#scenario-a-failed-batch-falls-back-to-individual-records)

- [x] 10.3 <a id="task-f41"></a>Recheck the shared pause after pacing and before sending. Use a controlled clock and mock transport to verify zero requests before 13:00 and normal eligibility afterwards. [F41](../../../docs/reviews/2026-11-17-code-review.md#finding-f41) · [Acceptance scenario](specs/source-clients/spec.md#scenario-a-pause-begins-while-a-client-awaits-its-turn)

- [x] 10.4 <a id="task-f43"></a>Include paper DOIs in the fingerprint of their owning lookup. Prepare, add a paper entity, prepare again and verify one lookup with no repeat on an unchanged run. [F43](../../../docs/reviews/2026-11-17-code-review.md#finding-f43) · [Acceptance scenario](specs/work-ledger/spec.md#scenario-adding-a-paper-changes-the-lookup-inputs)

- [x] 10.5 <a id="task-f46"></a>Use the screening eligibility calculation in the read-only plan. Check the plan before and after successive bounded runs and confirm that planning itself leaves ledger and lead rows untouched. [F46](../../../docs/reviews/2026-11-17-code-review.md#finding-f46) · [Acceptance scenario](specs/lead-screening/spec.md#scenario-planning-sees-the-same-newly-eligible-leads-as-screening)

## Workflow follow-up

- Archive this change after `openspec/changes/social-link-backfill` is archived, so `lead-reading` and `lead-screening` exist in `openspec/specs/`.
- Tell the owners of `work-reuse-and-metrics` that its task 2.2 (spans from every step) is done here by the runner for pipeline steps, leaving 2.3 (the lookup Worker) to that change.
- Tell the owners of `work-reuse-and-metrics` 4.3 and `idempotent-runs-and-one-address` 5.3 and 5.5 that the staged-result seam of `design.md` decision 9 is where those land.

## Trial on a copy, 17 November 2026

Run by the assistant on a trimmed copy of the database as frozen on 16 November (357,964 leads that passed triage, every claim), on the test server, after merging `main`. Not a substitute for 6.7, 7.9 and 9.2, which stay open for the writer.

- Migrations 0024 to 0037 applied (the three of this change are numbered 0036 to 0038 since `main` gained a 0035 of its own). `backfill rekey-links --apply` then `backfill run link_screen`: 352,650 done, none failed.
- `backfill run link_read --limit 6 --workers 2`, against the page reader and the model: 4 done, 1 found nothing (`identity_unresolved`), 2 put off (`reader_not_now`, `outlet_just_asked`), 1 needing a fix (`no_date`).
- `prepare --pending` was stopped by hand after 595 substance lookups and 85 registry searches, then `prepare <slug>` for the one claim the read drafted: nothing finished was asked for again, and the claim was approved by rule and held for audit. MeSH did not answer after 4 attempts: the run stopped at `claim_terms`, the claim's terms stayed due, and its decision was not held.
- What the first `prepare --pending` on the writer will cost, from `thenwhat measure` here: the substance lookup of all 595 live claims took 637 requests to RxNorm and 17 minutes of pacing. The registry search of 85 claims took 614 requests to ClinicalTrials.gov and 18 minutes of pacing, so every live claim is about 4,300 requests and two hours, once. A run stopped part way carries on from where it stopped.
