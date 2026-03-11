"""Thumbnail generation dispatch via tls external tools."""

from __future__ import annotations

import json
import shlex
import shutil
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from workbench.config.roots import WORKBENCH_ROOT
from workbench.lib.subprocess import CommandError, run_text

DEFAULT_THUMB_SIZE = (512, 512)


class ThumbnailError(RuntimeError):
    """Raised when thumbnail generation fails."""


def _resolve_tls_executable() -> str:
    preferred = WORKBENCH_ROOT / "tools" / "bin" / "tls"
    legacy_preferred = Path.home().resolve() / "Tools" / "bin" / "tls"
    tls_on_path = shutil.which("tls")
    if tls_on_path:
        return tls_on_path
    if preferred.exists():
        return str(preferred)
    if legacy_preferred.exists():
        return str(legacy_preferred)
    raise ThumbnailError(
        "tls executable not found (expected in PATH or workbench/tools/bin/tls)"
    )


def _resolve_tool_command(tool_name: str) -> list[str]:
    tls_exec = _resolve_tls_executable()
    try:
        resolved = run_text([tls_exec, "resolve", tool_name]).strip()
    except CommandError as exc:
        raise ThumbnailError(f"failed to resolve tls tool '{tool_name}': {exc}") from exc

    if not resolved:
        raise ThumbnailError(f"tls resolve returned empty command for '{tool_name}'")

    command = shlex.split(resolved)
    if not command:
        raise ThumbnailError(f"unable to parse tls command for '{tool_name}'")

    # Ensure nested invocations can still run when `tls` is not in PATH.
    if command[0] == "tls" and shutil.which("tls") is None:
        command[0] = tls_exec

    return command


def generate_thumbnail(
    source_path: Path,
    destination_path: Path,
    *,
    size: tuple[int, int] = DEFAULT_THUMB_SIZE,
) -> bool:
    """Generate a thumbnail via tls and return True when a new file was written."""
    if destination_path.exists():
        return False

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        command = _resolve_tool_command("image_thumb")
        command.extend(
            [
                "--source",
                str(source_path),
                "--destination",
                str(destination_path),
                "--width",
                str(size[0]),
                "--height",
                str(size[1]),
                "--json",
            ]
        )
        output = run_text(command)
        payload = json.loads(output.strip() or "{}")
        generated = payload.get("generated")
        if isinstance(generated, bool):
            return generated
        return destination_path.exists()
    except (ThumbnailError, CommandError, json.JSONDecodeError):
        # Fallback path keeps compile-assets functional even when `tls` is
        # unavailable in local/dev test environments.
        try:
            with Image.open(source_path) as image:
                image.thumbnail(size)
                image.save(destination_path)
            return True
        except (OSError, UnidentifiedImageError) as exc:
            raise ThumbnailError(f"thumbnail generation failed: {exc}") from exc


__all__ = ["DEFAULT_THUMB_SIZE", "ThumbnailError", "generate_thumbnail"]
