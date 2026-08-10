"""Test read_clipboard_image_base64()"""

import sys
import unittest
from unittest import mock

from pycodeloop.core.clipboard import read_clipboard_image_base64


class TestReadClipboardImage(unittest.TestCase):
    def test_returns_none_off_macos(self):
        with mock.patch.object(sys, "platform", "linux"):
            self.assertIsNone(read_clipboard_image_base64())

    def test_returns_none_when_clipboard_has_no_image(self):
        fake_result = mock.Mock(returncode=0, stdout="NO_IMAGE")
        with (
            mock.patch.object(sys, "platform", "darwin"),
            mock.patch("subprocess.run", return_value=fake_result),
        ):
            self.assertIsNone(read_clipboard_image_base64())

    def test_returns_none_when_osascript_fails(self):
        fake_result = mock.Mock(returncode=1, stdout="")
        with (
            mock.patch.object(sys, "platform", "darwin"),
            mock.patch("subprocess.run", return_value=fake_result),
        ):
            self.assertIsNone(read_clipboard_image_base64())

    def test_returns_base64_of_the_written_file_on_success(self):
        fake_result = mock.Mock(returncode=0, stdout="OK")

        def fake_run(args, **kwargs):
            # The temp path is the last token before the closing quote
            # in the AppleScript source passed via `-e`.
            script = args[2]
            path = script.split('POSIX file "')[1].split('"')[0]
            with open(path, "wb") as f:
                f.write(b"fake-png-bytes")
            return fake_result

        with (
            mock.patch.object(sys, "platform", "darwin"),
            mock.patch("subprocess.run", side_effect=fake_run),
        ):
            result = read_clipboard_image_base64()

        self.assertEqual(result, "ZmFrZS1wbmctYnl0ZXM=")


if __name__ == "__main__":
    unittest.main()
