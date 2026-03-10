"""`wkb` dispatcher entrypoint."""

from __future__ import annotations

import importlib
import sys
from types import ModuleType
from typing import Callable

from workbench.cli import discover_commands


def _load_module(module_name: str) -> ModuleType:
    return importlib.import_module(module_name)


def _get_parser(module: ModuleType) -> object | None:
    parser_factory = getattr(module, "parser", None)
    if callable(parser_factory):
        return parser_factory()
    parser_factory = getattr(module, "_parser", None)
    if callable(parser_factory):
        return parser_factory()
    return None


def _command_description(module_name: str) -> str:
    module = _load_module(module_name)
    parser = _get_parser(module)
    if parser is None:
        return ""
    return str(getattr(parser, "description", "") or "")


def _print_top_help(commands: dict[str, str]) -> None:
    print("Workbench CLI")
    print()
    print("Usage:")
    print("  wkb <command> [options]")
    print()
    print("Commands:")
    print()
    for name, module_name in sorted(commands.items()):
        print(f"  {name:18} {_command_description(module_name)}")
    print()
    print("Use:")
    print("  wkb help <command>")


def _resolve_command(argv: list[str], commands: dict[str, str]) -> tuple[str, int] | None:
    max_depth = min(4, len(argv))
    for depth in range(max_depth, 0, -1):
        candidate = "-".join(argv[:depth])
        if candidate in commands:
            return candidate, depth
    return None


def _load_main(module_name: str) -> Callable[[list[str] | None], int]:
    module = _load_module(module_name)
    main = getattr(module, "main", None)
    if not callable(main):
        raise RuntimeError(f"module missing callable main(argv): {module_name}")
    return main


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    commands = discover_commands()

    if not args or args[0] in {"-h", "--help", "help"}:
        if args and args[0] == "help" and len(args) > 1:
            resolved = _resolve_command(args[1:], commands)
            if resolved is None:
                print(f"Unknown command: {' '.join(args[1:])}", file=sys.stderr)
                return 2
            command, _ = resolved
            module = _load_module(commands[command])
            parser = _get_parser(module)
            if parser is None:
                print(f"Command has no parser: {command}", file=sys.stderr)
                return 2
            parser.print_help()
            return 0
        _print_top_help(commands)
        return 0

    resolved = _resolve_command(args, commands)
    if resolved is None:
        print(f"Unknown command: {' '.join(args)}", file=sys.stderr)
        return 2

    command, consumed = resolved
    command_main = _load_main(commands[command])
    result = command_main(args[consumed:])
    if result is None:
        return 0
    return int(result)


def entrypoint() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(main())
