from __future__ import annotations

import typer

import upload.uploader as content_source

app = typer.Typer(
    help="Compile content or configuration records to NDJSON on stdout.",
    no_args_is_help=True,
)


@app.command("content")
def upload_content_command() -> None:
    code = int(content_source.main())
    if code:
        raise typer.Exit(code)


@app.command("configuration")
def upload_configuration_command() -> None:
    typer.echo("upload configuration: not implemented yet", err=True)
    raise typer.Exit(1)


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