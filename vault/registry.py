def read_vault_registry(vault_root: Path) -> dict[str, object]:
    registry_path = vault_root / VAULT_REGISTRY_FILENAME
    if not registry_path.exists():
        raise VaultRuntimeError(f"vault registry is missing: {registry_path}")
    try:
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise VaultRuntimeError(f"vault registry is invalid JSON: {registry_path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise VaultRuntimeError(f"vault registry must be a JSON object: {registry_path}")
    return payload