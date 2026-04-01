from __future__ import annotations

import json
from pathlib import Path

from transport.pandoc import PandocError, PandocJob, run_pandoc_jobs_serial


class MarkdownHelperError(RuntimeError):
    pass


PANDOC_DEFAULTS_BY_PREFIX: dict[str, str] = {
    "pss": "upload_prompts",
    "img": "upload_prompts",
    "scn": "upload_prompts",
    "web": "upload_prompts",
    "gbl": "upload_instructions",
    "cxt": "upload_instructions",
    "spc": "upload_instructions",
}


def build_payload(path: Path, *, slug: str) -> dict:
    defaults = pandoc_defaults_for_slug(slug)

    try:
        results = list(
            run_pandoc_jobs_serial(
                [
                    PandocJob(
                        defaults=defaults,
                        source_path=path,
                    )
                ]
            )
        )
    except PandocError as exc:
        raise MarkdownHelperError(f"pandoc failed for {path}: {exc}") from exc

    if len(results) != 1:
        raise MarkdownHelperError(f"unexpected pandoc result count for {path}")

    lines = [line for line in results[0].stdout.splitlines() if line.strip()]
    if len(lines) != 1:
        raise MarkdownHelperError(f"pandoc must emit exactly one JSON line for {path}")

    try:
        payload = json.loads(lines[0])
    except json.JSONDecodeError as exc:
        raise MarkdownHelperError(f"pandoc emitted invalid JSON for {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise MarkdownHelperError(f"pandoc emitted non-object payload for {path}")

    return payload


def pandoc_defaults_for_slug(slug: str) -> str:
    prefix = slug.split(".", 1)[0]

    try:
        return PANDOC_DEFAULTS_BY_PREFIX[prefix]
    except KeyError as exc:
        raise MarkdownHelperError(
            f"no pandoc defaults configured for slug prefix: {prefix}"
        ) from exc