from __future__ import annotations

import pytest

import workbench.cli.writevault as writevault_cli


class _TTYStdin:
    def isatty(self) -> bool:
        return True


def test_writevault_main_requires_piped_stdin(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(writevault_cli.sys, "stdin", _TTYStdin())

    rc = writevault_cli.main([])
    err = capsys.readouterr().err

    assert rc == 1
    assert "usage: writevault" in err
    assert "expected NDJSON input from stdin" in err


def test_writevault_main_rejects_unknown_cli_args() -> None:
    with pytest.raises(SystemExit) as exc:
        writevault_cli.main(["--path", "."])

    assert exc.value.code == 2
