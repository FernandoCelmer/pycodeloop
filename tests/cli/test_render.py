"""Test render.py's pure formatting helpers"""

import io
import unittest

from rich.console import Console

from aiflow.cli.render import (
    TurnBuffer,
    format_args,
    format_tokens,
    format_tool_call,
    render_preview,
    tool_icon,
)


class TestToolIcon(unittest.TestCase):
    def test_known_tool_has_specific_icon(self):
        self.assertEqual(tool_icon("bash"), "💻")

    def test_unknown_tool_falls_back(self):
        self.assertEqual(tool_icon("something_new"), "🔧")


class TestFormatTokens(unittest.TestCase):
    def test_small_count_is_plain(self):
        self.assertEqual(format_tokens(42), "42")

    def test_large_count_uses_k_suffix(self):
        self.assertEqual(format_tokens(12345), "12.3k")


class TestFormatArgs(unittest.TestCase):
    def test_single_arg_shows_bare_value(self):
        self.assertEqual(format_args({"path": "a.py"}), "a.py")

    def test_multiple_args_show_key_value_pairs(self):
        result = format_args({"path": "a.py", "offset": 1})
        self.assertEqual(result, "path=a.py, offset=1")

    def test_truncates_long_values(self):
        result = format_args({"text": "x" * 200})
        self.assertTrue(result.endswith("…"))
        self.assertLessEqual(len(result), 101)


class TestFormatToolCall(unittest.TestCase):
    def test_bash_shows_dollar_prompt_with_real_command(self):
        result = format_tool_call("bash", {"command": "echo hi"})
        self.assertIn("$", result)
        self.assertIn("echo hi", result)

    def test_bash_escapes_rich_markup_in_command(self):
        result = format_tool_call("bash", {"command": "echo [bold]hi"})
        # escaped so Rich renders it literally instead of parsing it as a
        # style tag — the backslash-escaped form, not the bare markup
        self.assertIn("\\[bold]hi", result)

    def test_other_tool_shows_name_and_args(self):
        result = format_tool_call("read_file", {"path": "a.py"})
        self.assertIn("read_file", result)
        self.assertIn("a.py", result)


class TestRenderPreview(unittest.TestCase):
    def test_diff_plus_minus_and_dollar_lines_get_distinct_styles(self):
        preview = "+added\n-removed\n$ ls\ncontext\n"
        text = render_preview(preview)

        styles = {str(span.style) for span in text.spans}
        # Three distinct non-dim styles: bold white (+ and $) and grey50 (-)
        self.assertIn("bold white", styles)
        self.assertIn("grey50", styles)


class TestTurnBuffer(unittest.TestCase):
    def test_flush_prints_buffered_text_and_clears_it(self):
        console = Console(file=io.StringIO(), width=60)
        buffer = TurnBuffer(console)
        buffer.delta("hello ")
        buffer.delta("world")

        buffer.flush()

        self.assertEqual(buffer._text, "")

    def test_flush_with_no_text_prints_nothing(self):
        out = io.StringIO()
        console = Console(file=out, width=60)
        buffer = TurnBuffer(console)

        buffer.flush()

        self.assertEqual(out.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
