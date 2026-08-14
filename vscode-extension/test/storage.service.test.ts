import assert from "node:assert/strict";
import { test } from "node:test";
import { sortByRecency } from "../src/services/storage.service";

const SESSIONS = [
  { key: "old", updated_at: 100, message_count: 2, cwd: "/repo" },
  { key: "new", updated_at: 300, message_count: 5 },
  { key: "mid", updated_at: 200 },
];

test("sortByRecency orders newest-first without mutating the input", () => {
  const sorted = sortByRecency(SESSIONS);
  assert.deepEqual(
    sorted.map((s) => s.key),
    ["new", "mid", "old"]
  );
  assert.equal(SESSIONS[0].key, "old");
});
