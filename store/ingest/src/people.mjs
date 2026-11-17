// People in a ClinicalTrials.gov record. The project keeps no personal data beyond
// subscriber emails (CLAUDE.md), and a trial's full record names people: its officials
// and contacts, each site's contacts, the investigator a responsible party is, a sponsor
// or collaborator who is a person, and the results' point of contact. A writer removes
// them before it hands a record over (pipeline/src/thenwhat/sources/people.py,
// `without_people`); this is that file's `people_in`, so that the door can refuse a
// record that still has them. The two must say the same.
const PERSON_CLASSES = ["INDIV", "INDIVIDUAL"];
const INVESTIGATOR_FIELDS = ["investigatorFullName", "investigatorTitle", "investigatorAffiliation", "oldNameTitle"];
const object = (value) => (value && typeof value === "object" && !Array.isArray(value) ? value : {});
const list = (value) => (Array.isArray(value) ? value : []);
const filled = (value) => (Array.isArray(value) ? value.length > 0 : value && typeof value === "object" ? Object.keys(value).length > 0 : Boolean(value));

function hasKey(value, keys) {
  if (Array.isArray(value)) return value.some((item) => hasKey(item, keys));
  if (value && typeof value === "object") return Object.entries(value).some(([key, item]) => keys.includes(key) || hasKey(item, keys));
  return false;
}

// The kinds of field a record names a person in; none for a record without people or a
// payload that is not a registry record. Names of fields only, never what they hold.
export function peopleIn(study) {
  const protocol = object(study).protocolSection;
  if (!protocol || typeof protocol !== "object" || Array.isArray(protocol)) return [];
  const found = new Set();
  const contacts = object(protocol.contactsLocationsModule);
  if (filled(contacts.centralContacts)) found.add("centralContacts");
  if (filled(contacts.overallOfficials)) found.add("overallOfficials");
  if (list(contacts.locations).some((site) => filled(object(site).contacts))) found.add("location contacts");
  const sponsors = object(protocol.sponsorCollaboratorsModule);
  const party = object(sponsors.responsibleParty), lead = object(sponsors.leadSponsor);
  if (INVESTIGATOR_FIELDS.some((field) => filled(party[field]))) found.add("investigator name, title or affiliation");
  if (lead.name && (PERSON_CLASSES.includes(lead.class) || party.type === "SPONSOR_INVESTIGATOR")) found.add("person lead sponsor's name");
  if (list(sponsors.collaborators).some((one) => object(one).name && PERSON_CLASSES.includes(object(one).class))) found.add("person collaborator's name");
  if (filled(object(object(study.resultsSection).moreInfoModule).pointOfContact)) found.add("results point of contact");
  if (hasKey(study, ["email"])) found.add("email");
  if (hasKey(study, ["phone", "phoneExt"])) found.add("phone");
  return [...found];
}

// The same of a payload's body as it travels: text that may or may not be JSON.
export function peopleInText(text) {
  if (!text.includes("protocolSection")) return [];
  try { return peopleIn(JSON.parse(text)); } catch { return []; }
}
