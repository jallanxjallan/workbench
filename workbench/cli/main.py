"""`wkb` dispatcher entrypoint."""

from __future__ import annotations

import importlib
import sys
from typing import Callable

from workbench.cli.registry import REGISTRY, CommandEntry


def _print_root_help() -> None:
    print("Usage: wkb <namespace> [command] [args]")
    print()
    print("Namespaces:")
    for name, entry in REGISTRY.items():
        print(f"  {name:<8} {entry.summary}")
    print()
    print("Run `wkb <namespace>` to list commands.")
    print("Run `wkb <namespace> <command> --help` for command help.")


def _print_namespace_help(namespace: str) -> None:
    entry = REGISTRY[namespace]
    print(f"Usage: wkb {namespace} <command> [args]")
    print()
    print(f"{namespace} commands:")
    for cmd, cmd_entry in entry.commands.items():
        print(f"  {cmd:<16} {cmd_entry.summary}")


def _load_main(entry: CommandEntry) -> Callable[[list[str] | None], int]:
    module = importlib.import_module(entry.module)
    main = getattr(module, "main", None)
    if not callable(main):
        raise RuntimeError(f"module missing callable main(argv): {entry.module}")
    return main


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)

    if not args or args[0] in {"-h", "--help"}:
        _print_root_help()
        return 0

    namespace = args[0]
    if namespace not in REGISTRY:
        print(f"wkb: unknown namespace '{namespace}'", file=sys.stderr)
        _print_root_help()
        return 2

    if len(args) == 1 or args[1] in {"-h", "--help"}:
        _print_namespace_help(namespace)
        return 0

    command = args[1]
    namespace_entry = REGISTRY[namespace]
    command_entry = namespace_entry.commands.get(command)
    if command_entry is None:
        print(f"wkb: unknown command '{namespace} {command}'", file=sys.stderr)
        _print_namespace_help(namespace)
        return 2

    command_main = _load_main(command_entry)
    return int(command_main(args[2:]))


def entrypoint() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(main())
