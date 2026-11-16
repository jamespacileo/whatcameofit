# address-identity

## Purpose

Says which addresses are one article, for the pipeline, the site and the extension alike, and how what is stored follows that rule when it changes.

## ADDED Requirements

### Requirement: One comparison for the pipeline, the site and the extension
The pipeline's address key and the article key of the site and the extension SHALL give the same key for the same address. One cases file SHALL be read by the tests of both, listing addresses that are one article with their key, pairs of addresses that are not one article, and addresses that have no key.

#### Scenario: A rule added on one side only
- **WHEN** a rule is added to the pipeline's key and not to the site's
- **THEN** a case for it in the shared file fails the site's test

#### Scenario: A difference only one side would see
- **WHEN** an address has parameters whose order depends on a locale, or a path with characters a browser and the pipeline escape differently
- **THEN** the shared file holds a case for it and both give its key

#### Scenario: An address that only looks like another
- **WHEN** two addresses differ in the letter case of the path, in a page suffix, or in a parameter that names the article
- **THEN** they have different keys

### Requirement: What does not make a second article
Two addresses SHALL have one key when they differ only in how the address is written (scheme, host case, a same-site host label, stray dots, slashes, escape case, a fragment, an AMP form), in a parameter that says how a reader arrived, or in a host on the list of hosts that serve one site under two names. A parameter that one outlet uses that way SHALL be ignored on that outlet only.

#### Scenario: A tracking parameter added after a run
- **WHEN** one share gives an article's address and another gives it with `?mbid=synd_feed`
- **THEN** both have one key

#### Scenario: An outlet's own parameter
- **WHEN** an address on wsj.com is shared with `?mod=hp_lead_pos5`
- **THEN** it has the key of the address without it

#### Scenario: The same parameter name elsewhere
- **WHEN** an address on another site has `?mod=news`
- **THEN** the parameter stays in its key

#### Scenario: An edition's host
- **WHEN** an article is shared from `uk.businessinsider.com` and from `www.businessinsider.com` at one path
- **THEN** both have one key

#### Scenario: A host label that is not listed
- **WHEN** an address is on `lite.` or `uk.` of a site that is not on the list
- **THEN** it keeps its host in its key

### Requirement: The key has a version
The address key SHALL carry a version that is raised with every change that gives a stored address another key. A link lead SHALL record the version its key was made under.

#### Scenario: A lead loaded today
- **WHEN** a link lead is stored
- **THEN** it records the current version of the key

### Requirement: Stored leads follow the address key
`thenwhat backfill rekey-links` SHALL bring every link lead keyed under an earlier version to the current one. Without `--apply` it SHALL only report how many leads keep their key, get a new one, or would be merged. It SHALL send no request and call no model. It SHALL be safe to stop and run again.

#### Scenario: Looking before bringing the leads up to date
- **WHEN** the operator runs it without `--apply`
- **THEN** the counts are reported and nothing is changed

#### Scenario: A stored lead's key changes
- **WHEN** a lead's address has another key under the current version and no other lead has that key
- **THEN** the lead takes the key, with the outlet the key names

#### Scenario: Two stored leads are one article under the current form
- **WHEN** a lead's new key is the key of another lead
- **THEN** one lead remains, with the shares of both and the earlier first share, and a share both held is kept once

#### Scenario: What screening found for either lead is kept
- **WHEN** two leads are merged and screening had found stored records for the one removed
- **THEN** the lead that remains holds them, each once

#### Scenario: A run is under way
- **WHEN** `--apply` is given while a step worked on a link lead in the last ten minutes
- **THEN** it is refused and nothing is changed

#### Scenario: Bringing the leads up to date twice
- **WHEN** it is run again after it finished
- **THEN** no lead is looked at

### Requirement: Rekeying pays for nothing
Of two leads that are one article, the lead kept SHALL be the one that has come furthest: one that drafted a claim, else one that joined a claim, else read, scored, screened, else the older. The lead that remains SHALL point at the claim and source article that either lead pointed at. Bringing a lead to the current key SHALL NOT make it due again for a step that asks a source or a model. A step that asks nothing SHALL be due again when what it reads changed.

#### Scenario: A lead that was scored is not scored again
- **WHEN** a scored lead is merged with an unscored one, or takes a new key, and triage is run again
- **THEN** no model call is made for it and it keeps its score

#### Scenario: One of the two leads drafted a claim
- **WHEN** an older lead was read and made nothing, and a newer lead of the same article drafted a claim
- **THEN** the newer lead is the one kept, with its claim and source article

#### Scenario: Screening looks again
- **WHEN** a screened lead takes a new key
- **THEN** it is due for screening again

#### Scenario: Two leads that made two claims
- **WHEN** two merged leads had each made or joined a different claim
- **THEN** the pair of claims is reported to the operator and no claim is changed

### Requirement: No load while stored keys are behind
`thenwhat backfill load-links` and any step over link leads SHALL be refused while a stored lead is keyed under an earlier version, and SHALL name the command that brings the leads up to date.

#### Scenario: Loading before the stored leads are up to date
- **WHEN** the operator loads a file while a lead is behind
- **THEN** the load is refused, nothing is stored, and the message names `thenwhat backfill rekey-links --apply`

### Requirement: An address that names where it leads
An archive copy or a redirect whose address contains the address it leads to SHALL have the key of that address. No request SHALL be sent to find it. The lead SHALL keep the address as it was shared.

#### Scenario: An archive copy
- **WHEN** `web.archive.org/web/20170110111518/https://example.org/story` is shared
- **THEN** it belongs to the lead of `example.org/story`

### Requirement: A shortened link is stored as where it leads
A link lead on a host from a fixed list of shorteners SHALL be unfurled by asking that host for its redirect only, and SHALL then have the key of the address it leads to. The request SHALL stop at the first address whose host is not on the list, and that address SHALL NOT be fetched. Each host's robots.txt SHALL be obeyed. A host that is not on the list SHALL NOT be asked. `t.co` SHALL NOT be on the list.

#### Scenario: A shortener on the list
- **WHEN** a lead's address is on `bit.ly` and its redirect names a news article
- **THEN** the lead takes the key of the article's address, and the article's page is not requested

#### Scenario: A shortener that refuses
- **WHEN** a host's robots.txt disallows the link's path
- **THEN** the lead is left as it is and no request is sent to the link

#### Scenario: Asked once
- **WHEN** the step is run again
- **THEN** a lead already unfurled is not asked for again

### Requirement: One article once per claim
A claim SHALL NOT hold two source articles with one key, and a registry trial SHALL NOT hold two article leads with one key.

#### Scenario: The same article under another form
- **WHEN** an article is added to a claim that holds it under another form of its address
- **THEN** it is found as the article already there
