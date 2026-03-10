from __future__ import annotations

import pytest

import workbench.cli.write_back as write_back_cli
import workbench.cli.write_new as write_new_cli


class _TTYStdin:
    def isatty(self) -> bool:
        return True


def test_writeback_main_requires_piped_stdin(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(write_back_cli.sys, "stdin", _TTYStdin())

    rc = write_back_cli.main([])
    err = capsys.readouterr().err

    assert rc == 1
    assert "usage: write-back" in err
    assert "expected NDJSON input from stdin" in err


def test_writeback_main_rejects_cli_args() -> None:
    with pytest.raises(SystemExit) as exc:
        write_back_cli.main(["--path", "."])

    assert exc.value.code == 2


def test_writenew_main_requires_piped_stdin(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(write_new_cli.sys, "stdin", _TTYStdin())

    rc = write_new_cli.main(["--schema", "passage", "--path", "."])
    err = capsys.readouterr().err

    assert rc == 1
    assert "usage: write-new" in err
    assert "expected NDJSON input from stdin" in err
