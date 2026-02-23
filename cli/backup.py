"""
Backup workflows.
"""

from __future__ import annotations

import argparse

from _runtime import run_bash_script, run_python_module


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "backup",
        help=__doc__.strip(),
        description=__doc__,
    )
    backup_sub = parser.add_subparsers(dest="backup_command")

    project = backup_sub.add_parser("project", help="Run project backup")
    project.add_argument("args", nargs=argparse.REMAINDER)
    project.set_defaults(runner=_run_project)

    secrets = backup_sub.add_parser("secrets", help="Run secrets backup")
    secrets.add_argument("args", nargs=argparse.REMAINDER)
    secrets.set_defaults(runner=_run_secrets)

    snapshot = backup_sub.add_parser("snapshot", help="Run full snapshot backup")
    snapshot.add_argument("args", nargs=argparse.REMAINDER)
    snapshot.set_defaults(runner=_run_snapshot)


def _trim(args: list[str]) -> list[str]:
    return [arg for arg in args if arg != "--"]


def _run_project(parsed: argparse.Namespace) -> int:
    return run_python_module("workbench.backups.backup_project", _trim(parsed.args))


def _run_secrets(parsed: argparse.Namespace) -> int:
    return run_python_module("workbench.backups.secrets_backup", _trim(parsed.args))


def _run_snapshot(parsed: argparse.Namespace) -> int:
    return run_bash_script("shell/commands/backup_snapshot.sh", _trim(parsed.args))
