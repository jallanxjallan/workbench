def _validate_required_directory(path: Path) -> None:
    if not path.exists() or not path.is_dir():
        raise CreateVaultError(f"Required directory is missing: {path}")


def _validate_preconditions() -> None:
    _validate_required_directory(OBSIDIAN_CORE_ROOT)
    _validate_required_directory(OBSIDIAN_CONTROL_ROOT)


def _iter_copyable_core_sources() -> list[Path]:
    sources: list[Path] = []
    for root_name in COPYABLE_CORE_ROOTS:
        root_path = OBSIDIAN_CORE_ROOT / root_name
        if not root_path.exists():
            continue
        sources.extend(sorted(root_path.rglob("*")))
    return sources


def _iter_managed_core_relative_files() -> tuple[str, ...]:
    files: list[str] = []
    for root_name in COPYABLE_CORE_ROOTS:
        root_path = OBSIDIAN_CORE_ROOT / root_name
        if not root_path.exists():
            continue
        for source in sorted(root_path.rglob("*")):
            if not source.is_file():
                continue
            relative = source.relative_to(OBSIDIAN_CORE_ROOT).as_posix()
            if relative in MANAGED_CORE_FILE_EXCLUDES:
                continue
            files.append(relative)
    return tuple(files)


def _resolve_vault_path(vault_path: str | None, *, cwd: Path | None = None) -> Path:
    if vault_path is not None:
        raw = str(vault_path).strip()
        if not raw:
            raise CreateVaultError("Vault path must be non-empty.")

        if "/" in raw or "\\" in raw:
            raise CreateVaultError(
                "Vault name must be a single folder name when passed as an argument."
            )
        return (STUDIO_ROOT / raw).resolve()

    current = (cwd or Path.cwd()).expanduser().resolve()
    studio_root = STUDIO_ROOT.expanduser().resolve()
    if current.parent == studio_root:
        return current
    raise CreateVaultError(
        "vault path is required unless current directory is a direct child of Studio"
    )


def is_vault(path: Path) -> bool:
    return (path / REGISTRY_JSON_FILENAME).is_file()


def _display_path(path: Path) -> str:
    home = Path.home().resolve()
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(home))
    except ValueError:
        return str(resolved)


def _encode_ulid(value: int) -> str:
    chars: list[str] = []
    remaining = value
    for _ in range(26):
        chars.append(ULID_ALPHABET[remaining & 0x1F])
        remaining >>= 5
    return "".join(reversed(chars))


def _generate_ulid() -> str:
    timestamp_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    if timestamp_ms >= (1 << 48):
        raise CreateVaultError("ULID timestamp overflow.")
    randomness = secrets.randbits(80)
    return _encode_ulid((timestamp_ms << 80) | randomness)


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _copy_core_without_overwrite(vault_path: Path) -> None:
    for source in _iter_copyable_core_sources():
        relative = source.relative_to(OBSIDIAN_CORE_ROOT)
        if relative.parts and relative.parts[0] == "_control":
            continue
        destination = vault_path / relative

        if source.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            continue

        if destination.exists() or destination.is_symlink():
            continue

        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def _install_core_if_missing(vault_path: Path) -> bool:
    obsidian_dir = vault_path / ".obsidian"
    if obsidian_dir.exists():
        if not obsidian_dir.is_dir():
            raise CreateVaultError(
                f"Unsafe path exists and is not a directory: {obsidian_dir}"
            )
        return False

    _copy_core_without_overwrite(vault_path)
    return True


def _sync_managed_core_files(vault_path: Path) -> int:
    synced = 0
    for relative in _iter_managed_core_relative_files():
        source = OBSIDIAN_CORE_ROOT / relative
        if not source.exists() or not source.is_file():
            raise CreateVaultError(f"Managed core file is missing: {source}")

        destination = vault_path / relative
        if destination.exists() and destination.is_dir():
            raise CreateVaultError(
                f"Unsafe path exists and is a directory: {destination}"
            )

        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and filecmp.cmp(source, destination, shallow=False):
            continue

        shutil.copy2(source, destination)
        synced += 1

    return synced


