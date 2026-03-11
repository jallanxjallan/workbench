from __future__ import annotations

import pytest

import workbench.cli.writeback as writeback_cli
import workbench.cli.writenew as writenew_cli


class _TTYStdin:
    def isatty(self) -> bool:
        return True


def test_writeback_main_requires_piped_stdin(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(writeback_cli.sys, "stdin", _TTYStdin())

    rc = writeback_cli.main([])
    err = capsys.readouterr().err

    assert rc == 1
    assert "usage: writeback" in err
    assert "expected NDJSON input from stdin" in err


def test_writeback_main_rejects_cli_args() -> None:
    with pytest.raises(SystemExit) as exc:
        writeback_cli.main(["--path", "."])

    assert exc.value.code == 2


def test_writenew_main_requires_piped_stdin(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(writenew_cli.sys, "stdin", _TTYStdin())

    rc = writenew_cli.main([])
    err = capsys.readouterr().err

    assert rc == 1
    assert "usage: writenew" in err
    assert "expected NDJSON input from stdin" in err
