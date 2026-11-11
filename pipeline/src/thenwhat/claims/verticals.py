"""The configured set of verticals: slug to display title.

Add a vertical here before entering claims for it. The site lists a vertical
only once it has a published claim.

Each vertical may sit under one group, a broader body system or disease area the
site files it under. Add the group to GROUPS, then name it in VERTICAL_GROUPS.
"""

VERTICALS: dict[str, str] = {
    "ageing": "Ageing",
    "allergies": "Allergies",
    "brain-and-nerves": "Brain and nerves",
    "cancer": "Cancer",
    "dementia": "Dementia",
    "dental-regeneration": "Dental regeneration",
    "diabetes-and-metabolism": "Diabetes and metabolism",
    "hair-loss": "Hair loss",
    "heart-and-circulation": "Heart and circulation",
    "infections": "Infections",
    "mental-health": "Mental health",
    "pain": "Pain",
    "sight-and-hearing": "Sight and hearing",
    "transplants": "Transplants",
}

# Group slug to display title.
GROUPS: dict[str, str] = {
    "ageing-and-longevity": "Ageing and longevity",
    "brain-and-mind": "Brain and mind",
    "cancer": "Cancer",
    "heart-and-metabolism": "Heart and metabolism",
    "immune-system-and-infections": "Immune system and infections",
    "mouth-and-teeth": "Mouth and teeth",
    "senses": "Senses",
    "skin-and-hair": "Skin and hair",
}

# Vertical slug to group slug. A vertical left out has no group.
VERTICAL_GROUPS: dict[str, str] = {
    "ageing": "ageing-and-longevity",
    "allergies": "immune-system-and-infections",
    "brain-and-nerves": "brain-and-mind",
    "cancer": "cancer",
    "dementia": "brain-and-mind",
    "dental-regeneration": "mouth-and-teeth",
    "diabetes-and-metabolism": "heart-and-metabolism",
    "hair-loss": "skin-and-hair",
    "heart-and-circulation": "heart-and-metabolism",
    "infections": "immune-system-and-infections",
    "mental-health": "brain-and-mind",
    "pain": "brain-and-mind",
    "sight-and-hearing": "senses",
    "transplants": "immune-system-and-infections",
}
