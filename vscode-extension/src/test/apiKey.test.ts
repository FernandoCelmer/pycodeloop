import assert from "node:assert/strict";
import { test } from "node:test";
import { API_KEY_ENV, spawnEnvForApiKey } from "../lib/apiKey";

test("spawnEnvForApiKey omits env when the key is missing or blank", () => {
  assert.equal(spawnEnvForApiKey(undefined), undefined);
  assert.equal(spawnEnvForApiKey(""), undefined);
  assert.equal(spawnEnvForApiKey("   "), undefined);
});

test("spawnEnvForApiKey injects PYCODELOOP_API_KEY without putting it on argv", () => {
  assert.deepEqual(spawnEnvForApiKey("sk-test"), { [API_KEY_ENV]: "sk-test" });
  assert.deepEqual(spawnEnvForApiKey("  sk-test  "), { [API_KEY_ENV]: "sk-test" });
});
