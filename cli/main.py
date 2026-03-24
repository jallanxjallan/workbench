"""Typer-based `wkb` CLI entrypoint."""

from __future__ import annotations

import sys

import typer

from cli import load_command_module


_PASSTHROUGH_SETTINGS = {
    "allow_extra_args": True,
    "ignore_unknown_options": True,
}

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)


def _dispatch(command_name: str, argv: list[str] | None = None) -> int:
    module = load_command_module(command_name)
    command_main = getattr(module, "main", None)
    if not callable(command_main):
        raise RuntimeError(f"command module missing main(argv): {module.__name__}")

    try:
        result = command_main(argv)
    except SystemExit as exc:
        code = exc.code
        return int(code if isinstance(code, int) else 1)
    if result is None:
        return 0
    return int(result)


def _run_passthrough(command_name: str, ctx: typer.Context) -> None:
    code = _dispatch(command_name, list(ctx.args))
    if code != 0:
        raise typer.Exit(code=code)

@app.command("create-vault", context_settings=_PASSTHROUGH_SETTINGS)
def create_vault_command(ctx: typer.Context) -> None:
    _run_passthrough("create-vault", ctx)


@app.command("slug_filepaths", context_settings=_PASSTHROUGH_SETTINGS)
def slugs_to_files_command(ctx: typer.Context) -> None:
    _run_passthrough("slug_filepaths", ctx)


@app.command("stream", context_settings=_PASSTHROUGH_SETTINGS)
def stream_command(ctx: typer.Context) -> None:
    _run_passthrough("stream", ctx)


@app.command("writeback", context_settings=_PASSTHROUGH_SETTINGS)
def writeback_command(ctx: typer.Context) -> None:
    _run_passthrough("writeback", ctx)


@app.command("writenew", context_settings=_PASSTHROUGH_SETTINGS)
def writenew_command(ctx: typer.Context) -> None:
    _run_passthrough("writenew", ctx)


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
