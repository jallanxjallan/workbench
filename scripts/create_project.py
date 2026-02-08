#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

REQUIRED_PLUGINS = ("dataview", "quickadd", "templater-obsidian")

APP_JSON = {"promptDelete": False}
CORE_PLUGINS_JSON = {
    "file-explorer": True,
    "global-search": True,
    "switcher": True,
    "graph": True,
    "backlink": True,
    "canvas": True,
    "outgoing-link": True,
    "tag-pane": True,
    "page-preview": True,
    "daily-notes": True,
    "templates": True,
    "note-composer": True,
    "command-palette": True,
    "editor-status": True,
    "bookmarks": True,
    "outline": True,
    "word-count": True,
    "file-recovery": True,
}
COMMUNITY_PLUGINS_JSON = ["dataview", "quickadd", "templater-obsidian"]
TEMPLATES_JSON = {"folder": "_common/templates"}

DATAVIEW_DATA_JSON = {
    "renderNullAs": "\\-",
    "taskCompletionTracking": False,
    "taskCompletionUseEmojiShorthand": False,
    "taskCompletionText": "completion",
    "taskCompletionDateFormat": "yyyy-MM-dd",
    "recursiveSubTaskCompletion": False,
    "warnOnEmptyResult": True,
    "refreshEnabled": True,
    "refreshInterval": 2500,
    "defaultDateFormat": "dd MMM yyyy",
    "defaultDateTimeFormat": "h:mm a - dd MMM yyyy",
    "maxRecursiveRenderDepth": 4,
    "tableIdColumnName": "File",
    "tableGroupColumnName": "Group",
    "showResultCount": True,
    "allowHtml": True,
    "inlineQueryPrefix": "=",
    "inlineJsQueryPrefix": "$=",
    "inlineQueriesInCodeblocks": True,
    "enableInlineDataview": True,
    "enableDataviewJs": True,
    "enableInlineDataviewJs": True,
    "prettyRenderInlineFields": True,
    "prettyRenderInlineFieldsInLivePreview": True,
    "dataviewJsKeyword": "dataviewjs",
}

TEMPLATER_DATA_JSON = {
    "command_timeout": 5,
    "templates_folder": "_common/templates",
    "templates_pairs": [["", ""]],
    "trigger_on_file_creation": False,
    "auto_jump_to_cursor": False,
    "enable_system_commands": False,
    "shell_path": "",
    "user_scripts_folder": "_common/scripts",
    "enable_folder_templates": True,
    "folder_templates": [{"folder": "", "template": ""}],
    "enable_file_templates": False,
    "file_templates": [{"regex": ".*", "template": ""}],
    "syntax_highlighting": True,
    "syntax_highlighting_mobile": False,
    "enabled_templates_hotkeys": [],
    "startup_templates": [""],
    "intellisense_render": 1,
    "user_script_commands": True,
}

QUICKADD_DATA_JSON = {
    "choices": [],
    "inputPrompt": "single-line",
    "devMode": False,
    "templateFolderPath": "_common/templates",
    "announceUpdates": True,
    "globalVariables": {},
    "onePageInputEnabled": False,
    "disableOnlineFeatures": True,
    "enableRibbonIcon": False,
    "showCaptureNotification": True,
    "enableTemplatePropertyTypes": False,
}


def die(message: str) -> None:
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(1)


