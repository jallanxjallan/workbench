"""
Vault operations.
"""

from __future__ import annotations

import argparse

from _runtime import run_python_module


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "vault",
        help=__doc__.strip(),
        description=__doc__,
    )
    vault_sub = parser.add_subparsers(dest="vault_command")

    create = vault_sub.add_parser("create-project", help="Create project vault scaffold")
    create.add_argument("args", nargs=argparse.REMAINDER)
    create.set_defaults(runner=_run_create_project)


def _trim(args: list[str]) -> list[str]:
    return [arg for arg in args if arg != "--"]


def _run_create_project(parsed: argparse.Namespace) -> int:
    return run_python_module("workbench.vault.create_project", _trim(parsed.args))
