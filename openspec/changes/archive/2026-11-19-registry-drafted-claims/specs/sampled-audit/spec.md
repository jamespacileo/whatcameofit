# Spec Delta

## Purpose

Says how a batch of claims held awaiting audit may be released on a sample the pipeline draws, so that release keeps pace with batches of thousands without ending the hold.

## ADDED Requirements

### Requirement: The pipeline draws the sample
`thenwhat audit sample` SHALL draw, for a held batch, a sample of the configured size at random from the batch's held claims, and SHALL record which claims were drawn and the seed that drew them. The person or assistant who judges SHALL NOT choose which claims are in the sample. A batch smaller than the sample size SHALL be judged whole.

#### Scenario: A batch of 2,000
- **WHEN** the sample size is 100 and a batch holds 2,000 claims
- **THEN** 100 claims are drawn and recorded with the seed

#### Scenario: A batch of 60
- **WHEN** the sample size is 100 and a batch holds 60 claims
- **THEN** all 60 are to be judged

### Requirement: Every sampled claim is judged right or wrong, with who judged
Each sampled claim SHALL be judged right or wrong against what its records show: that its approved trials test its intervention for its indication, that it duplicates no other claim, and that its vertical fits. A judgement SHALL record who made it, and one made by an assistant SHALL be recorded as an assistant's and never as a person's. A wrong claim SHALL be archived or corrected by the commands that exist, and its defect recorded on the fault sheet.

#### Scenario: An assistant judges
- **WHEN** an assistant judges a sampled claim wrong for citing a trial of another condition
- **THEN** the judgement is recorded as an assistant's, the claim is archived or corrected, and the defect is recorded

### Requirement: A batch is released only at or below the operator's figure
The share of wrong claims a sample may hold SHALL be a setting with no default. `thenwhat audit clear --batch` SHALL release every held claim of a batch that was not judged wrong only when every sampled claim has been judged and the share judged wrong is at or below the figure. While the figure is empty, a batch SHALL be released only by judging every claim, as before.

#### Scenario: Two wrong in a hundred, figure of three
- **WHEN** a sample of 100 has 2 judged wrong and the figure is 3 in 100
- **THEN** the 2 are not released and the rest of the batch is

#### Scenario: A sample not yet finished
- **WHEN** 80 of 100 sampled claims have been judged
- **THEN** the batch is not released and the command says 20 remain

#### Scenario: No figure set
- **WHEN** the figure is not configured
- **THEN** the batch is not released on a sample, and the command says so

### Requirement: A sample over the figure holds the whole batch
When the share judged wrong is above the figure, no claim of the batch SHALL be released on that sample. The batch SHALL stay held until its defects are fixed and a new sample, drawn afresh, is at or below the figure, or until every claim has been judged.

#### Scenario: Six wrong in a hundred, figure of three
- **WHEN** a sample of 100 has 6 judged wrong and the figure is 3 in 100
- **THEN** nothing is released, and the command lists the defects by category

### Requirement: A release on a sample is recorded and changes no review decision
A release SHALL record the batch, the sample's size, the count judged wrong, the figure, and who judged. It SHALL change no claim's, match's or event's review state, and a claim released on a sample SHALL state that no person checked it unless a person approved it.

#### Scenario: Export after a release on a sample
- **WHEN** a batch is released on a sample an assistant judged
- **THEN** its claims are published and each says no person checked it

### Requirement: The operator spot-checks an assistant's sample
When an assistant judged a sample, a share of its judgements, drawn by the pipeline, SHALL be offered to the operator to judge again, and the count on which they differ SHALL be recorded with the batch.

#### Scenario: A spot-check differs
- **WHEN** the operator judges ten of an assistant's judgements and differs on two
- **THEN** the batch records 2 of 10, and the two claims are judged as the operator said
