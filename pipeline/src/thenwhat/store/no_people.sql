-- People in the registry records Postgres holds. Every count must be 0 once
-- `thenwhat backfill strip-event-people --apply` has run (pipeline/src/thenwhat/sources/people.py).
-- Read-only: psql "$DATABASE_URL" -f pipeline/src/thenwhat/store/no_people.sql

SELECT 'evidence_event' AS "table", 'centralContacts' AS field, count(*) AS rows FROM evidence_event
  WHERE raw_payload ? 'protocolSection' AND (raw_payload #> '{protocolSection,contactsLocationsModule,centralContacts}' IS NOT NULL)
UNION ALL
SELECT 'evidence_event' AS "table", 'overallOfficials' AS field, count(*) AS rows FROM evidence_event
  WHERE raw_payload ? 'protocolSection' AND (raw_payload #> '{protocolSection,contactsLocationsModule,overallOfficials}' IS NOT NULL)
UNION ALL
SELECT 'evidence_event' AS "table", 'location contacts' AS field, count(*) AS rows FROM evidence_event
  WHERE raw_payload ? 'protocolSection' AND (jsonb_path_exists(raw_payload, '$.protocolSection.contactsLocationsModule.locations[*].contacts'))
UNION ALL
SELECT 'evidence_event' AS "table", 'investigator name, title or affiliation' AS field, count(*) AS rows FROM evidence_event
  WHERE raw_payload ? 'protocolSection' AND (jsonb_path_exists(raw_payload, '$.protocolSection.sponsorCollaboratorsModule.responsibleParty ? (exists(@.investigatorFullName) || exists(@.investigatorTitle) || exists(@.investigatorAffiliation) || exists(@.oldNameTitle))'))
UNION ALL
SELECT 'evidence_event' AS "table", 'person lead sponsor''s name' AS field, count(*) AS rows FROM evidence_event
  WHERE raw_payload ? 'protocolSection' AND ((jsonb_path_exists(raw_payload, '$.protocolSection.sponsorCollaboratorsModule.leadSponsor ? ((@.class == "INDIV" || @.class == "INDIVIDUAL") && exists(@.name))') OR (raw_payload #>> '{protocolSection,sponsorCollaboratorsModule,responsibleParty,type}' = 'SPONSOR_INVESTIGATOR' AND raw_payload #> '{protocolSection,sponsorCollaboratorsModule,leadSponsor,name}' IS NOT NULL)))
UNION ALL
SELECT 'evidence_event' AS "table", 'person collaborator''s name' AS field, count(*) AS rows FROM evidence_event
  WHERE raw_payload ? 'protocolSection' AND (jsonb_path_exists(raw_payload, '$.protocolSection.sponsorCollaboratorsModule.collaborators[*] ? ((@.class == "INDIV" || @.class == "INDIVIDUAL") && exists(@.name))'))
UNION ALL
SELECT 'evidence_event' AS "table", 'results point of contact' AS field, count(*) AS rows FROM evidence_event
  WHERE raw_payload ? 'protocolSection' AND (raw_payload #> '{resultsSection,moreInfoModule,pointOfContact}' IS NOT NULL)
UNION ALL
SELECT 'evidence_event' AS "table", 'email' AS field, count(*) AS rows FROM evidence_event
  WHERE raw_payload ? 'protocolSection' AND (jsonb_path_exists(raw_payload, 'strict $.**.email'))
UNION ALL
SELECT 'evidence_event' AS "table", 'phone' AS field, count(*) AS rows FROM evidence_event
  WHERE raw_payload ? 'protocolSection' AND (jsonb_path_exists(raw_payload, 'strict $.**.phone') OR jsonb_path_exists(raw_payload, 'strict $.**.phoneExt'))
UNION ALL
SELECT 'registry_trial' AS "table", 'centralContacts' AS field, count(*) AS rows FROM registry_trial
  WHERE raw_payload ? 'protocolSection' AND (raw_payload #> '{protocolSection,contactsLocationsModule,centralContacts}' IS NOT NULL)
UNION ALL
SELECT 'registry_trial' AS "table", 'overallOfficials' AS field, count(*) AS rows FROM registry_trial
  WHERE raw_payload ? 'protocolSection' AND (raw_payload #> '{protocolSection,contactsLocationsModule,overallOfficials}' IS NOT NULL)
UNION ALL
SELECT 'registry_trial' AS "table", 'location contacts' AS field, count(*) AS rows FROM registry_trial
  WHERE raw_payload ? 'protocolSection' AND (jsonb_path_exists(raw_payload, '$.protocolSection.contactsLocationsModule.locations[*].contacts'))
UNION ALL
SELECT 'registry_trial' AS "table", 'investigator name, title or affiliation' AS field, count(*) AS rows FROM registry_trial
  WHERE raw_payload ? 'protocolSection' AND (jsonb_path_exists(raw_payload, '$.protocolSection.sponsorCollaboratorsModule.responsibleParty ? (exists(@.investigatorFullName) || exists(@.investigatorTitle) || exists(@.investigatorAffiliation) || exists(@.oldNameTitle))'))
UNION ALL
SELECT 'registry_trial' AS "table", 'person lead sponsor''s name' AS field, count(*) AS rows FROM registry_trial
  WHERE raw_payload ? 'protocolSection' AND ((jsonb_path_exists(raw_payload, '$.protocolSection.sponsorCollaboratorsModule.leadSponsor ? ((@.class == "INDIV" || @.class == "INDIVIDUAL") && exists(@.name))') OR (raw_payload #>> '{protocolSection,sponsorCollaboratorsModule,responsibleParty,type}' = 'SPONSOR_INVESTIGATOR' AND raw_payload #> '{protocolSection,sponsorCollaboratorsModule,leadSponsor,name}' IS NOT NULL)))
UNION ALL
SELECT 'registry_trial' AS "table", 'person collaborator''s name' AS field, count(*) AS rows FROM registry_trial
  WHERE raw_payload ? 'protocolSection' AND (jsonb_path_exists(raw_payload, '$.protocolSection.sponsorCollaboratorsModule.collaborators[*] ? ((@.class == "INDIV" || @.class == "INDIVIDUAL") && exists(@.name))'))
UNION ALL
SELECT 'registry_trial' AS "table", 'results point of contact' AS field, count(*) AS rows FROM registry_trial
  WHERE raw_payload ? 'protocolSection' AND (raw_payload #> '{resultsSection,moreInfoModule,pointOfContact}' IS NOT NULL)
UNION ALL
SELECT 'registry_trial' AS "table", 'email' AS field, count(*) AS rows FROM registry_trial
  WHERE raw_payload ? 'protocolSection' AND (jsonb_path_exists(raw_payload, 'strict $.**.email'))
UNION ALL
SELECT 'registry_trial' AS "table", 'phone' AS field, count(*) AS rows FROM registry_trial
  WHERE raw_payload ? 'protocolSection' AND (jsonb_path_exists(raw_payload, 'strict $.**.phone') OR jsonb_path_exists(raw_payload, 'strict $.**.phoneExt'))
UNION ALL
SELECT 'registry_trial', 'lead_sponsor_name of a person', count(*) FROM registry_trial
  WHERE lead_sponsor_name IS NOT NULL AND (sponsor_class IN ('INDIV', 'INDIVIDUAL')
    OR raw_payload #>> '{protocolSection,sponsorCollaboratorsModule,responsibleParty,type}' = 'SPONSOR_INVESTIGATOR');

-- Authors, abstracts and person keys in every other stored payload: a follow-up paper's
-- record, a retraction notice, a paper's or a trial paper's record. Every count must be 0
-- once `thenwhat backfill strip-paper-people --apply` has run.
SELECT 'evidence_event' AS "table", 'abstract' AS field, count(*) AS rows FROM evidence_event
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.abstract')
UNION ALL
SELECT 'evidence_event' AS "table", 'abstractText' AS field, count(*) AS rows FROM evidence_event
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.abstractText')
UNION ALL
SELECT 'evidence_event' AS "table", 'abstract_inverted_index' AS field, count(*) AS rows FROM evidence_event
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.abstract_inverted_index')
UNION ALL
SELECT 'evidence_event' AS "table", 'affiliation' AS field, count(*) AS rows FROM evidence_event
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.affiliation')
UNION ALL
SELECT 'evidence_event' AS "table", 'author' AS field, count(*) AS rows FROM evidence_event
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.author')
UNION ALL
SELECT 'evidence_event' AS "table", 'authorIdList' AS field, count(*) AS rows FROM evidence_event
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.authorIdList')
UNION ALL
SELECT 'evidence_event' AS "table", 'authorList' AS field, count(*) AS rows FROM evidence_event
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.authorList')
UNION ALL
SELECT 'evidence_event' AS "table", 'authorString' AS field, count(*) AS rows FROM evidence_event
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.authorString')
UNION ALL
SELECT 'evidence_event' AS "table", 'authors' AS field, count(*) AS rows FROM evidence_event
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.authors')
UNION ALL
SELECT 'evidence_event' AS "table", 'authorships' AS field, count(*) AS rows FROM evidence_event
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.authorships')
UNION ALL
SELECT 'evidence_event' AS "table", 'centralContacts' AS field, count(*) AS rows FROM evidence_event
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.centralContacts')
UNION ALL
SELECT 'evidence_event' AS "table", 'contacts' AS field, count(*) AS rows FROM evidence_event
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.contacts')
UNION ALL
SELECT 'evidence_event' AS "table", 'corresponding_author_ids' AS field, count(*) AS rows FROM evidence_event
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.corresponding_author_ids')
UNION ALL
SELECT 'evidence_event' AS "table", 'corresponding_institution_ids' AS field, count(*) AS rows FROM evidence_event
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.corresponding_institution_ids')
UNION ALL
SELECT 'evidence_event' AS "table", 'editor' AS field, count(*) AS rows FROM evidence_event
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.editor')
UNION ALL
SELECT 'evidence_event' AS "table", 'email' AS field, count(*) AS rows FROM evidence_event
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.email')
UNION ALL
SELECT 'evidence_event' AS "table", 'fullTextIdList' AS field, count(*) AS rows FROM evidence_event
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.fullTextIdList')
UNION ALL
SELECT 'evidence_event' AS "table", 'fullTextUrlList' AS field, count(*) AS rows FROM evidence_event
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.fullTextUrlList')
UNION ALL
SELECT 'evidence_event' AS "table", 'investigatorAffiliation' AS field, count(*) AS rows FROM evidence_event
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.investigatorAffiliation')
UNION ALL
SELECT 'evidence_event' AS "table", 'investigatorFullName' AS field, count(*) AS rows FROM evidence_event
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.investigatorFullName')
UNION ALL
SELECT 'evidence_event' AS "table", 'investigatorList' AS field, count(*) AS rows FROM evidence_event
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.investigatorList')
UNION ALL
SELECT 'evidence_event' AS "table", 'investigatorTitle' AS field, count(*) AS rows FROM evidence_event
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.investigatorTitle')
UNION ALL
SELECT 'evidence_event' AS "table", 'oldNameTitle' AS field, count(*) AS rows FROM evidence_event
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.oldNameTitle')
UNION ALL
SELECT 'evidence_event' AS "table", 'overallOfficials' AS field, count(*) AS rows FROM evidence_event
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.overallOfficials')
UNION ALL
SELECT 'evidence_event' AS "table", 'phone' AS field, count(*) AS rows FROM evidence_event
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.phone')
UNION ALL
SELECT 'evidence_event' AS "table", 'phoneExt' AS field, count(*) AS rows FROM evidence_event
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.phoneExt')
UNION ALL
SELECT 'evidence_event' AS "table", 'pointOfContact' AS field, count(*) AS rows FROM evidence_event
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.pointOfContact')
UNION ALL
SELECT 'paper_record' AS "table", 'abstract' AS field, count(*) AS rows FROM paper_record
  WHERE payload IS NOT NULL AND NOT payload ? 'protocolSection' AND jsonb_path_exists(payload, 'strict $.**.abstract')
UNION ALL
SELECT 'paper_record' AS "table", 'abstractText' AS field, count(*) AS rows FROM paper_record
  WHERE payload IS NOT NULL AND NOT payload ? 'protocolSection' AND jsonb_path_exists(payload, 'strict $.**.abstractText')
UNION ALL
SELECT 'paper_record' AS "table", 'abstract_inverted_index' AS field, count(*) AS rows FROM paper_record
  WHERE payload IS NOT NULL AND NOT payload ? 'protocolSection' AND jsonb_path_exists(payload, 'strict $.**.abstract_inverted_index')
UNION ALL
SELECT 'paper_record' AS "table", 'affiliation' AS field, count(*) AS rows FROM paper_record
  WHERE payload IS NOT NULL AND NOT payload ? 'protocolSection' AND jsonb_path_exists(payload, 'strict $.**.affiliation')
UNION ALL
SELECT 'paper_record' AS "table", 'author' AS field, count(*) AS rows FROM paper_record
  WHERE payload IS NOT NULL AND NOT payload ? 'protocolSection' AND jsonb_path_exists(payload, 'strict $.**.author')
UNION ALL
SELECT 'paper_record' AS "table", 'authorIdList' AS field, count(*) AS rows FROM paper_record
  WHERE payload IS NOT NULL AND NOT payload ? 'protocolSection' AND jsonb_path_exists(payload, 'strict $.**.authorIdList')
UNION ALL
SELECT 'paper_record' AS "table", 'authorList' AS field, count(*) AS rows FROM paper_record
  WHERE payload IS NOT NULL AND NOT payload ? 'protocolSection' AND jsonb_path_exists(payload, 'strict $.**.authorList')
UNION ALL
SELECT 'paper_record' AS "table", 'authorString' AS field, count(*) AS rows FROM paper_record
  WHERE payload IS NOT NULL AND NOT payload ? 'protocolSection' AND jsonb_path_exists(payload, 'strict $.**.authorString')
UNION ALL
SELECT 'paper_record' AS "table", 'authors' AS field, count(*) AS rows FROM paper_record
  WHERE payload IS NOT NULL AND NOT payload ? 'protocolSection' AND jsonb_path_exists(payload, 'strict $.**.authors')
UNION ALL
SELECT 'paper_record' AS "table", 'authorships' AS field, count(*) AS rows FROM paper_record
  WHERE payload IS NOT NULL AND NOT payload ? 'protocolSection' AND jsonb_path_exists(payload, 'strict $.**.authorships')
UNION ALL
SELECT 'paper_record' AS "table", 'centralContacts' AS field, count(*) AS rows FROM paper_record
  WHERE payload IS NOT NULL AND NOT payload ? 'protocolSection' AND jsonb_path_exists(payload, 'strict $.**.centralContacts')
UNION ALL
SELECT 'paper_record' AS "table", 'contacts' AS field, count(*) AS rows FROM paper_record
  WHERE payload IS NOT NULL AND NOT payload ? 'protocolSection' AND jsonb_path_exists(payload, 'strict $.**.contacts')
UNION ALL
SELECT 'paper_record' AS "table", 'corresponding_author_ids' AS field, count(*) AS rows FROM paper_record
  WHERE payload IS NOT NULL AND NOT payload ? 'protocolSection' AND jsonb_path_exists(payload, 'strict $.**.corresponding_author_ids')
UNION ALL
SELECT 'paper_record' AS "table", 'corresponding_institution_ids' AS field, count(*) AS rows FROM paper_record
  WHERE payload IS NOT NULL AND NOT payload ? 'protocolSection' AND jsonb_path_exists(payload, 'strict $.**.corresponding_institution_ids')
UNION ALL
SELECT 'paper_record' AS "table", 'editor' AS field, count(*) AS rows FROM paper_record
  WHERE payload IS NOT NULL AND NOT payload ? 'protocolSection' AND jsonb_path_exists(payload, 'strict $.**.editor')
UNION ALL
SELECT 'paper_record' AS "table", 'email' AS field, count(*) AS rows FROM paper_record
  WHERE payload IS NOT NULL AND NOT payload ? 'protocolSection' AND jsonb_path_exists(payload, 'strict $.**.email')
UNION ALL
SELECT 'paper_record' AS "table", 'fullTextIdList' AS field, count(*) AS rows FROM paper_record
  WHERE payload IS NOT NULL AND NOT payload ? 'protocolSection' AND jsonb_path_exists(payload, 'strict $.**.fullTextIdList')
UNION ALL
SELECT 'paper_record' AS "table", 'fullTextUrlList' AS field, count(*) AS rows FROM paper_record
  WHERE payload IS NOT NULL AND NOT payload ? 'protocolSection' AND jsonb_path_exists(payload, 'strict $.**.fullTextUrlList')
UNION ALL
SELECT 'paper_record' AS "table", 'investigatorAffiliation' AS field, count(*) AS rows FROM paper_record
  WHERE payload IS NOT NULL AND NOT payload ? 'protocolSection' AND jsonb_path_exists(payload, 'strict $.**.investigatorAffiliation')
UNION ALL
SELECT 'paper_record' AS "table", 'investigatorFullName' AS field, count(*) AS rows FROM paper_record
  WHERE payload IS NOT NULL AND NOT payload ? 'protocolSection' AND jsonb_path_exists(payload, 'strict $.**.investigatorFullName')
UNION ALL
SELECT 'paper_record' AS "table", 'investigatorList' AS field, count(*) AS rows FROM paper_record
  WHERE payload IS NOT NULL AND NOT payload ? 'protocolSection' AND jsonb_path_exists(payload, 'strict $.**.investigatorList')
UNION ALL
SELECT 'paper_record' AS "table", 'investigatorTitle' AS field, count(*) AS rows FROM paper_record
  WHERE payload IS NOT NULL AND NOT payload ? 'protocolSection' AND jsonb_path_exists(payload, 'strict $.**.investigatorTitle')
UNION ALL
SELECT 'paper_record' AS "table", 'oldNameTitle' AS field, count(*) AS rows FROM paper_record
  WHERE payload IS NOT NULL AND NOT payload ? 'protocolSection' AND jsonb_path_exists(payload, 'strict $.**.oldNameTitle')
UNION ALL
SELECT 'paper_record' AS "table", 'overallOfficials' AS field, count(*) AS rows FROM paper_record
  WHERE payload IS NOT NULL AND NOT payload ? 'protocolSection' AND jsonb_path_exists(payload, 'strict $.**.overallOfficials')
UNION ALL
SELECT 'paper_record' AS "table", 'phone' AS field, count(*) AS rows FROM paper_record
  WHERE payload IS NOT NULL AND NOT payload ? 'protocolSection' AND jsonb_path_exists(payload, 'strict $.**.phone')
UNION ALL
SELECT 'paper_record' AS "table", 'phoneExt' AS field, count(*) AS rows FROM paper_record
  WHERE payload IS NOT NULL AND NOT payload ? 'protocolSection' AND jsonb_path_exists(payload, 'strict $.**.phoneExt')
UNION ALL
SELECT 'paper_record' AS "table", 'pointOfContact' AS field, count(*) AS rows FROM paper_record
  WHERE payload IS NOT NULL AND NOT payload ? 'protocolSection' AND jsonb_path_exists(payload, 'strict $.**.pointOfContact')
UNION ALL
SELECT 'trial_paper' AS "table", 'abstract' AS field, count(*) AS rows FROM trial_paper
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.abstract')
UNION ALL
SELECT 'trial_paper' AS "table", 'abstractText' AS field, count(*) AS rows FROM trial_paper
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.abstractText')
UNION ALL
SELECT 'trial_paper' AS "table", 'abstract_inverted_index' AS field, count(*) AS rows FROM trial_paper
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.abstract_inverted_index')
UNION ALL
SELECT 'trial_paper' AS "table", 'affiliation' AS field, count(*) AS rows FROM trial_paper
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.affiliation')
UNION ALL
SELECT 'trial_paper' AS "table", 'author' AS field, count(*) AS rows FROM trial_paper
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.author')
UNION ALL
SELECT 'trial_paper' AS "table", 'authorIdList' AS field, count(*) AS rows FROM trial_paper
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.authorIdList')
UNION ALL
SELECT 'trial_paper' AS "table", 'authorList' AS field, count(*) AS rows FROM trial_paper
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.authorList')
UNION ALL
SELECT 'trial_paper' AS "table", 'authorString' AS field, count(*) AS rows FROM trial_paper
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.authorString')
UNION ALL
SELECT 'trial_paper' AS "table", 'authors' AS field, count(*) AS rows FROM trial_paper
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.authors')
UNION ALL
SELECT 'trial_paper' AS "table", 'authorships' AS field, count(*) AS rows FROM trial_paper
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.authorships')
UNION ALL
SELECT 'trial_paper' AS "table", 'centralContacts' AS field, count(*) AS rows FROM trial_paper
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.centralContacts')
UNION ALL
SELECT 'trial_paper' AS "table", 'contacts' AS field, count(*) AS rows FROM trial_paper
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.contacts')
UNION ALL
SELECT 'trial_paper' AS "table", 'corresponding_author_ids' AS field, count(*) AS rows FROM trial_paper
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.corresponding_author_ids')
UNION ALL
SELECT 'trial_paper' AS "table", 'corresponding_institution_ids' AS field, count(*) AS rows FROM trial_paper
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.corresponding_institution_ids')
UNION ALL
SELECT 'trial_paper' AS "table", 'editor' AS field, count(*) AS rows FROM trial_paper
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.editor')
UNION ALL
SELECT 'trial_paper' AS "table", 'email' AS field, count(*) AS rows FROM trial_paper
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.email')
UNION ALL
SELECT 'trial_paper' AS "table", 'fullTextIdList' AS field, count(*) AS rows FROM trial_paper
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.fullTextIdList')
UNION ALL
SELECT 'trial_paper' AS "table", 'fullTextUrlList' AS field, count(*) AS rows FROM trial_paper
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.fullTextUrlList')
UNION ALL
SELECT 'trial_paper' AS "table", 'investigatorAffiliation' AS field, count(*) AS rows FROM trial_paper
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.investigatorAffiliation')
UNION ALL
SELECT 'trial_paper' AS "table", 'investigatorFullName' AS field, count(*) AS rows FROM trial_paper
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.investigatorFullName')
UNION ALL
SELECT 'trial_paper' AS "table", 'investigatorList' AS field, count(*) AS rows FROM trial_paper
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.investigatorList')
UNION ALL
SELECT 'trial_paper' AS "table", 'investigatorTitle' AS field, count(*) AS rows FROM trial_paper
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.investigatorTitle')
UNION ALL
SELECT 'trial_paper' AS "table", 'oldNameTitle' AS field, count(*) AS rows FROM trial_paper
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.oldNameTitle')
UNION ALL
SELECT 'trial_paper' AS "table", 'overallOfficials' AS field, count(*) AS rows FROM trial_paper
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.overallOfficials')
UNION ALL
SELECT 'trial_paper' AS "table", 'phone' AS field, count(*) AS rows FROM trial_paper
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.phone')
UNION ALL
SELECT 'trial_paper' AS "table", 'phoneExt' AS field, count(*) AS rows FROM trial_paper
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.phoneExt')
UNION ALL
SELECT 'trial_paper' AS "table", 'pointOfContact' AS field, count(*) AS rows FROM trial_paper
  WHERE raw_payload IS NOT NULL AND NOT raw_payload ? 'protocolSection' AND jsonb_path_exists(raw_payload, 'strict $.**.pointOfContact');
