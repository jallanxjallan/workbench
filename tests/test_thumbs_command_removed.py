from __future__ import annotations

import pytest

import workbench.cli.main as cli_main
from workbench.cli import discover_commands


def test_thumbs_command_is_removed_from_discovery() -> None:
    commands = discover_commands()
    assert "generate-thumbs" not in commands


def test_cli_rejects_removed_thumbs_command(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = cli_main.main(["generate-thumbs", "--help"])
    err = capsys.readouterr().err

    assert rc == 2
    assert "No such command" in err
