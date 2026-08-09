"""Test TodoTool"""

import unittest

from codeloop.core.tools.todo import TodoTool


class TestTodoTool(unittest.TestCase):
    def test_add_then_list(self):
        tool = TodoTool()

        tool.run(action="add", text="write tests")
        result = tool.run(action="list")

        self.assertIn("write tests", result.output)
        self.assertIn("[ ]", result.output)

    def test_complete_marks_done(self):
        tool = TodoTool()
        tool.run(action="add", text="write tests")

        result = tool.run(action="complete", item_id=1)

        self.assertIn("[x]", result.output)

    def test_state_persists_across_calls_on_same_instance(self):
        tool = TodoTool()
        tool.run(action="add", text="a")
        tool.run(action="add", text="b")

        result = tool.run(action="list")

        self.assertIn("a", result.output)
        self.assertIn("b", result.output)

    def test_clear_empties_list(self):
        tool = TodoTool()
        tool.run(action="add", text="a")

        result = tool.run(action="clear")

        self.assertEqual(result.output, "(empty)")

    def test_complete_unknown_id_is_error(self):
        tool = TodoTool()

        result = tool.run(action="complete", item_id=99)

        self.assertTrue(result.is_error)


if __name__ == "__main__":
    unittest.main()
