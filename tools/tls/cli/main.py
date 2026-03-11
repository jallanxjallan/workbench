"""CLI entrypoint for tls."""

from __future__ import annotations

import json
from pathlib import Path

import typer
import yaml

from tls.image.normalize import normalize_image
from tls.image.thumbnail import ThumbnailError, generate_thumbnail
from tls.pdf.extract_images import extract_images
from tls.pdf.extract_text import extract_text

app = typer.Typer(help="Tools Layer System (tls)")


def _registry_path() -> Path:
    return Path(__file__).resolve().parents[1] / "tools_registry.yaml"


def _load_registry() -> dict[str, str]:
    path = _registry_path()
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise typer.Exit(code=1)
    resolved: dict[str, str] = {}
    for key, value in data.items():
        if isinstance(key, str) and isinstance(value, str):
            resolved[key] = value
    return resolved


@app.command()
def info() -> None:
    """Display TLS environment info."""
    typer.echo("TLS toolchain available")


@app.command()
def resolve(tool_name: str) -> None:
    """Resolve a logical tool name from tls/tools_registry.yaml."""
    registry = _load_registry()
    command = registry.get(tool_name)
    if not command:
        raise typer.BadParameter(f"unknown tool: {tool_name}")
    typer.echo(command)


@app.command("image-thumb")
def image_thumb(
    source: Path = typer.Option(..., "--source", exists=True, file_okay=True, dir_okay=False),
    destination: Path = typer.Option(..., "--destination"),
    width: int = typer.Option(512, min=1),
    height: int = typer.Option(512, min=1),
    overwrite: bool = typer.Option(False, "--overwrite"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Generate an image thumbnail."""
    try:
        generated = generate_thumbnail(
            source_path=source,
            destination_path=destination,
            size=(width, height),
            overwrite=overwrite,
        )
    except ThumbnailError as exc:
        raise typer.BadParameter(str(exc)) from exc

    payload = {
        "source": str(source),
        "destination": str(destination),
        "generated": generated,
    }
    if json_output:
        typer.echo(json.dumps(payload))
        return
    typer.echo("generated" if generated else "reused")


@app.command("image-normalize")
def image_normalize(
    source: Path = typer.Option(..., "--source", exists=True, file_okay=True, dir_okay=False),
    destination: Path = typer.Option(..., "--destination"),
) -> None:
    """Normalize an image to RGB and write to destination."""
    normalize_image(source_path=source, destination_path=destination)
    typer.echo(str(destination))


@app.command("pdf-extract-text")
def pdf_extract_text(source: Path = typer.Option(..., "--source", exists=True, file_okay=True, dir_okay=False)) -> None:
    """Extract text from a PDF file."""
    text = extract_text(source)
    typer.echo(text)


@app.command("pdf-extract-images")
def pdf_extract_images(
    source: Path = typer.Option(..., "--source", exists=True, file_okay=True, dir_okay=False),
    output_dir: Path = typer.Option(..., "--output-dir"),
) -> None:
    """Extract embedded images from a PDF file."""
    paths = extract_images(source, output_dir)
    for path in paths:
        typer.echo(str(path))


def cli() -> None:
    app()


if __name__ == "__main__":
    cli()
