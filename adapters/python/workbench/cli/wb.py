from __future__ import annotations

import fire

from workbench.backups import backup_tools
from workbench.naming import naming_tools


class NamingCLI:
    def check(self, root: str = ".") -> int:
        return naming_tools.check(root=root)

    def inventory(
        self,
        repos: str = ".",
        inventory_out: str = "identifier_inventory.json",
        rename_plan_out: str = "rename_plan.json",
    ) -> dict[str, str | int]:
        return naming_tools.inventory(
            repos=repos,
            inventory_out=inventory_out,
            rename_plan_out=rename_plan_out,
        )


class BackupsCLI:
    def list(
        self,
        backup_root: str = backup_tools.DEFAULT_BACKUP_ROOT,
        project: str | None = None,
    ) -> list[str]:
        return backup_tools.list(backup_root=backup_root, project=project)


class WorkbenchCLI:
    def naming(self):
        return NamingCLI()

    def backups(self):
        return BackupsCLI()


def main() -> None:
    fire.Fire(WorkbenchCLI())
