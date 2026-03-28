from __future__ import annotations

import sys

import typer

from upload.instructions import UploadInstructionsError
from upload.package import UploadPackageSimpleError
from upload.profiles import UploadProfilesSimpleError
import upload.instructions as instructions_source
import upload.package as package_source
import upload.profiles as profiles_source

app = typer.Typer(
    help="Compile instructions, profiles, or packages to NDJSON on stdout.",
    no_args_is_help=True,
)


@app.command("instructions")
def upload_instructions_command() -> None:
    try:
        raise typer.Exit(int(instructions_source.main()))
    except UploadInstructionsError as exc:
        typer.echo(f"upload instructions: {exc}", err=True)
        raise typer.Exit(1) from exc
    except Exception as exc:
        typer.echo(f"upload instructions: {exc}", err=True)
        raise typer.Exit(1) from exc


@app.command("profiles")
def upload_profiles_command() -> None:
    try:
        raise typer.Exit(int(profiles_source.main()))
    except UploadProfilesSimpleError as exc:
        typer.echo(f"upload profiles: {exc}", err=True)
        raise typer.Exit(1) from exc
    except Exception as exc:
        typer.echo(f"upload profiles: {exc}", err=True)
        raise typer.Exit(1) from exc


@app.command("packages")
def upload_packages_command() -> None:
    try:
        raise typer.Exit(int(package_source.main()))
    except UploadPackageSimpleError as exc:
        typer.echo(f"upload packages: {exc}", err=True)
        raise typer.Exit(1) from exc
    except Exception as exc:
        typer.echo(f"upload packages: {exc}", err=True)
        raise typer.Exit(1) from exc
    

def main(argv: list[str] | None = None) -> int:
    args = [] if argv is None else list(argv)
    try:
        app(args=args, prog_name="wkb upload")
        return 0
    except SystemExit as exc:
        code = exc.code
        return int(code if isinstance(code, int) else 1)


if __name__ == "__main__":
    app()