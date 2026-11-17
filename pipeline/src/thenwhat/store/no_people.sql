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
