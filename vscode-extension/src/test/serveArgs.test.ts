import assert from "node:assert/strict";
import { test } from "node:test";
import { buildServeArgs, ServeArgsOptions } from "../lib/serveArgs";

const identity = (value: string) => value;

function baseOptions(overrides: Partial<ServeArgsOptions> = {}): ServeArgsOptions {
  return {
    provider: "",
    model: "",
    url: "",
    skills: true,
    delegation: false,
    autoApprove: false,
    mcpServers: [],
    resolveSetting: identity,
    ...overrides,
  };
}

test("bare defaults produce just the serve command", () => {
  assert.deepEqual(buildServeArgs(baseOptions()), ["serve"]);
});

test("adds --provider, resolved through resolveSetting", () => {
  const args = buildServeArgs(
    baseOptions({
      provider: "${workspaceFolder}/provider.json",
      resolveSetting: (value) => value.replace("${workspaceFolder}", "/repo"),
    })
  );
  assert.deepEqual(args, ["serve", "--provider", "/repo/provider.json"]);
});

test("adds --model and --url when set", () => {
  const args = buildServeArgs(baseOptions({ model: "gpt-5", url: "http://localhost:1234" }));
  assert.deepEqual(args, ["serve", "--model", "gpt-5", "--url", "http://localhost:1234"]);
});

test("adds --no-skills only when skills is disabled", () => {
  assert.deepEqual(buildServeArgs(baseOptions({ skills: false })), ["serve", "--no-skills"]);
  assert.deepEqual(buildServeArgs(baseOptions({ skills: true })), ["serve"]);
});

test("adds --delegate only when delegation is enabled", () => {
  assert.deepEqual(buildServeArgs(baseOptions({ delegation: true })), ["serve", "--delegate"]);
  assert.deepEqual(buildServeArgs(baseOptions({ delegation: false })), ["serve"]);
});

test("adds --yes only when autoApprove is enabled", () => {
  assert.deepEqual(buildServeArgs(baseOptions({ autoApprove: true })), ["serve", "--yes"]);
});

test("adds one --mcp flag per configured server, in order", () => {
  const args = buildServeArgs(baseOptions({ mcpServers: ["server-a", "server-b"] }));
  assert.deepEqual(args, ["serve", "--mcp", "server-a", "--mcp", "server-b"]);
});

test("combines every flag together in a stable order", () => {
  const args = buildServeArgs(
    baseOptions({
      provider: "provider.json",
      model: "gpt-5",
      url: "http://x",
      skills: false,
      delegation: true,
      autoApprove: true,
      mcpServers: ["srv"],
    })
  );
  assert.deepEqual(args, [
    "serve",
    "--provider",
    "provider.json",
    "--model",
    "gpt-5",
    "--url",
    "http://x",
    "--no-skills",
    "--delegate",
    "--yes",
    "--mcp",
    "srv",
  ]);
});