def _install_gitignore_if_missing(vault_path: Path) -> bool:
    gitignore_path = vault_path / ".gitignore"
    if gitignore_path.exists() and gitignore_path.is_dir():
        raise CreateVaultError(f"Unsafe path exists and is a directory: {gitignore_path}")

    if gitignore_path.exists():
        return False

    atomic_write_text(gitignore_path, VAULT_GITIGNORE_TEMPLATE)
    return True


def _ensure_control_symlink(vault_path: Path) -> bool:
    link_path = vault_path / "_control"
    control_target = OBSIDIAN_CONTROL_ROOT.resolve()

    if link_path.exists() or link_path.is_symlink():
        if not link_path.is_symlink():
            raise CreateVaultError(
                f"Unsafe existing _control path (not symlink): {link_path}"
            )

        resolved = link_path.resolve(strict=False)
        if resolved != control_target:
            raise CreateVaultError(
                f"Existing _control symlink points to {resolved}, expected {control_target}"
            )
        return False

    relative_target = os.path.relpath(control_target, start=link_path.parent.resolve())
    link_path.symlink_to(relative_target, target_is_directory=True)
    return True


def _normalize_mnemonic(value: str) -> str:
    return str(value).strip()


def _validate_mnemonic(mnemonic: str) -> str:
    normalized = _normalize_mnemonic(mnemonic)
    if not _MNEMONIC_RE.fullmatch(normalized):
        raise CreateVaultError(
            "Mnemonic must be 1-5 characters of lowercase letters and digits only."
        )
    return normalized


def _project_mnemonic(vault_path: Path) -> str:
    mnemonic = create_mnemonic(vault_path.name)
    mnemonic = _validate_mnemonic(mnemonic)
    if not mnemonic:
        raise CreateVaultError("Vault mnemonic is empty after normalization.")
    return mnemonic


def _find_mnemonic_collisions(
    mnemonic: str,
    *,
    studio_root: Path | None = None,
    exclude_vault: Path | None = None,
) -> tuple[Path, ...]:
    root = Path(studio_root or STUDIO_ROOT).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        return ()

    pattern = rf'"mnemonic"\s*:\s*"{re.escape(mnemonic)}"'
    matches: set[Path] = set()
    try:
        for match in rg_search(
            pattern=pattern,
            root=root,
            extensions=["json"],
        ):
            path = match.get("path")
            if not isinstance(path, Path) or path.name != REGISTRY_JSON_FILENAME:
                continue
            resolved = path.resolve()
            if exclude_vault is not None and resolved.parent == exclude_vault.resolve():
                continue
            matches.add(resolved)
    except RipgrepError as exc:
        raise CreateVaultError(str(exc)) from exc
    return tuple(sorted(matches))


def _ensure_mnemonic_available(
    mnemonic: str,
    *,
    studio_root: Path | None = None,
    exclude_vault: Path | None = None,
) -> str:
    validated = _validate_mnemonic(mnemonic)
    collisions = _find_mnemonic_collisions(
        validated,
        studio_root=studio_root,
        exclude_vault=exclude_vault,
    )
    if collisions:
        raise CreateVaultError(f'Mnemonic "{validated}" already exists.')
    return validated


def _is_interactive() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def _prompt_for_mnemonic(
    vault_path: Path,
    *,
    input_func: Callable[[str], str] = builtins.input,
    studio_root: Path | None = None,
) -> str:
    suggested = _project_mnemonic(vault_path)
    print(f"Suggested mnemonic: {suggested}")
    response = str(input_func("Accept? [Y/n] ")).strip().lower()
    if response in {"", "y", "yes"}:
        candidate = suggested
    else:
        candidate = ""

    while True:
        if candidate:
            try:
                return _ensure_mnemonic_available(
                    candidate,
                    studio_root=studio_root,
                    exclude_vault=vault_path,
                )
            except CreateVaultError as exc:
                print(str(exc))

        candidate = str(
            input_func(f"Enter alternate mnemonic (<=5 chars): ")
        ).strip()
        try:
            candidate = _validate_mnemonic(candidate)
        except CreateVaultError as exc:
            print(str(exc))
            candidate = ""


