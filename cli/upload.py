from __future__ import annotations

from pathlib import Path

import typer

import upload.working as working_source
import upload.control as control_source

app = typer.Typer(
    help="Compile content or control records to NDJSON on stdout.",
    no_args_is_help=True,
)


@app.command("working")
def upload_working_command() -> None:
    code = int(working_source.main())
    if code:
        raise typer.Exit(code)


@app.command("control")
def upload_control_command(
    manifest: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to the JSON manifest file.",
    ),
) -> None:
    code = int(control_source.main(manifest))
    if code:
        raise typer.Exit(code)


def main(argv: list[str] | None = None) -> int:
    args = [] if argv is None else list(argv)
    try:
        app(args=args, prog_name="wkb upload")
        return 0
    except SystemExit as exc:
        code = exc.code
        return int(code if isinstance(code, int) else 1)


if __name__ == "__main__":
    raise SystemExit(main())