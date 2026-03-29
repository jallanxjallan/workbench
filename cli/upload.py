from __future__ import annotations

import typer

from upload.batches import UploadBatchesSimpleError
from upload.instructions import UploadInstructionsError
from upload.packages import UploadPackageSimpleError
from upload.profiles import UploadProfilesSimpleError
from upload.prompts import UploadPromptsError

import upload.batches as batches_source
import upload.instructions as instructions_source
import upload.packages as package_source
import upload.profiles as profiles_source
import upload.prompts as prompts_source

app = typer.Typer(
    help="Compile batches, instructions, profiles, prompts, or packages to NDJSON on stdout.",
    no_args_is_help=True,
)


@app.command("batches")
def upload_batches_command() -> None:
    try:
        raise typer.Exit(int(batches_source.main()))
    except UploadBatchesSimpleError as exc:
        typer.echo(f"upload batches: {exc}", err=True)
        raise typer.Exit(1) from exc
    except Exception as exc:
        typer.echo(f"upload batches: {exc}", err=True)
        raise typer.Exit(1) from exc


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


@app.command("prompts")
def upload_prompts_command() -> None:
    try:
        raise typer.Exit(int(prompts_source.main()))
    except UploadPromptsError as exc:
        typer.echo(f"upload prompts: {exc}", err=True)
        raise typer.Exit(1) from exc
    except Exception as exc:
        typer.echo(f"upload prompts: {exc}", err=True)
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
    raise SystemExit(main())