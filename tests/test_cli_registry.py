from __future__ import annotations

import pytest

from workbench.cli import discover_commands
import workbench.cli.main as cli_main
import workbench.cli.writenew as writenew_module


def test_discovery_includes_expected_root_commands() -> None:
    commands = discover_commands()

    assert commands["writenew"] == "workbench.cli.writenew"
    assert commands["writeback"] == "workbench.cli.writeback"
    assert commands["writestream"] == "workbench.cli.writestream"
    assert commands["stream"] == "workbench.cli.stream"
    assert commands["generate-slugs"] == "workbench.cli.generate_slugs"
    assert commands["compile-registries"] == "workbench.cli.compile_registries"
    assert commands["compile-regex"] == "workbench.cli.compile_regex"
    assert commands["compile-assets"] == "workbench.cli.compile_assets"
    assert commands["find-duplicates"] == "workbench.cli.find_duplicates"


def test_discovery_excludes_removed_write_aliases() -> None:
    commands = discover_commands()

    assert "write-new" not in commands
    assert "write-back" not in commands
    assert "write-stream" not in commands


def test_dispatch_calls_writenew_module_main(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called: dict[str, list[str] | None] = {}

    def _fake_main(argv: list[str] | None = None) -> int:
        called["argv"] = argv
        return 0

    monkeypatch.setattr(writenew_module, "main", _fake_main)

    rc = cli_main.main(["writenew"])

    assert rc == 0
    assert called["argv"] == []


def test_help_shows_standardized_write_commands(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = cli_main.main(["--help"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "writenew" in out
    assert "writeback" in out
    assert "writestream" in out
