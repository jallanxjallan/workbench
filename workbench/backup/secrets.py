"""Create encrypted secrets backups for Dropbox using age."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

DEFAULT_INCLUDE_FILE = "~/.config/workbench/secrets_include.txt"
DEFAULT_BACKUP_ROOT = "~/Dropbox/secure-backups"
DEFAULT_KEY_FILE = "~/.config/age/keys.txt"
DEFAULT_KEEP = 30
MANIFEST_NAME = ".secrets_backup_manifest.json"
TIMESTAMP_FORMAT = "%Y-%m-%dT%H-%M"


@dataclass(frozen=True)
class IncludeEntry:
    path: Path
    optional: bool


@dataclass(frozen=True)
class BackupConfig:
    include_file: Path
    backup_root: Path
    key_file: Path
    recipient: str | None
    keep: int
    age_bin: str
    dry_run: bool
    force: bool


def parse_args(argv: list[str] | None = None) -> BackupConfig:
    parser = argparse.ArgumentParser(description="Create encrypted secrets backups with age.")
    parser.add_argument(
        "--include-file",
        default=DEFAULT_INCLUDE_FILE,
        help="List of files/directories to back up (default: %(default)s).",
    )
    parser.add_argument(
        "--backup-root",
        default=DEFAULT_BACKUP_ROOT,
        help="Dropbox destination for encrypted backups (default: %(default)s).",
    )
    parser.add_argument(
        "--key-file",
        default=DEFAULT_KEY_FILE,
        help="age private key file used to derive recipient when --recipient is omitted.",
    )
    parser.add_argument(
        "--recipient",
        default=None,
        help="Explicit age recipient public key (age1...). Overrides --key-file derivation.",
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=DEFAULT_KEEP,
        help="Number of most recent encrypted backups to keep (default: %(default)s).",
    )
    parser.add_argument(
        "--age-bin",
        default="age",
        help="age binary to execute (default: %(default)s).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be backed up without creating an archive.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Create a backup even when tracked secrets are unchanged.",
    )
    ns = parser.parse_args(argv)

    if ns.keep < 1:
        parser.error("--keep must be at least 1")

    return BackupConfig(
        include_file=Path(ns.include_file).expanduser(),
        backup_root=Path(ns.backup_root).expanduser(),
        key_file=Path(ns.key_file).expanduser(),
        recipient=ns.recipient,
        keep=ns.keep,
        age_bin=ns.age_bin,
        dry_run=ns.dry_run,
        force=ns.force,
    )


def resolve_entry_path(raw: str, home: Path) -> Path:
    p = Path(raw).expanduser()
    if p.is_absolute():
        return p
    return (home / p).resolve()


def parse_include_file(include_file: Path, home: Path) -> list[IncludeEntry]:
    if not include_file.is_file():
        raise RuntimeError(f"Include file not found: {include_file}")

    entries: list[IncludeEntry] = []
    seen: set[Path] = set()

    for raw_line in include_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        optional = line.startswith("?")
        if optional:
            line = line[1:].strip()

        if not line:
            continue

        path = resolve_entry_path(line, home)
        if path in seen:
            continue
        seen.add(path)
        entries.append(IncludeEntry(path=path, optional=optional))

    if not entries:
        raise RuntimeError(f"No backup entries found in include file: {include_file}")
    return entries


def validate_entries(entries: list[IncludeEntry], key_file: Path) -> list[Path]:
    existing: list[Path] = []
    missing_required: list[Path] = []
    key_resolved = key_file.resolve(strict=False)

    for entry in entries:
        path = entry.path
        if not path.exists():
            if entry.optional:
                continue
            missing_required.append(path)
            continue

        resolved = path.resolve()
        if resolved == key_resolved:
            raise RuntimeError(f"Refusing to back up the age private key file: {resolved}")
        if resolved.is_dir() and key_resolved.is_relative_to(resolved):
            raise RuntimeError(
                f"Refusing to back up directory containing age private key: {resolved}"
            )
        existing.append(resolved)

    if missing_required:
        missing_text = "\n".join(f"  - {path}" for path in missing_required)
        raise RuntimeError(f"Required paths are missing:\n{missing_text}")

    if not existing:
        raise RuntimeError("All include-file paths are missing or optional; nothing to back up.")
    return existing


def resolve_recipient(recipient: str | None, key_file: Path) -> str:
    if recipient:
        return recipient

    if not key_file.is_file():
        raise RuntimeError(
            f"age key file not found: {key_file}. Provide --recipient or create keys with age-keygen."
        )

    for line in key_file.read_text(encoding="utf-8").splitlines():
        cleaned = line.strip()
        if cleaned.startswith("#"):
            cleaned = cleaned[1:].strip()
        if cleaned.lower().startswith("public key:"):
            value = cleaned.split(":", 1)[1].strip()
            if value:
                return value

    raise RuntimeError(f"No 'public key:' entry found in age key file: {key_file}")


def ensure_age_available(age_bin: str) -> None:
    if shutil.which(age_bin):
        return
    raise RuntimeError(
        f"age binary not found: {age_bin}. Install age first (https://github.com/FiloSottile/age)."
    )


def file_signature(path: Path) -> str:
    stat = path.stat()
    return f"{stat.st_size}:{stat.st_mtime_ns}"


def collect_state(paths: list[Path], home: Path) -> dict[str, str]:
    state: dict[str, str] = {}
    visited_dirs: set[str] = set()

    for root_path in sorted(paths):
        if root_path.is_file():
            state[archive_key(root_path, home)] = file_signature(root_path)
            continue

        for current_root, dirnames, filenames in os.walk(root_path, topdown=True, followlinks=True):
            real_root = os.path.realpath(current_root)
            if real_root in visited_dirs:
                dirnames[:] = []
                continue
            visited_dirs.add(real_root)

            root = Path(current_root)
            for filename in filenames:
                file_path = root / filename
                if not file_path.is_file():
                    continue
                state[archive_key(file_path, home)] = file_signature(file_path)

    return state


def archive_key(path: Path, home: Path) -> str:
    try:
        return str(path.relative_to(home))
    except ValueError:
        return f"_external/{str(path).lstrip('/')}"


def read_manifest(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def write_manifest(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as tmp:
        json.dump(payload, tmp, indent=2, sort_keys=True)
        tmp.write("\n")
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def create_archive_path(backup_root: Path, now: datetime) -> Path:
    stamp = now.strftime(TIMESTAMP_FORMAT)
    base = f"secrets-{stamp}"
    archive = backup_root / f"{base}.tar.age"
    suffix = 1
    while archive.exists():
        archive = backup_root / f"{base}-{suffix:02d}.tar.age"
        suffix += 1
    return archive


def encrypt_tar_stream(
    paths: list[Path], archive_path: Path, recipient: str, age_bin: str, home: Path
) -> None:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(
        [age_bin, "-r", recipient, "-o", str(archive_path), "-"],
        stdin=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        assert proc.stdin is not None
        with tarfile.open(fileobj=proc.stdin, mode="w|", dereference=True) as tar:
            for path in paths:
                tar.add(path, arcname=archive_key(path, home))
    except Exception:
        proc.kill()
        proc.wait()
        archive_path.unlink(missing_ok=True)
        raise
    finally:
        if proc.stdin:
            proc.stdin.close()

    stderr = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
    rc = proc.wait()
    if rc != 0:
        archive_path.unlink(missing_ok=True)
        raise RuntimeError(f"age encryption failed: {stderr.strip() or f'exit code {rc}'}")


def enforce_retention(backup_root: Path, keep: int) -> None:
    archives = sorted(backup_root.glob("secrets-*.tar.age"))
    overflow = len(archives) - keep
    if overflow <= 0:
        return
    for old in archives[:overflow]:
        old.unlink()


def count_changes(previous: dict[str, str], current: dict[str, str]) -> int:
    changed = 0
    for key in set(previous) | set(current):
        if previous.get(key) != current.get(key):
            changed += 1
    return changed


def run(config: BackupConfig) -> int:
    home = Path.home().resolve()
    entries = parse_include_file(config.include_file, home)
    paths = validate_entries(entries, config.key_file)
    state = collect_state(paths, home)

    if not state:
        raise RuntimeError("No files found in selected paths; nothing to back up.")

    manifest_path = config.backup_root / MANIFEST_NAME
    manifest = read_manifest(manifest_path)
    previous = manifest.get("tracked_files")
    if not isinstance(previous, dict):
        previous = {}
    changed = count_changes(previous, state)

    if changed == 0 and not config.force:
        print("SKIP secrets: no changes")
        return 0

    now = datetime.now()
    archive_path = create_archive_path(config.backup_root, now)

    if config.dry_run:
        print(f"DRY-RUN secrets -> {archive_path}")
        print(f"DRY-RUN tracked files: {len(state)}")
        return 0

    ensure_age_available(config.age_bin)
    recipient = resolve_recipient(config.recipient, config.key_file)
    encrypt_tar_stream(paths, archive_path, recipient, config.age_bin, home)
    enforce_retention(config.backup_root, config.keep)
    write_manifest(
        manifest_path,
        {
            "last_successful_backup": now.strftime(TIMESTAMP_FORMAT),
            "last_archive": archive_path.name,
            "keep": config.keep,
            "tracked_file_count": len(state),
            "changed_file_count": changed,
            "tracked_files": state,
        },
    )
    print(f"BACKUP secrets -> {archive_path} ({changed} changed)")
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return run(parse_args(argv))
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL secrets {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
