"""
Split, write, and select adapter tools.
"""

from __future__ import annotations

import argparse

from _runtime import run_bash_script, run_python_module


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "split",
        help=__doc__.strip(),
        description=__doc__,
    )
    split_sub = parser.add_subparsers(dest="split_command")

    files = split_sub.add_parser("files", help="Split NDJSON records on section markers")
    files.add_argument("args", nargs=argparse.REMAINDER)
    files.set_defaults(runner=_run_files)

    write = split_sub.add_parser("write", help="Write NDJSON records to vault files")
    write.add_argument("args", nargs=argparse.REMAINDER)
    write.set_defaults(runner=_run_write)

    records = split_sub.add_parser("select-records", help="Resolve selected paths into records")
    records.add_argument("args", nargs=argparse.REMAINDER)
    records.set_defaults(runner=_run_select_records)

    sentinel = split_sub.add_parser("select-sentinel", help="Select files by ASC sentinel")
    sentinel.add_argument("args", nargs=argparse.REMAINDER)
    sentinel.set_defaults(runner=_run_select_sentinel)

    smoke = split_sub.add_parser("smoke", help="Run split/write smoke test")
    smoke.add_argument("args", nargs=argparse.REMAINDER)
    smoke.set_defaults(runner=_run_smoke)


def _trim(args: list[str]) -> list[str]:
    return [arg for arg in args if arg != "--"]


def _run_files(parsed: argparse.Namespace) -> int:
    return run_python_module("workbench.adapters.split_files", _trim(parsed.args))


def _run_write(parsed: argparse.Namespace) -> int:
    return run_python_module("workbench.adapters.write_vault_files", _trim(parsed.args))


def _run_select_records(parsed: argparse.Namespace) -> int:
    return run_python_module("workbench.adapters.select.select_records", _trim(parsed.args))


def _run_select_sentinel(parsed: argparse.Namespace) -> int:
    return run_python_module("workbench.adapters.select.select_sentinel", _trim(parsed.args))


def _run_smoke(parsed: argparse.Namespace) -> int:
    return run_bash_script("dev/experiments/smoke_split_write.sh", _trim(parsed.args))
