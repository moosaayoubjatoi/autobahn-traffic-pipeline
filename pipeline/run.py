"""Run the full pipeline: extract -> load -> dbt build (models + tests).

Usage: python -m pipeline.run
"""

import subprocess
import sys
from pathlib import Path

from pipeline import extract, load

TRANSFORM_DIR = Path(__file__).resolve().parent.parent / "transform"


def run_dbt() -> None:
    """Build all dbt models and run their tests. Stops the pipeline if a test fails."""
    subprocess.run(
        [sys.executable, "-m", "dbt.cli.main", "build", "--profiles-dir", "."],
        cwd=TRANSFORM_DIR,
        check=True,
    )


def main() -> None:
    extract.run()
    load.run()
    run_dbt()


if __name__ == "__main__":
    main()
