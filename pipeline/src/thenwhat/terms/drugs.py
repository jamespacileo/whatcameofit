"""The reasons a drug card and the target card a drug's record gives are made. Found by
rule: neither is scored. Behavior: openspec knowledge-cards, "A drug card states what it
is and what it acts on" and "A drug record's target comes before a named gene".
"""

# The drug source's own name for the drug equals this name of the claim.
DRUG_NAME_EQUALS_NAME = "drug_name_equals_name"
# The record of the drug with this name gives this as the one protein it acts on.
DRUG_RECORD_NAMES_TARGET = "drug_record_names_target"
DRUG_REASON_CODES = (DRUG_NAME_EQUALS_NAME, DRUG_RECORD_NAMES_TARGET)
