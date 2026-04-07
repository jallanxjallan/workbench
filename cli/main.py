"""Typer-based `wkb` CLI entrypoint."""

from __future__ import annotations

import sys
from collections.abc import Callable

import typer

from .create_vault import main as create_vault_main
from .stream import main as stream_main
from .upload import main as upload_main
from .writeback import main as writeback_main
from .writenew import main as writenew_main


CommandMain = Callable[[list[str] | None], int | None]

_PASSTHROUGH_SETTINGS = {
    "allow_extra_args": True,
    "ignore_unknown_options": True,
}

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)


def _dispatch(command_main: CommandMain, argv: list[str] | None = None) -> int:
    try:
        result = command_main(argv)
    except SystemExit as exc:
        code = exc.code
        return int(code if isinstance(code, int) else 1)

    if result is None:
        return 0
    return int(result)


def _run_passthrough(command_main: CommandMain, ctx: typer.Context) -> None:
    code = _dispatch(command_main, list(ctx.args))
    if code != 0:
        raise typer.Exit(code=code)


@app.command("create-vault", context_settings=_PASSTHROUGH_SETTINGS)
def create_vault_command(ctx: typer.Context) -> None:
    _run_passthrough(create_vault_main, ctx)


@app.command("stream", context_settings=_PASSTHROUGH_SETTINGS)
def stream_command(ctx: typer.Context) -> None:
    _run_passthrough(stream_main, ctx)


@app.command("upload", context_settings=_PASSTHROUGH_SETTINGS)
def upload_command(ctx: typer.Context) -> None:
    _run_passthrough(upload_main, ctx)


@app.command("writeback", context_settings=_PASSTHROUGH_SETTINGS)
def writeback_command(ctx: typer.Context) -> None:
    _run_passthrough(writeback_main, ctx)


@app.command("writenew", context_settings=_PASSTHROUGH_SETTINGS)
def writenew_command(ctx: typer.Context) -> None:
    _run_passthrough(writenew_main, ctx)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        app(args=args, prog_name="wkb")
        return 0
    except SystemExit as exc:
        code = exc.code
        return int(code if isinstance(code, int) else 1)


if __name__ == "__main__":
    raise SystemExit(main())