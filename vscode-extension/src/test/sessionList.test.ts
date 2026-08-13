import assert from "node:assert/strict";
import { test } from "node:test";
import { sortByRecency, toSessionPickItems } from "../lib/sessionList";

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

test("toSessionPickItems marks the active session with a checkmark", () => {
  const items = toSessionPickItems(SESSIONS, "mid");
  const active = items.find((item) => item.key === "mid");
  assert.ok(active?.label.startsWith("$(check) "));

  const inactive = items.find((item) => item.key === "new");
  assert.ok(!inactive?.label.startsWith("$(check) "));
});

test("toSessionPickItems formats the description with message count and cwd", () => {
  const items = toSessionPickItems(SESSIONS, "");
  const old = items.find((item) => item.key === "old");
  assert.equal(old?.description, "2 messages · /repo");

  const withoutCwd = items.find((item) => item.key === "new");
  assert.equal(withoutCwd?.description, "5 messages");
});

test("toSessionPickItems defaults message count to 0 when missing", () => {
  const items = toSessionPickItems([{ key: "bare" }], "");
  assert.equal(items[0].description, "0 messages");
  assert.equal(items[0].detail, undefined);
});
