# 12. One runner for leads and claims, and a failure is final only when it is known to be

**Superseded on 2026-11-20.** The operator removed claims and the claims pipeline that day. Nothing in this repository acts on this decision any more; it is kept as the record of why the removed code worked as it did.

Date: 2026-11-17. Status: accepted with `openspec/changes/archive/2026-11-18-one-work-runner`, which the operator asked to be written on 17 November 2026 and then to be applied. Proposed by the assistant; the choices marked below as the assistant's were put to the operator in the proposal's summary and not overruled. Touches 0006 and 0007.

## Context

Work ran in two ways. Link leads went through the work ledger: one record a transaction, safe to stop and start again. A claim's preparation ran as one process per step outside it, with "finished" read off whatever happened to be stored.

A review of the database as it stood on 16 November 2026 found the same fault in both: a failure that passes was written down as an answer. A site answering 503 made a lead unreadable for good. A lead refused for a page with no date was never read again once the reader learned to find the date. Three failures skipped a lead for ever, and a model outage counted as a failure of every lead it met. A registry lookup that failed still let its claim be decided, so 52 claims were archived at audit for standing at "no trial record found" while trials exist, and 206 of 594 live claims had no terms because nothing proposed them again.

The operator asked whether to rebuild the pipeline from the ground up. The assistant advised against rebuilding the rules, which are measured fixes, and for rebuilding once the layer that runs them.

## Decision

- One module, `thenwhat.work`, owns how work runs for every kind of record: what a step answers, when a record is due, how a source or a model is asked, and what is done when it cannot be.
- A step's answer says whether the record comes back. Final: done, or nothing found. Put off: the cause is expected to pass, and the record is due by itself after a stated time. Needs a fix: the cause will not pass until something outside the record changes, and the record waits to be made due. A step never records as final a cause it cannot tell from one that passes.
- Every answer but done and a failure carries a reason as a code the step declares, with its values. Words are made from the code.
- `thenwhat work requeue <step> --reason <code>` is the one way to bring records back for a cause that was put right. Raising a step's version stays for a change to the step itself.
- A source, the page reader or a model that cannot be asked stops the run, in every step, with nothing counted against any record.
- A claim's preparation is steps of the same ledger. A claim a read drafted is decided when its substance lookup, its registry search and its fetch have finished. Its papers, readings and terms do not hold the decision and stay due until done.

## The assistant's choices within it

- A lookup of a claim's substance that fails now holds the claim's decision, where it used to pass silently. More claims wait while that registry is down; fewer duplicates are approved because the rule that finds a twin by substance had nothing to read.
- A site's refusal (401, 403) needs a fix and can be made due by outlet; it used to be final except through `retry-outlet`.
- A record put off for one reason for thirty days is said to need a fix, so nothing is asked for without end.

## What does not change

- Every rule about names, classes, conditions and duplicates, every prompt and every threshold.
- Which claims are approved, rejected or held for audit (0001, 0007), and that no model decides a status.
- Whether and how a site is asked is the page reader's decision (0006): the pipeline acts on its answers and does not retry around it.
- No article text is stored. A reason carries a status, an outlet, a count: never words from a page.

## Consequences

- A lead once counted as unreadable can come back and cost a page request and a read. Only reasons declared as put off or needing a fix can, a requeue counts them first with `--dry-run`, and the allowances and the spend ceiling apply as to any run.
- "No trial record found" still cannot be told from "never searched" by the status alone. The record each search leaves is what tells them apart, and `thenwhat prepare` and the audit list say which claims were never searched.
- The plan and the funnel report gain lines for records put off and needing a fix, by reason. A number that used to read as finished work may now read as waiting.
- Steps written later get resumption, reasons and measurement from the runner and write none of it themselves.
