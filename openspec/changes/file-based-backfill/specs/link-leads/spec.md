# Spec Delta

## MODIFIED Requirements

### Requirement: Loading from a file
The load stage of a run SHALL read one or more bulk files of one platform from the operator's disk and write, to the run's files, a share for each post that links to an address on a listed outlet. It SHALL send no request to any platform or outlet and SHALL write to no database. It SHALL finish by reporting how many posts were read, how many shares were written, how many distinct addresses those are, and how many posts were skipped for each reason, the reason "outlet not listed" among them.

#### Scenario: A file of stories
- **WHEN** the operator loads a file of 10,000 Hacker News stories of which 7,000 link to an address and 800 of those are on listed outlets
- **THEN** 800 shares are written to the run, 6,200 are counted as outlet not listed, the report gives the counts, and no request is sent

#### Scenario: Stopped part way
- **WHEN** a load is stopped and started again on the same files
- **THEN** the run holds every post that links to a listed outlet once

#### Scenario: A platform with no reader
- **WHEN** the operator names a platform the pipeline has no reader for
- **THEN** the command fails, lists the platforms it can read, and writes nothing

#### Scenario: A domain is added to the list
- **WHEN** a domain is added to the outlet list and a new run is started over the same files
- **THEN** the run holds the posts on that domain, and its later stages pay for none of the leads an earlier run pushed

### Requirement: Link lead record
A link lead SHALL be kept once per article address, in a run's files and in the truth store alike. It SHALL carry the address, the outlet's domain, the outlet kind, the title the article was first shared under, and each share of it: the platform, the community, the time shared and the score. A share SHALL be kept once.

#### Scenario: One article shared in two places
- **WHEN** the same article address is shared on Hacker News and in a Reddit community, in two runs that are both pushed
- **THEN** the truth store holds one link lead with two shares

#### Scenario: The same file in two runs
- **WHEN** two runs over the same file are both pushed
- **THEN** the truth store holds no lead and no share twice

## ADDED Requirements

### Requirement: Unlisted domains are tallied, not kept
A load SHALL write a tally in the run giving, for each unlisted domain, the platform, the number of link posts and the number whose title names a topic word. The tally SHALL hold no title, no address beyond the domain, and nothing about who shared. No link on an unlisted outlet SHALL appear in any other file of the run or be pushed.

#### Scenario: A code repository's domain
- **WHEN** a file holds 5,000 posts that link to one unlisted domain
- **THEN** the tally gives that domain 5,000 for the platform, and the run's other files hold none of them

### Requirement: A row that fails is set aside, within a budget
A row that cannot be read into a post SHALL be recorded in the run's quarantine with the bulk file's name, the row's position and the kind of error, and nothing of the row's content. The load SHALL go on. It SHALL stop with an error when such rows exceed `LOAD_ERROR_BUDGET` as a share of the rows read, and SHALL refuse to start while that setting is empty.

#### Scenario: One malformed line
- **WHEN** one line in a file of 10,000 is not valid JSON
- **THEN** the load writes the rest, and the quarantine has one entry with the file name, the line number and the error's kind

#### Scenario: A file in an unexpected shape
- **WHEN** more rows fail than the budget allows
- **THEN** the load stops and says how many failed of how many read

### Requirement: A file is checked before it is loaded
Before writing anything, a load SHALL check that each file has the fields its reader takes. A file without them SHALL be refused with the missing fields named.

#### Scenario: A column is missing
- **WHEN** a Hacker News file has no `url` column
- **THEN** the load writes nothing and names the column

### Requirement: Dry run
A load run with `--dry-run` SHALL read the files and print the report a load would give, and SHALL write nothing but the tally.

#### Scenario: A dry run before a load
- **WHEN** the operator dry-runs a load and then runs it
- **THEN** the dry run's count of shares on listed outlets equals the load's
