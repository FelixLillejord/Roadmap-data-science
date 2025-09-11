"""CLI entrypoint for the public sector job scraper.

Provides command-line interface for running discovery and detail parsing,
with options like `--full`, `--debug`, and `--out-dir`.
"""

from __future__ import annotations

from typing import Optional, Sequence


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the CLI.

    Placeholder implementation. Real logic will be wired in later tasks.
    """
    # TODO: Implement argparse and wiring in task 10.x
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

