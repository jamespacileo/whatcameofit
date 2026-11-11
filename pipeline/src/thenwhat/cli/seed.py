"""The seed command."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from thenwhat.cli.console import out
from thenwhat.cli.entry import entry_session
from thenwhat.seed.load import load_seed

seed_app = typer.Typer(help="Load checked-in seed claims.", no_args_is_help=True)


@seed_app.command("load")
def seed_load(
    files: Annotated[list[Path], typer.Argument(exists=True, dir_okay=False, help="Seed files.")],
) -> None:
    """Load seed claims as already reviewed. A claim that already exists is left alone.

    Seed decisions are recorded as made by the seed loader, not by you.
    """
    with entry_session() as session:
        for file in files:
            claim = load_seed(session, json.loads(file.read_text()), now=datetime.now(UTC))
            if claim is None:
                out.print(f"Skipped {file.name}: its claim already exists.", markup=False)
            else:
                out.print(
                    f"Loaded {claim.slug} from {file.name}: {claim.current_status.value}.",
                    markup=False,
                )
