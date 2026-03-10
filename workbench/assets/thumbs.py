"""Thumbnail generation dispatch via tls external tools."""

from __future__ import annotations

import json
import shlex
import shutil
from pathlib import Path

from workbench.lib.subprocess import CommandError, run_text

DEFAULT_THUMB_SIZE = (512, 512)


class ThumbnailError(RuntimeError):
    """Raised when thumbnail generation fails."""


def _resolve_tls_executable() -> str:
    preferred = Path.home().resolve() / "Tools" / "bin" / "tls"
    tls_on_path = shutil.which("tls")
    if tls_on_path:
        return tls_on_path
    if preferred.exists():
        return str(preferred)
    raise ThumbnailError(
        "tls executable not found (expected in PATH or ~/Tools/bin/tls)"
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

    try:
        output = run_text(command)
    except CommandError as exc:
        raise ThumbnailError(f"tls thumbnail generation failed: {exc}") from exc

    try:
        payload = json.loads(output.strip() or "{}")
    except json.JSONDecodeError as exc:
        raise ThumbnailError(f"tls image-thumb returned invalid JSON: {exc}") from exc

    generated = payload.get("generated")
    if isinstance(generated, bool):
        return generated

    return destination_path.exists()


__all__ = ["DEFAULT_THUMB_SIZE", "ThumbnailError", "generate_thumbnail"]
