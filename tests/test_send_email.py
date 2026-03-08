import os
import pathlib
import tempfile
import unittest
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


if __name__ == "__main__":
    unittest.main()
