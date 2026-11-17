// People in a ClinicalTrials.gov record, and the record without them. Pure.
//
// The project keeps no personal data beyond subscriber emails (CLAUDE.md). A registry
// record names people: its officials and contacts, each site's contacts, the investigator
// a responsible party is, a sponsor or collaborator who is a person, and the results'
// point of contact. `withoutPeople` removes each of them and nothing else, before a
// record is saved, shown, compared or sent to a model. The same rule as the pipeline's
// (`without_people`, `people_in`); keep them in step.
//
// A site's facility, city and country are kept: they are places, not people. Free text
// the registry holds (a summary, a description) is not searched for names.
const PERSON_CLASSES = ["INDIV", "INDIVIDUAL"];
const SPONSOR_INVESTIGATOR = "SPONSOR_INVESTIGATOR";
// What a responsible party says of the person it is.
const INVESTIGATOR_FIELDS = ["investigatorFullName", "investigatorTitle", "investigatorAffiliation", "oldNameTitle"];
// Keys that hold a person's means of contact, wherever they appear.
const CONTACT_KEYS = ["email", "phone", "phoneExt"];

const isObject = (value) => Boolean(value) && typeof value === "object" && !Array.isArray(value);
const object = (value) => (isObject(value) ? value : {});
const list = (value) => (Array.isArray(value) ? value : []);
const filled = (value) => (Array.isArray(value) ? value.length > 0 : isObject(value) ? Object.keys(value).length > 0 : Boolean(value));
const without = (value, keys) => Object.fromEntries(Object.entries(value).filter(([key]) => !keys.includes(key)));

const isStudy = (value) => isObject(value) && isObject(value.protocolSection);

/** Whether a record's lead sponsor is a person: classed as an individual by the registry,
 * or a sponsor-investigator, whom the registry often classes as "other". */
export function sponsoredByAPerson(sponsors) {
  return PERSON_CLASSES.includes(object(sponsors?.leadSponsor).class) ||
    object(sponsors?.responsibleParty).type === SPONSOR_INVESTIGATOR;
}

function withoutContactKeys(value) {
  if (Array.isArray(value)) return value.map(withoutContactKeys);
  if (!isObject(value)) return value;
  return Object.fromEntries(Object.entries(value).filter(([key]) => !CONTACT_KEYS.includes(key)).map(([key, item]) => [key, withoutContactKeys(item)]));
}

/** The registry's record with every person removed, and nothing else. The record given
 * is not changed; a payload that is not a registry record is given back as it is. */
export function withoutPeople(study) {
  if (!isStudy(study)) return study;
  const protocol = { ...study.protocolSection };

  const contacts = protocol.contactsLocationsModule;
  if (isObject(contacts)) {
    const kept = without(contacts, ["centralContacts", "overallOfficials"]);
    if (Array.isArray(contacts.locations)) kept.locations = contacts.locations.map((site) => (isObject(site) ? without(site, ["contacts"]) : site));
    protocol.contactsLocationsModule = kept;
  }

  const sponsors = protocol.sponsorCollaboratorsModule;
  if (isObject(sponsors)) {
    const kept = { ...sponsors };
    if (isObject(sponsors.leadSponsor) && sponsoredByAPerson(sponsors)) kept.leadSponsor = without(sponsors.leadSponsor, ["name"]);
    if (Array.isArray(sponsors.collaborators)) {
      kept.collaborators = sponsors.collaborators.map((one) => (isObject(one) && PERSON_CLASSES.includes(one.class) ? without(one, ["name"]) : one));
    }
    if (isObject(sponsors.responsibleParty)) {
      const { type } = sponsors.responsibleParty;
      kept.responsibleParty = type === undefined ? {} : { type };
    }
    protocol.sponsorCollaboratorsModule = kept;
  }

  const stripped = { ...study, protocolSection: protocol };
  const results = study.resultsSection;
  if (isObject(results) && isObject(results.moreInfoModule)) {
    stripped.resultsSection = { ...results, moreInfoModule: without(results.moreInfoModule, ["pointOfContact"]) };
  }
  return withoutContactKeys(stripped);
}

/** A registry answer without people: one record, or a page of them. */
export function answerWithoutPeople(body) {
  if (isObject(body) && Array.isArray(body.studies)) return { ...body, studies: body.studies.map(withoutPeople) };
  return withoutPeople(body);
}

function hasKey(value, keys) {
  if (Array.isArray(value)) return value.some((item) => hasKey(item, keys));
  if (isObject(value)) return Object.entries(value).some(([key, item]) => keys.includes(key) || hasKey(item, keys));
  return false;
}

/** The kinds of field a record names a person in; none for a record without people or a
 * payload that is not a registry record. Names of fields only, never what they hold. */
export function peopleIn(study) {
  if (!isStudy(study)) return [];
  const protocol = study.protocolSection;
  const found = new Set();
  const contacts = object(protocol.contactsLocationsModule);
  if (filled(contacts.centralContacts)) found.add("centralContacts");
  if (filled(contacts.overallOfficials)) found.add("overallOfficials");
  if (list(contacts.locations).some((site) => filled(object(site).contacts))) found.add("location contacts");
  const sponsors = object(protocol.sponsorCollaboratorsModule);
  const party = object(sponsors.responsibleParty);
  if (INVESTIGATOR_FIELDS.some((field) => filled(party[field]))) found.add("investigator name, title or affiliation");
  if (Object.keys(party).some(key => key !== "type" && !INVESTIGATOR_FIELDS.includes(key))) found.add("responsible party beyond its type");
  if (object(sponsors.leadSponsor).name && sponsoredByAPerson(sponsors)) found.add("person lead sponsor's name");
  if (list(sponsors.collaborators).some((one) => object(one).name && PERSON_CLASSES.includes(object(one).class))) found.add("person collaborator's name");
  if (filled(object(object(study.resultsSection).moreInfoModule).pointOfContact)) found.add("results point of contact");
  if (hasKey(study, ["email"])) found.add("email");
  if (hasKey(study, ["phone", "phoneExt"])) found.add("phone");
  return [...found];
}
