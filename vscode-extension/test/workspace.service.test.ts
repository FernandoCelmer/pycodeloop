import assert from "node:assert/strict";
import { test } from "node:test";
import { resolveWorkspacePath } from "../src/services/workspace.service";

test("leaves a value with no placeholder untouched", () => {
  assert.equal(resolveWorkspacePath("templates/anthropic.json", "/repo"), "templates/anthropic.json");
});

test("substitutes a single ${workspaceFolder}", () => {
  assert.equal(
    resolveWorkspacePath("${workspaceFolder}/.venv/bin/pycodeloop", "/repo"),
    "/repo/.venv/bin/pycodeloop"
  );
});

test("substitutes every occurrence, not just the first", () => {
  assert.equal(
    resolveWorkspacePath("${workspaceFolder}/a:${workspaceFolder}/b", "/repo"),
    "/repo/a:/repo/b"
  );
});
