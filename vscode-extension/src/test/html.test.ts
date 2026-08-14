import assert from "node:assert/strict";
import { test } from "node:test";
import { renderChatHtml } from "../webview/html";

const OPTIONS = {
  cspSource: "vscode-webview://abc",
  scriptUri: "vscode-webview://abc/main.js",
  styleUri: "vscode-webview://abc/main.css",
  nonce: "test-nonce",
};

test("wires the script/style URIs and nonce into the markup", () => {
  const html = renderChatHtml(OPTIONS);
  assert.ok(html.includes('href="vscode-webview://abc/main.css"'));
  assert.ok(html.includes('src="vscode-webview://abc/main.js"'));
  assert.ok(html.includes("nonce-test-nonce"));
  assert.ok(html.includes("script-src 'nonce-test-nonce'"));
});

test("CSP restricts style-src and img-src to the given cspSource", () => {
  const html = renderChatHtml(OPTIONS);
  assert.ok(html.includes("style-src vscode-webview://abc;"));
  assert.ok(html.includes("img-src vscode-webview://abc data:;"));
});

test("includes the elements main.js expects to find by id", () => {
  const html = renderChatHtml(OPTIONS);
  for (const id of [
    "messages",
    "prompt",
    "send",
    "cancel",
    "menu-auto-approve-check",
    "menu-skills-check",
    "menu-mcp",
    "menu-api-key",
    "api-key",
    "api-key-save",
  ]) {
    assert.ok(html.includes(`id="${id}"`), `missing #${id}`);
  }
});
