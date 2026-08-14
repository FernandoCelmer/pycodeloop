/** Every message the webview (main.js) can post to the extension host.
 * Keep this in sync with the `vscode.postMessage({...})` call sites in
 * media/main.js — there's no compiler on that side to catch drift, so
 * this union is the single place the full inbound contract is written
 * down and checked. */
export type WebviewMessage =
  | { type: "sendPrompt"; prompt: string; images?: string[] }
  | { type: "askAside"; id: string; prompt: string }
  | { type: "cancel" }
  | { type: "confirmResponse"; id: string; answer: boolean | string }
  | { type: "newSession" }
  | { type: "selectConfig" }
  | { type: "showProviders" }
  | { type: "connectProvider"; id: string }
  | { type: "changeProviderModel"; id: string }
  | { type: "disconnectProvider"; id: string }
  | { type: "selectSession" }
  | { type: "selectModel"; current?: string }
  | { type: "setApiKey"; value?: string; clear?: boolean }
  | { type: "toggleAutoApprove"; next: boolean }
  | { type: "toggleSkills"; next: boolean }
  | { type: "toggleDelegation"; next: boolean }
  | { type: "toggleMemory"; next: boolean }
  | { type: "manageMcpServers" }
  | { type: "reload" }
  | { type: "installCli" }
  | { type: "openSettings" };
