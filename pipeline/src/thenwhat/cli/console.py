"""Shared consoles: results go to stdout, refusals and errors to stderr."""

from rich.console import Console

out = Console(soft_wrap=True, highlight=False)
err = Console(stderr=True, soft_wrap=True, highlight=False)
