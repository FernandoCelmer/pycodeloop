import assert from "node:assert/strict";
import { test } from "node:test";
import { API_KEY_ENV, providerAuthFromJson, spawnEnvForApiKey } from "../lib/apiKey";

test("spawnEnvForApiKey omits env when the key is missing or blank", () => {
  assert.equal(spawnEnvForApiKey(undefined), undefined);
  assert.equal(spawnEnvForApiKey(""), undefined);
  assert.equal(spawnEnvForApiKey("   "), undefined);
});

test("spawnEnvForApiKey injects PYCODELOOP_API_KEY and the template env name", () => {
  assert.deepEqual(spawnEnvForApiKey("sk-test"), { [API_KEY_ENV]: "sk-test" });
  assert.deepEqual(spawnEnvForApiKey("  sk-test  ", ["ANTHROPIC_API_KEY"]), {
    [API_KEY_ENV]: "sk-test",
    ANTHROPIC_API_KEY: "sk-test",
  });
});

test("providerAuthFromJson reads api_key_env and auth_header", () => {
  assert.deepEqual(
    providerAuthFromJson(
      '{"url":"http://x","api_key_env":"ANTHROPIC_API_KEY","auth_header":"x-api-key"}'
    ),
    { apiKeyEnv: "ANTHROPIC_API_KEY", authHeader: "x-api-key" }
  );
  assert.deepEqual(providerAuthFromJson("{"), {});
  assert.deepEqual(providerAuthFromJson('{"url":"http://x"}'), {
    apiKeyEnv: undefined,
    authHeader: undefined,
  });
});
