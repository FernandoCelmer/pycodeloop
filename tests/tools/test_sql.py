"""Test SqlSchemaTool and SqlQueryTool"""

import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine, text

from pycodeloop.tools.sql import SqlQueryTool, SqlSchemaTool


class SqlToolTestCase(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.db_path = Path(self._tmpdir.name) / "test.db"
        self.url = f"sqlite:///{self.db_path}"

        engine = create_engine(self.url)
        with engine.begin() as conn:
            conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)"))
            conn.execute(text("INSERT INTO users (id, name) VALUES (1, 'ada')"))
            conn.execute(text("INSERT INTO users (id, name) VALUES (2, 'grace')"))
        engine.dispose()


class TestSqlSchemaTool(SqlToolTestCase):
    def test_lists_tables(self):
        result = SqlSchemaTool().run(url=self.url)

        self.assertIn("users", result.output)
        self.assertFalse(result.is_error)

    def test_lists_columns_for_a_table(self):
        result = SqlSchemaTool().run(url=self.url, table="users")

        self.assertIn("id", result.output)
        self.assertIn("name", result.output)

    def test_reports_missing_table(self):
        result = SqlSchemaTool().run(url=self.url, table="nope")

        self.assertTrue(result.is_error)

    def test_reports_bad_url(self):
        result = SqlSchemaTool().run(url="not-a-real-url://nope")

        self.assertTrue(result.is_error)


class TestSqlQueryTool(SqlToolTestCase):
    def test_runs_a_select(self):
        result = SqlQueryTool().run(url=self.url, query="SELECT id, name FROM users ORDER BY id")

        self.assertFalse(result.is_error)
        self.assertIn("ada", result.output)
        self.assertIn("grace", result.output)

    def test_rejects_insert(self):
        result = SqlQueryTool().run(
            url=self.url, query="INSERT INTO users (id, name) VALUES (3, 'x')"
        )

        self.assertTrue(result.is_error)
        self.assertIn("read-only", result.output)

    def test_rejects_delete(self):
        result = SqlQueryTool().run(url=self.url, query="DELETE FROM users")

        self.assertTrue(result.is_error)

    def test_rejects_drop_table(self):
        result = SqlQueryTool().run(url=self.url, query="DROP TABLE users")

        self.assertTrue(result.is_error)

    def test_rejects_stacked_statements(self):
        result = SqlQueryTool().run(
            url=self.url, query="SELECT 1; DROP TABLE users;"
        )

        self.assertTrue(result.is_error)
        self.assertIn("single", result.output)

    def test_caps_rows_at_max_rows(self):
        engine = create_engine(self.url)
        with engine.begin() as conn:
            for i in range(3, 13):
                conn.execute(text("INSERT INTO users (id, name) VALUES (:i, :n)"), {"i": i, "n": f"u{i}"})
        engine.dispose()

        result = SqlQueryTool().run(url=self.url, query="SELECT * FROM users", max_rows=5)

        self.assertIn("capped at 5", result.output)

    def test_reports_invalid_sql(self):
        result = SqlQueryTool().run(url=self.url, query="SELECT * FROM nope")

        self.assertTrue(result.is_error)


if __name__ == "__main__":
    unittest.main()
