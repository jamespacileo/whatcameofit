"""Read NLM's annual descriptor download into the clinical vocabulary."""

import gzip
import re
from pathlib import Path
from xml.etree.ElementTree import iterparse

from thenwhat.clinical.vocabulary import Vocabulary
from thenwhat.sources.mesh import BASE


def mesh_xml_vocabulary(path: Path) -> Vocabulary:
    source = re.fullmatch(r"desc(\d{4})\.(?:gz|xml)", path.name)
    if source is None:
        raise ValueError("Expected an NLM descriptor file named descYYYY.gz or descYYYY.xml.")
    year = source.group(1)
    descriptors: dict[str, tuple[str, list[str]]] = {}
    with gzip.open(path, "rb") if path.suffix == ".gz" else path.open("rb") as handle:
        items = iterparse(handle, events=("start", "end"))
        _, root = next(items)
        if root.tag != "DescriptorRecordSet":
            raise ValueError("The file does not contain an NLM descriptor record set.")
        for event, entry in items:
            if event != "end" or entry.tag != "DescriptorRecord":
                continue
            identifier = entry.findtext("DescriptorUI")
            label = entry.findtext("DescriptorName/String")
            if not identifier or not label or identifier in descriptors:
                raise ValueError(f"Invalid or duplicate MeSH descriptor {identifier!r}.")
            trees = [
                number.text for number in entry.findall("TreeNumberList/TreeNumber") if number.text
            ]
            descriptors[identifier] = label, trees
            root.remove(entry)
    if not descriptors:
        raise ValueError("The NLM descriptor file contains no records.")

    by_tree = {
        number: identifier for identifier, (_, trees) in descriptors.items() for number in trees
    }
    prefix = f"{BASE}/{year}/"
    records = (
        (
            identifier,
            {
                "term": {
                    "@id": prefix + identifier,
                    "label": label,
                    "treeNumber": [prefix + number for number in trees],
                    "broaderDescriptor": sorted(
                        {
                            prefix + parent
                            for number in trees
                            if (parent := by_tree.get(number.rpartition(".")[0]))
                        }
                    ),
                },
            },
        )
        for identifier, (label, trees) in descriptors.items()
    )
    return Vocabulary(records, year=year)
