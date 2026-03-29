from __future__ import annotations

from pathlib import Path
import sys

from transport.pandoc import PandocError, PandocJob, run_pandoc_jobs_serial
from scan import rg_search
from vault.validate import validate_vault


PANDOC_DEFAULTS = "upload_prompts"
MARKDOWN_EXTENSIONS = ["md", "markdown"]
SCAN_EXCLUDE_DIRS = [".git", "_compiled", "node_modules", "__pycache__"]
PROMPT_SLUG_PATTERN = r"^slug:\s*pss\..*$"


class UploadPromptsError(RuntimeError):
    """Raised when upload-prompts cannot compile its file list."""


def discover_prompt_paths(cwd: Path | None = None) -> list[Path]:
    current_cwd = (Path.cwd() if cwd is None else Path(cwd)).expanduser().resolve()
    vault_root = validate_vault(current_cwd)

    records = rg_search(
        pattern=PROMPT_SLUG_PATTERN,
        root=vault_root,
        extensions=MARKDOWN_EXTENSIONS,
        exclude_dirs=SCAN_EXCLUDE_DIRS,
    )

    paths: list[Path] = []
    seen: set[Path] = set()

    for record in records:
        candidate = record.get("path")
        if not isinstance(candidate, Path):
            raise UploadPromptsError("scan returned a match without a path")

        normalized = candidate.expanduser().resolve()
        if normalized in seen:
            continue

        try:
            normalized.relative_to(vault_root)
        except ValueError:
            continue

        if not normalized.is_file():
            continue

        seen.add(normalized)
        paths.append(normalized)

    return sorted(paths)


def iter_prompt_jobs(cwd: Path | None = None) -> list[PandocJob]:
    paths = discover_prompt_paths(cwd)
    return [
        PandocJob(
            defaults=PANDOC_DEFAULTS,
            source_path=path,
        )
        for path in paths
    ]


def emit_prompt_records(cwd: Path | None = None) -> None:
    jobs = iter_prompt_jobs(cwd)

    for result in run_pandoc_jobs_serial(jobs):
        if result.stdout:
            sys.stdout.write(result.stdout)
            if not result.stdout.endswith("\n"):
                sys.stdout.write("\n")


def main() -> int:
    try:
        emit_prompt_records()
    except PandocError as exc:
        print(f"upload-prompts: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"upload-prompts: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())