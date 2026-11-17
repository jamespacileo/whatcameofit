"""Hold an export taken from the truth store to what the site reads, and say how it
compares with the snapshot the site is built from today. A rehearsal's check (openspec
truth-store, "A deployment can rehearse taking its export from the store"): it reads
three files and changes none.

    python -m thenwhat.export.rehearsal EXPORT SCHEMA PUBLISHED_SNAPSHOT
"""

import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


def problems(export: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    """Why the export cannot be the site's: where it breaks the schema, or that it holds
    no claim."""
    found = [
        f"{'/'.join(str(part) for part in error.absolute_path) or 'the export'}: {error.message}"
        for error in sorted(Draft202012Validator(schema).iter_errors(export), key=str)
    ]
    if not export.get("claims"):
        found.append("The export holds no claim.")
    return found


def against(export: dict[str, Any], published: dict[str, Any]) -> list[str]:
    """How the export's claims compare with the published snapshot's, in words. A
    difference here is expected whenever the store has moved on since the snapshot."""
    ours = {claim["slug"] for claim in export.get("claims", [])}
    theirs = {claim["slug"] for claim in published.get("claims", [])}
    lines = [
        f"{len(ours)} claims from the store, {len(theirs)} in the published snapshot,"
        f" {len(ours & theirs)} in both."
    ]
    for label, slugs in (
        ("Only from the store", ours - theirs),
        ("Only in the snapshot", theirs - ours),
    ):
        if slugs:
            shown = ", ".join(sorted(slugs)[:10])
            more = f" and {len(slugs) - 10} more" if len(slugs) > 10 else ""
            lines.append(f"{label}: {shown}{more}.")
    return lines


def main(arguments: list[str]) -> int:
    if len(arguments) != 3:
        print("Usage: python -m thenwhat.export.rehearsal EXPORT SCHEMA PUBLISHED_SNAPSHOT")
        return 2
    export, schema, published = (json.loads(Path(name).read_text()) for name in arguments)
    found = problems(export, schema)
    for line in found[:20]:
        print(line)
    if found:
        print(f"The export from the store is not one the site reads: {len(found)} problems.")
        return 1
    print("The export from the store is in the schema the site reads.")
    for line in against(export, published):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
