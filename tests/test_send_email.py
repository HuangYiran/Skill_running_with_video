import os
import pathlib
import tempfile
import unittest
from argparse import Namespace
from unittest import mock

from tools import send_email


class SendEmailRecipientConfigTest(unittest.TestCase):
    def test_resolve_recipient_prefers_cli_value(self) -> None:
        with mock.patch.dict(os.environ, {"TARGET_EMAIL": "env@example.com"}, clear=False):
            recipient = send_email.resolve_recipient("cli@example.com", "missing.txt")
        self.assertEqual(recipient, "cli@example.com")

    def test_resolve_recipient_uses_env_when_cli_missing(self) -> None:
        with mock.patch.dict(os.environ, {"TARGET_EMAIL": "env@example.com"}, clear=False):
            recipient = send_email.resolve_recipient(None, "missing.txt")
        self.assertEqual(recipient, "env@example.com")

    def test_resolve_recipient_reads_default_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            recipient_file = pathlib.Path(tmp_dir) / "target_email.txt"
            recipient_file.write_text("ihuangyiran@icloud.com\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {}, clear=True):
                recipient = send_email.resolve_recipient(None, str(recipient_file))
        self.assertEqual(recipient, "ihuangyiran@icloud.com")

    def test_resolve_recipient_returns_none_when_missing(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            recipient = send_email.resolve_recipient(None, "missing.txt")
        self.assertIsNone(recipient)


class SendEmailDeliveryTest(unittest.TestCase):
    def test_send_success_returns_true(self) -> None:
        fake_server = mock.MagicMock()
        fake_smtp = mock.MagicMock()
        fake_smtp.__enter__.return_value = fake_server

        with mock.patch("tools.send_email.smtplib.SMTP", return_value=fake_smtp):
            with mock.patch.dict(os.environ, {}, clear=True):
                msg = send_email.build_message(
                    "ihuangyiran@icloud.com", "subject", "body content"
                )
                ok, message = send_email.send(msg)

        self.assertTrue(ok)
        self.assertIn("Email sent successfully", message)
        fake_server.send_message.assert_called_once()

    def test_send_failure_writes_fallback_file(self) -> None:
        fallback_content = ""
        with tempfile.TemporaryDirectory() as tmp_dir:
            original_cwd = os.getcwd()
            os.chdir(tmp_dir)
            try:
                with mock.patch(
                    "tools.send_email.smtplib.SMTP",
                    side_effect=RuntimeError("smtp down"),
                ):
                    msg = send_email.build_message(
                        "ihuangyiran@icloud.com", "subject", "body content"
                    )
                    ok, message = send_email.send(msg)
            finally:
                os.chdir(original_cwd)

            fallback_files = list(
                (pathlib.Path(tmp_dir) / ".email_fallback").glob("email_*.txt")
            )
            self.assertEqual(len(fallback_files), 1)
            fallback_content = fallback_files[0].read_text(encoding="utf-8")

        self.assertFalse(ok)
        self.assertIn("SMTP failed", message)
        self.assertIn(
            "Please provide the following information to troubleshoot SMTP failure:",
            fallback_content,
        )


class SendEmailFailureDiagnosticsTest(unittest.TestCase):
    def test_build_smtp_info_request_contains_actionable_fields(self) -> None:
        diagnostic = send_email.build_smtp_info_request(
            exc=RuntimeError("smtp down"),
            host="smtp.example.com",
            port=587,
            use_tls=True,
            use_ssl=False,
            user="robot@example.com",
            has_password=True,
            from_addr="robot@example.com",
            to_addr="ihuangyiran@icloud.com",
        )
        self.assertIn("Full SMTP error output", diagnostic)
        self.assertIn("smtp://smtp.example.com:587", diagnostic)
        self.assertIn("SMTP_USE_TLS=True, SMTP_USE_SSL=False", diagnostic)
        self.assertIn("app password/OAuth requirement", diagnostic)


class SendEmailMainExitCodeTest(unittest.TestCase):
    def test_main_exits_nonzero_when_delivery_fails_by_default(self) -> None:
        args = Namespace(
            to=None,
            to_file="unused.txt",
            subject="subject",
            body_file="body.txt",
            allow_fallback_success=False,
        )

        with mock.patch("tools.send_email.parse_args", return_value=args):
            with mock.patch(
                "tools.send_email.resolve_recipient", return_value="ihuangyiran@icloud.com"
            ):
                with mock.patch("tools.send_email.load_body", return_value="body"):
                    with mock.patch(
                        "tools.send_email.send", return_value=(False, "SMTP failed")
                    ):
                        with self.assertRaises(SystemExit) as exc:
                            send_email.main()
        self.assertEqual(exc.exception.code, 1)

    def test_main_can_allow_fallback_success_explicitly(self) -> None:
        args = Namespace(
            to=None,
            to_file="unused.txt",
            subject="subject",
            body_file="body.txt",
            allow_fallback_success=True,
        )

        with mock.patch("tools.send_email.parse_args", return_value=args):
            with mock.patch(
                "tools.send_email.resolve_recipient", return_value="ihuangyiran@icloud.com"
            ):
                with mock.patch("tools.send_email.load_body", return_value="body"):
                    with mock.patch(
                        "tools.send_email.send", return_value=(False, "SMTP failed")
                    ):
                        with self.assertRaises(SystemExit) as exc:
                            send_email.main()
        self.assertEqual(exc.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
