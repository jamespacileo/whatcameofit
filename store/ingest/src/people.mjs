// People in a ClinicalTrials.gov record. The project keeps no personal data beyond
// subscriber emails (CLAUDE.md), and a trial's full record names people: its officials
// and contacts, each site's contacts, the investigator a responsible party is, a sponsor
// or collaborator who is a person, and the results' point of contact. A writer removes
// them before it hands a record over (pipeline/src/thenwhat/sources/people.py,
// `without_people`); this is that file's `people_in`, so that the door can refuse a
// record that still has them. The two must say the same.
export const PERSON_CLASSES = ["INDIV", "INDIVIDUAL"];
export const INVESTIGATOR_FIELDS = ["investigatorFullName", "investigatorTitle", "investigatorAffiliation", "oldNameTitle"];
// All that is kept of a responsible party: whatever else it holds describes a person.
export const PARTY_KEPT = ["type"];
// Keys that hold a person's means of contact, wherever they appear.
export const CONTACT_KEYS = ["email", "phone", "phoneExt"];
// A registry's person keys, wherever they appear: for a record that is not shaped as a
// whole study but carries part of one.
export const REGISTRY_PERSON_KEYS = ["centralContacts", "overallOfficials", "investigatorFullName", "investigatorTitle", "investigatorAffiliation", "oldNameTitle", "pointOfContact", "contacts"];
// The keys that hold a paper's abstract or body text, in each index's record. The store
// keeps a paper's title, byline and links, never its text (docs/adr/0011).
export const ABSTRACT_KEYS = ["abstractText", "abstract_inverted_index", "abstract", "AbstractText", "fullText"];
const object = (value) => (value && typeof value === "object" && !Array.isArray(value) ? value : {});
const list = (value) => (Array.isArray(value) ? value : []);
const filled = (value) => (Array.isArray(value) ? value.length > 0 : value && typeof value === "object" ? Object.keys(value).length > 0 : Boolean(value));

function hasKey(value, keys) {
  if (Array.isArray(value)) return value.some((item) => hasKey(item, keys));
  if (value && typeof value === "object") return Object.entries(value).some(([key, item]) => keys.includes(key) || hasKey(item, keys));
  return false;
}
// Which of these keys appear anywhere in a value.
function keysFound(value, keys, found = new Set()) {
  if (Array.isArray(value)) for (const item of value) keysFound(item, keys, found);
  else if (value && typeof value === "object") for (const [key, item] of Object.entries(value)) { if (keys.includes(key)) found.add(key); keysFound(item, keys, found); }
  return found;
}
const isStudy = (value) => { const protocol = object(value).protocolSection; return Boolean(protocol) && typeof protocol === "object" && !Array.isArray(protocol); };

// The kinds of field a study names a person in; none for a record without people or a
// payload that is not a registry record. Names of fields only, never what they hold.
export function peopleIn(study) {
  if (!isStudy(study)) return [];
  const protocol = study.protocolSection;
  const found = new Set();
  const contacts = object(protocol.contactsLocationsModule);
  if (filled(contacts.centralContacts)) found.add("centralContacts");
  if (filled(contacts.overallOfficials)) found.add("overallOfficials");
  if (list(contacts.locations).some((site) => filled(object(site).contacts))) found.add("location contacts");
  const sponsors = object(protocol.sponsorCollaboratorsModule);
  const party = object(sponsors.responsibleParty), lead = object(sponsors.leadSponsor);
  if (INVESTIGATOR_FIELDS.some((field) => filled(party[field]))) found.add("investigator name, title or affiliation");
  // Anything of a responsible party beyond what is kept: the registry may name the person another way.
  if (Object.keys(party).some((key) => !PARTY_KEPT.includes(key) && !INVESTIGATOR_FIELDS.includes(key))) found.add("responsible party beyond its type");
  if (lead.name && (PERSON_CLASSES.includes(lead.class) || party.type === "SPONSOR_INVESTIGATOR")) found.add("person lead sponsor's name");
  if (list(sponsors.collaborators).some((one) => object(one).name && PERSON_CLASSES.includes(object(one).class))) found.add("person collaborator's name");
  if (filled(object(object(study.resultsSection).moreInfoModule).pointOfContact)) found.add("results point of contact");
  if (hasKey(study, ["email"])) found.add("email");
  if (hasKey(study, ["phone", "phoneExt"])) found.add("phone");
  return [...found];
}

// What a stored payload may not hold, as the pipeline's own proof reads it
// (pipeline/src/thenwhat/store/people.py, `_people`): a study's people; in any other
// payload a registry's person keys, an email or a phone, wherever they are; and a paper's
// abstract or text. A paper's byline is not a person field and stays (docs/adr/0011).
// `people` and `text` name fields only.
export function forbiddenIn(payload) {
  if (isStudy(payload)) return { people: peopleIn(payload), text: [] };
  return { people: [...keysFound(payload, [...REGISTRY_PERSON_KEYS, ...CONTACT_KEYS])], text: [...keysFound(payload, ABSTRACT_KEYS)] };
}

// The same of a payload's body as it travels: text that may or may not be JSON.
const NAMED = [...REGISTRY_PERSON_KEYS, ...CONTACT_KEYS, ...ABSTRACT_KEYS, "protocolSection"].map((key) => `"${key}"`);
export function forbiddenInText(text) {
  if (!NAMED.some((key) => text.includes(key))) return { people: [], text: [] };
  try { return forbiddenIn(JSON.parse(text)); } catch { return { people: [], text: [] }; }
}
