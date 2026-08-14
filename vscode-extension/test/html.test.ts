import assert from "node:assert/strict";
import { test } from "node:test";
import { renderChatHtml } from "../src/vscode/webview/html";

const OPTIONS = {
  cspSource: "vscode-webview://abc",
  scriptUris: ["vscode-webview://abc/dom.js", "vscode-webview://abc/app.js"],
  styleUri: "vscode-webview://abc/main.css",
  nonce: "test-nonce",
};

test("wires the script/style URIs and nonce into the markup", () => {
  const html = renderChatHtml(OPTIONS);
  assert.ok(html.includes('href="vscode-webview://abc/main.css"'));
  assert.ok(html.includes('src="vscode-webview://abc/dom.js"'));
  assert.ok(html.includes('src="vscode-webview://abc/app.js"'));
  assert.ok(html.includes("nonce-test-nonce"));
  assert.ok(html.includes("script-src 'nonce-test-nonce'"));
});

test("keeps script tags in the given order so shared globals are defined before use", () => {
  const html = renderChatHtml(OPTIONS);
  assert.ok(html.indexOf("dom.js") < html.indexOf("app.js"));
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
  ]) {
    assert.ok(html.includes(`id="${id}"`), `missing #${id}`);
  }
});
