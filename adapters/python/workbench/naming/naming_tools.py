from __future__ import annotations

from pathlib import Path

from workbench.naming import check_naming_conventions, generate_identifier_inventory


def check(root: str = ".") -> int:
    """Check kebab-case slug literals across repo files."""
    return check_naming_conventions.check(root)


def inventory(
    repos: str = ".",
    inventory_out: str = "identifier_inventory.json",
    rename_plan_out: str = "rename_plan.json",
) -> dict[str, str | int]:
    """Generate identifier inventory and rename plan JSON artifacts."""
    repo_list = [item for item in repos.split(",") if item.strip()]
    if not repo_list:
        repo_list = ["."]

    inv_path, plan_path, inventory_count, plan_count = generate_identifier_inventory.generate(
        repos=repo_list,
        inventory_out=inventory_out,
        rename_plan_out=rename_plan_out,
    )
    return {
        "inventory_entries": inventory_count,
        "rename_plan_entries": plan_count,
        "inventory_path": str(Path(inv_path)),
        "rename_plan_path": str(Path(plan_path)),
    }