def _create_vault_registry(vault_path: Path, *, mnemonic: str) -> bool:
    registry_path = vault_path / REGISTRY_JSON_FILENAME
    if registry_path.exists():
        return False

    record = {
        "vault_id": _generate_ulid(),
        "created": _utc_now_iso(),
        "tool": "workbench",
        "version": 1,
        "mnemonic": mnemonic,
        "project_mnemonic": mnemonic,
    }
    atomic_write_text(registry_path, json.dumps(record, separators=(",", ":")) + "\n")
    return True


def _ensure_staging_dir(vault_path: Path) -> bool:
    staging_path = vault_path / "_staging"
    if staging_path.exists():
        if not staging_path.is_dir():
            raise CreateVaultError(f"Unsafe existing _staging path (not directory): {staging_path}")
        return False

    staging_path.mkdir(parents=True, exist_ok=False)
    return True


def create_vault(
    vault_path: str | None,
    *,
    cwd: Path | None = None,
    mnemonic: str | None = None,
) -> CreateVaultResult:
    _validate_preconditions()
    target = _resolve_vault_path(vault_path, cwd=cwd)

    if target.exists() and not target.is_dir():
        raise CreateVaultError(f"Vault path exists and is not a directory: {target}")

    existing_vault = target.exists() and is_vault(target)

    created_dir = False
    if not target.exists():
        target.mkdir(parents=True, exist_ok=False)
        created_dir = True

    try:
        selected_mnemonic = None
        if not existing_vault:
            selected_mnemonic = _project_mnemonic(target) if mnemonic is None else mnemonic
            selected_mnemonic = _ensure_mnemonic_available(
                selected_mnemonic,
                exclude_vault=target,
            )
        core_installed = _install_core_if_missing(target)
        managed_core_files_synced = _sync_managed_core_files(target)
        _install_gitignore_if_missing(target)
        control_link_created = _ensure_control_symlink(target)
        registry_created = (
            _create_vault_registry(target, mnemonic=selected_mnemonic)
            if selected_mnemonic is not None
            else False
        )
        _ensure_staging_dir(target)
    except Exception as exc:
        if created_dir and target.exists() and not is_vault(target):
            shutil.rmtree(target, ignore_errors=True)
        if isinstance(exc, CreateVaultError):
            raise
        raise CreateVaultError(f"Vault provisioning failed: {exc}") from exc

    status = (
        STATUS_CREATED
        if created_dir
        else (STATUS_ALREADY if existing_vault else STATUS_INITIALIZED)
    )
    return CreateVaultResult(
        vault_path=target,
        status=status,
        core_installed=core_installed,
        control_link_created=control_link_created,
        registry_created=registry_created,
        managed_core_files_synced=managed_core_files_synced,
    )

import yaml

from config.roots import (
    STUDIO_ROOT,
    OBSIDIAN_CORE_ROOT as DEFAULT_OBSIDIAN_CORE_ROOT,
    OBSIDIAN_CONTROL_ROOT as DEFAULT_OBSIDIAN_CONTROL_ROOT,
    OBSIDIAN_ROOT as DEFAULT_OBSIDIAN_ROOT,
)
from vault.identity import create_mnemonic
from scan.rg import RipgrepError, rg_search
from write.common import atomic_write_text

OBSIDIAN_ROOT = DEFAULT_OBSIDIAN_ROOT
OBSIDIAN_CORE_ROOT = DEFAULT_OBSIDIAN_CORE_ROOT
OBSIDIAN_CONTROL_ROOT = DEFAULT_OBSIDIAN_CONTROL_ROOT

ULID_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

STATUS_CREATED = "created"
STATUS_INITIALIZED = "initialized"
STATUS_ALREADY = "already_initialized"

REGISTRY_JSON_FILENAME = "_vault_registry.json"
_MNEMONIC_RE = re.compile(r"^[a-z0-9]{1,5}$")
_MAX_VAULT_MNEMONIC_LENGTH = 5
COPYABLE_CORE_ROOTS = (".obsidian",)
MANAGED_CORE_FILE_EXCLUDES = frozenset(
    {
        ".obsidian/workspace.json",
    }
)



class CreateVaultError(RuntimeError):
    pass


@dataclass(frozen=True)
class CreateVaultResult:
    vault_path: Path
    status: str
    core_installed: bool
    control_link_created: bool
    registry_created: bool
    managed_core_files_synced: int
