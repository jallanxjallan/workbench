"""
Run encrypted secrets backup to Dropbox.
"""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

WORKBENCH_ROOT = Path(__file__).resolve().parents[2]


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "backup-secrets",
        help=__doc__.strip(),
        description=__doc__,
    )
    parser.add_argument(
        "args",
        nargs=argparse.REMAINDER,
        help="Arguments forwarded to workbench.backups.secrets_backup.",
    )
    parser.set_defaults(runner=run)


def _trim_forwarded_args(args: list[str]) -> list[str]:
    return [arg for arg in args if arg != "--"]


def run(args: argparse.Namespace) -> int:
    python_bin = os.environ.get(
        "WORKBENCH_PYTHON",
        str(Path.home() / "Python3.13Env" / "bin" / "python"),
    )
    adapters_dir = WORKBENCH_ROOT / "adapters" / "python"
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        f"{adapters_dir}:{existing_pythonpath}" if existing_pythonpath else str(adapters_dir)
    )
    cmd = [
        python_bin,
        "-m",
        "workbench.backups.secrets_backup",
        *_trim_forwarded_args(args.args),
    ]
    completed = subprocess.run(cmd, env=env, check=False)
    return int(completed.returncode)
