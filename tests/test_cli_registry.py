from __future__ import annotations

import pytest

from workbench.cli import discover_commands
import workbench.cli.main as cli_main
import workbench.cli.writevault as writevault_module


def test_discovery_includes_expected_root_commands() -> None:
    commands = discover_commands()

    assert commands["commit"] == "workbench.cli.commit"
    assert commands["compile-batch"] == "workbench.cli.compile_batch"
    assert commands["writevault"] == "workbench.cli.writevault"
    assert commands["writestream"] == "workbench.cli.writestream"
    assert commands["stream"] == "workbench.cli.stream"
    assert commands["publish-control"] == "workbench.cli.publish_control"
    assert commands["publish-context"] == "workbench.cli.publish_context"
    assert commands["select-records"] == "workbench.cli.select_records"
    assert commands["compile-control"] == "workbench.cli.compile_control"
    assert commands["compile-registries"] == "workbench.cli.compile_registries"
    assert commands["compile-regex"] == "workbench.cli.compile_regex"
    assert commands["compile-assets"] == "workbench.cli.compile_assets"
    assert commands["find-duplicates"] == "workbench.cli.find_duplicates"


def test_discovery_excludes_removed_write_aliases() -> None:
    commands = discover_commands()

    assert "writenew" not in commands
    assert "writeback" not in commands
    assert "write-new" not in commands
    assert "write-back" not in commands
    assert "write-stream" not in commands
    assert "generate-slugs" not in commands


def test_dispatch_calls_writevault_module_main(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called: dict[str, list[str] | None] = {}

    def _fake_main(argv: list[str] | None = None) -> int:
        called["argv"] = argv
        return 0

    monkeypatch.setattr(writevault_module, "main", _fake_main)

    rc = cli_main.main(["writevault"])

    assert rc == 0
    assert called["argv"] == []


def test_help_shows_standardized_write_commands(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = cli_main.main(["--help"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "writevault" in out
    assert "writestream" in out
    assert "commit" in out
    assert "compile-batch" in out
    assert "compile-control" in out
    assert "publish-control" in out
    assert "select-records" in out