def sanitize_mnemonic(raw: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", raw.lower())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def ensure_symlink(link_path: Path, target: str | Path) -> None:
    target_text = str(target)
    if link_path.is_symlink():
        existing = os.readlink(link_path)
        if existing != target_text:
            die(f"symlink exists with different target: {link_path} -> {existing}")
        return
    if link_path.exists():
        die(f"path exists and is not a symlink: {link_path}")
    link_path.symlink_to(target_text)


def seed_plugins(plugins_root: Path, source_plugins_root: Path) -> int:
    missing = []
    ensured = 0

    for plugin in REQUIRED_PLUGINS:
        src = source_plugins_root / plugin
        dst = plugins_root / plugin
        if not src.is_dir():
            missing.append(plugin)
            continue
        ensured += 1
        if not dst.exists():
            shutil.copytree(src, dst)

    if missing:
        die(
            "missing required Obsidian plugin dependencies in "
            f"{source_plugins_root}: {', '.join(missing)}"
        )

    return ensured


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="create_project.py")
    parser.add_argument("mnemonic")
    parser.add_argument(
        "--project-root",
        default=os.getcwd(),
        help="Project root to initialize (defaults to current working directory).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    mnemonic = sanitize_mnemonic(args.mnemonic)
    if not mnemonic:
        die(f"invalid project mnemonic '{args.mnemonic}'")

    home_dir = Path.home()
    project_root = Path(args.project_root).expanduser().resolve()
    project_vault_name = mnemonic
    project_vault = project_root / project_vault_name
    workbench_root = Path(os.environ.get("WORKBENCH_ROOT", str(home_dir / "Workbench"))).expanduser()
    workbench_common = Path(
        os.environ.get("WORKBENCH_COMMON", str(workbench_root / "obsidian-common"))
    ).expanduser()
    workbench_obsidian = Path(
        os.environ.get("WORKBENCH_OBSIDIAN", str(workbench_root / "obsidian"))
    ).expanduser()
    workbench_plugins = workbench_obsidian / "plugins"
    studio_active_root = Path(
        os.environ.get("STUDIO_ACTIVE_ROOT", str(home_dir / "Studio/writing/active"))
    ).expanduser()
    studio_project_path = studio_active_root / mnemonic
    plugins_root = project_vault / ".obsidian/plugins"

    if not workbench_common.is_dir():
        die(f"shared obsidian-common not found: {workbench_common}")
    if not workbench_plugins.is_dir():
        die(f"workbench obsidian plugins directory not found: {workbench_plugins}")
    if project_vault.exists():
        die(f"vault directory already exists: {project_vault}")
    if not studio_project_path.exists():
        die(f"studio project path not found: {studio_project_path}")

    (project_vault / ".obsidian").mkdir(parents=True, exist_ok=True)
    common_rel = os.path.relpath(workbench_common, project_vault)
    project_rel = os.path.relpath(studio_project_path, project_vault)

    ensure_symlink(project_vault / "_project", project_rel)
    ensure_symlink(project_vault / "_common", common_rel)

    write_text(
        project_root / ".env.local",
        (
            "# Project scope (generated by create_project)\n"
            f'PROJECT_MNEMONIC="{mnemonic}"\n'
            f'PROJECT_NAME="{mnemonic}"\n'
            f'PROJECT_ROOT="{project_root}"\n'
            f'PROJECT_VAULT="{project_vault}"\n'
            f'PROJECT_VAULT_NAME="{project_vault_name}"\n'
            f'PROJECT_STUDIO="{studio_project_path}"\n'
            'DEVHOOK_SCOPE="project"\n'
        ),
    )

    write_text(
        project_root / ".envrc",
        (
            "dotenv_if_exists .env.local\n"
            "PATH_add bin\n"
            "PATH_add scripts\n\n"
            "watch_file .env.local\n\n"
            'echo "[direnv] $(basename "$PWD") project scope loaded"\n'
        ),
    )

    write_json(project_vault / ".obsidian/app.json", APP_JSON)
    write_json(project_vault / ".obsidian/core-plugins.json", CORE_PLUGINS_JSON)
    write_json(project_vault / ".obsidian/community-plugins.json", COMMUNITY_PLUGINS_JSON)
    write_json(project_vault / ".obsidian/templates.json", TEMPLATES_JSON)

    copied_plugins = seed_plugins(plugins_root, workbench_plugins)

    (plugins_root / "dataview").mkdir(parents=True, exist_ok=True)
    (plugins_root / "quickadd").mkdir(parents=True, exist_ok=True)
    (plugins_root / "templater-obsidian").mkdir(parents=True, exist_ok=True)

    write_json(plugins_root / "dataview/data.json", DATAVIEW_DATA_JSON)
    write_json(plugins_root / "quickadd/data.json", QUICKADD_DATA_JSON)
    write_json(plugins_root / "templater-obsidian/data.json", TEMPLATER_DATA_JSON)

    if copied_plugins < len(REQUIRED_PLUGINS):
        print(
            f"WARNING: Plugin binaries not fully seeded ({copied_plugins}/{len(REQUIRED_PLUGINS)}).",
            file=sys.stderr,
        )
        print(
            "Open Obsidian -> Community Plugins and install missing plugins listed in "
            ".obsidian/community-plugins.json.",
            file=sys.stderr,
        )

    print("✅ Project initialised")
    print(f"   Mnemonic: {mnemonic}")
    print(f"   Root:     {project_root}")
    print(f"   Vault:    {project_vault}")
    print(f"   Links:    _project -> {project_rel}, _common -> {common_rel}")
    print(f"   Studio:   {studio_project_path}")
    print(f"   Devhook:  {project_root}/.env.local (+ .envrc)")
    print("   Plugins:  dataview, quickadd, templater-obsidian")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
