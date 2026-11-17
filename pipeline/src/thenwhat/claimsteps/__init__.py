"""A claim's preparation as steps of the work ledger, each over claims: reading its
unread articles, looking up its substance, searching the trial registry, searching for
papers, looking up the records its articles' pages name, fetching its approved records,
reading its trial records, proposing its terms, and deciding a read's draft.
Behavior: openspec claim-extraction, entity-resolution and work-ledger (change
one-work-runner).

Each step is all or nothing for a claim in its own transaction, and says why when it
did not finish: a source that failed puts the claim off, a source that cannot be asked
at all stops the run, and nothing is recorded as a finished search that did not run.
"""
