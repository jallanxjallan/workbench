from __future__ import annotations

import pytest

import workbench.write.writeback as writeback_module
import workbench.write.writenew as writenew_module


class _TTYStdin:
    def isatty(self) -> bool:
        return True


def test_writeback_main_requires_piped_stdin(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(writeback_module.sys, "stdin", _TTYStdin())

    rc = writeback_module.main([])
    err = capsys.readouterr().err

    assert rc == 1
    assert "usage: write-back" in err
    assert "expected NDJSON input from stdin" in err


def test_writeback_main_rejects_cli_args() -> None:
    with pytest.raises(SystemExit) as exc:
        writeback_module.main(["--path", "."])

    assert exc.value.code == 2


def test_writenew_main_requires_piped_stdin(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(writenew_module.sys, "stdin", _TTYStdin())

    rc = writenew_module.main(["--schema", "passage", "--path", "."])
    err = capsys.readouterr().err

    assert rc == 1
    assert "usage: write-new" in err
    assert "expected NDJSON input from stdin" in err
