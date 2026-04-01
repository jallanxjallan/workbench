from __future__ import annotations

import contextlib
import io
import types
import unittest
from unittest.mock import patch


class CliWrapperTests(unittest.TestCase):
    def _run_main(self, module_name: str, argv: list[str] | None = None) -> tuple[int, str, str]:
        module = __import__(module_name, fromlist=["main"])
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = module.main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_confirm_upload_catches_typed_domain_error(self) -> None:
        from cli import confirm_upload
        from upload.confirm import ConfirmUploadError

        with patch.object(confirm_upload, "confirm_upload", side_effect=ConfirmUploadError("bad trailer")):
            code, _, stderr = self._run_main("cli.confirm_upload", [])

        self.assertEqual(code, 1)
        self.assertEqual(stderr, "confirm-upload: bad trailer\n")

    def test_create_vault_catches_typed_domain_error(self) -> None:
        from cli import create_vault
        from vault.create import CreateVaultError

        with patch.object(create_vault, "create_vault", side_effect=CreateVaultError("missing core")):
            code, _, stderr = self._run_main("cli.create_vault", [])

        self.assertEqual(code, 1)
        self.assertEqual(stderr, "missing core\n")

    def test_slug_filepaths_catches_typed_domain_error(self) -> None:
        from cli import slug_filepaths
        from upload.dispatch import BatchDispatchError

        with patch.object(slug_filepaths, "dispatch_batch", side_effect=BatchDispatchError("bad manifest")):
            code, _, stderr = self._run_main("cli.slug_filepaths", ["selection.json"])

        self.assertEqual(code, 1)
        self.assertEqual(stderr, "slug_filepaths: bad manifest\n")

    def test_upload_package_catches_typed_domain_error(self) -> None:
        from cli import upload_package
        from upload.package import UploadPackageError

        with patch.object(upload_package, "upload_package", side_effect=UploadPackageError("bad package")):
            code, _, stderr = self._run_main("cli.upload_package", ["package.yml"])

        self.assertEqual(code, 1)
        self.assertEqual(stderr, "upload-package: bad package\n")

    def test_upload_profiles_catches_typed_domain_error(self) -> None:
        from cli import upload_profiles
        from upload.profiles import UploadProfilesError

        with patch.object(upload_profiles, "upload_profiles", side_effect=UploadProfilesError("bad profiles")):
            code, _, stderr = self._run_main("cli.upload_profiles", [])

        self.assertEqual(code, 1)
        self.assertEqual(stderr, "upload-profiles: bad profiles\n")

    def test_writeback_catches_current_domain_error(self) -> None:
        from cli import writeback
        from intake.writeback import WriteBackError

        with patch.object(writeback, "_has_piped_stdin", return_value=True), patch.object(
            writeback,
            "prepare_writeback_stream",
            side_effect=WriteBackError("dirty target"),
        ):
            code, _, stderr = self._run_main("cli.writeback", [])

        self.assertEqual(code, 1)
        self.assertEqual(stderr, "ERROR: dirty target\n")

    def test_writenew_catches_current_domain_error(self) -> None:
        from cli import writenew
        from intake.writenew import WriteNewError

        with patch.object(writenew, "_has_piped_stdin", return_value=True), patch.object(
            writenew,
            "prepare_writenew_stream",
            side_effect=WriteNewError("bad target"),
        ):
            code, _, stderr = self._run_main("cli.writenew", [])

        self.assertEqual(code, 1)
        self.assertEqual(stderr, "ERROR: bad target\n")

    def test_slug_to_path_catches_current_domain_error(self) -> None:
        from cli import slug_to_path
        from intake.slug_to_path import SlugToPathError

        with patch.object(slug_to_path, "_has_piped_stdin", return_value=True), patch.object(
            slug_to_path,
            "stream_slug_to_path_records",
            side_effect=SlugToPathError("missing slug"),
        ):
            code, _, stderr = self._run_main("cli.slug_to_path", [])

        self.assertEqual(code, 1)
        self.assertEqual(stderr, "ERROR: missing slug\n")

    def test_main_dispatches_newly_registered_wrapper_commands(self) -> None:
        fake_typer = types.SimpleNamespace()

        class FakeExit(Exception):
            def __init__(self, code: int = 0) -> None:
                self.code = code

        class FakeTyperApp:
            def __init__(self, **_: object) -> None:
                self.commands: dict[str, object] = {}

            def command(self, name: str, context_settings: dict[str, object] | None = None):
                def decorator(func):
                    self.commands[name] = func
                    return func

                return decorator

            def __call__(self, *, args: list[str], prog_name: str) -> None:
                command_name = args[0]
                ctx = types.SimpleNamespace(args=args[1:])
                self.commands[command_name](ctx)

        fake_typer.Typer = FakeTyperApp
        fake_typer.Context = object
        fake_typer.Exit = FakeExit

        with patch.dict("sys.modules", {"typer": fake_typer}):
            import importlib

            main = importlib.import_module("cli.main")
            importlib.reload(main)

            with patch.object(main, "_dispatch", return_value=0) as dispatch:
                self.assertEqual(main.main(["upload-package", "pkg.yml"]), 0)
                dispatch.assert_called_with("upload-package", ["pkg.yml"])

            with patch.object(main, "_dispatch", return_value=0) as dispatch:
                self.assertEqual(main.main(["upload-profiles"]), 0)
                dispatch.assert_called_with("upload-profiles", [])


if __name__ == "__main__":
    unittest.main()
