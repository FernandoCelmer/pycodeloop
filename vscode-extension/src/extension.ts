import * as vscode from "vscode";
import * as crypto from "crypto";
import { RpcClient } from "./rpcClient";

const FORWARDED_NOTIFICATIONS = [
  "ready",
  "chat/textDelta",
  "chat/toolCall",
  "chat/toolResult",
  "chat/usage",
  "chat/context",
  "chat/retry",
  "chat/compactStart",
  "chat/compactEnd",
  "chat/confirmRequest",
  "chat/autoApproved",
];

const SESSION_KEY_STATE = "pycodeloop.sessionKey";

class ChatViewProvider implements vscode.WebviewViewProvider {
  private webviewView: vscode.WebviewView | undefined;
  private client: RpcClient | undefined;
  private sessionKey: string;

  constructor(
    private readonly extensionUri: vscode.Uri,
    private readonly state: vscode.Memento
  ) {
    this.sessionKey = state.get<string>(SESSION_KEY_STATE) ?? crypto.randomUUID();
  }

  resolveWebviewView(webviewView: vscode.WebviewView): void {
    this.webviewView = webviewView;
    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [vscode.Uri.joinPath(this.extensionUri, "media")],
    };
    webviewView.webview.html = this.renderHtml(webviewView.webview);

    webviewView.webview.onDidReceiveMessage((message) => this.onWebviewMessage(message));
    webviewView.onDidDispose(() => this.disposeClient());

    this.postSettings();
    if (this.isConfigured()) {
      this.post({ type: "connecting" });
      this.ensureClient();
    } else {
      this.post({ type: "needsSetup" });
    }
  }

  private isConfigured(): boolean {
    return !!vscode.workspace.getConfiguration("pycodeloop").get<string>("provider", "");
  }

  private postSettings(): void {
    const config = vscode.workspace.getConfiguration("pycodeloop");
    this.post({
      type: "settings",
      model: config.get<string>("model", ""),
      autoApprove: config.get<boolean>("autoApprove", false),
    });
  }

  newSession(): void {
    this.sessionKey = crypto.randomUUID();
    this.state.update(SESSION_KEY_STATE, this.sessionKey);
    this.post({ type: "sessionReset" });
  }

  async selectSession(): Promise<void> {
    this.ensureClient();
    if (!this.client) {
      return;
    }

    const response = await this.client.request("session/list");
    const sessions: Array<{
      key: string;
      updated_at?: number;
      message_count?: number;
      cwd?: string;
    }> = response.result?.sessions ?? [];

    if (!sessions.length) {
      vscode.window.showInformationMessage("No saved CodeLoop sessions yet.");
      return;
    }

    sessions.sort((a, b) => (b.updated_at ?? 0) - (a.updated_at ?? 0));
    const items = sessions.map((session) => ({
      label: (session.key === this.sessionKey ? "$(check) " : "") + session.key,
      description:
        (session.message_count ?? 0) + " messages" + (session.cwd ? " · " + session.cwd : ""),
      detail: session.updated_at
        ? new Date(session.updated_at * 1000).toLocaleString()
        : undefined,
      key: session.key,
    }));

    const picked = await vscode.window.showQuickPick(items, {
      title: "CodeLoop sessions",
      placeHolder: "Switch to a saved session",
    });
    if (!picked || picked.key === this.sessionKey) {
      return;
    }

    this.sessionKey = picked.key;
    await this.state.update(SESSION_KEY_STATE, this.sessionKey);
    this.post({ type: "sessionReset" });
    await this.loadHistory();
  }

  private async loadHistory(): Promise<void> {
    if (!this.client) {
      return;
    }
    const response = await this.client.request("session/load", { key: this.sessionKey });
    const messages = response.result?.messages ?? [];
    if (messages.length) {
      this.post({ type: "history", messages });
    }
  }

  reload(): void {
    this.disposeClient();
    this.post({ type: "connecting" });
    this.ensureClient();
  }

  async selectConfig(): Promise<void> {
    const picked = await vscode.window.showOpenDialog({
      canSelectMany: false,
      filters: { "Provider config": ["json"] },
      openLabel: "Use as provider config",
      defaultUri: vscode.workspace.workspaceFolders?.[0]?.uri,
    });
    const file = picked?.[0];
    if (!file) {
      return;
    }

    await vscode.workspace
      .getConfiguration("pycodeloop")
      .update("provider", file.fsPath, vscode.ConfigurationTarget.Workspace);

    this.post({ type: "configChanged", path: file.fsPath });
    this.reload();
  }

  async selectModel(current: string): Promise<void> {
    const model = await vscode.window.showInputBox({
      title: "CodeLoop model override",
      prompt: "Model name (empty clears the override and uses the provider's default)",
      value: current,
      placeHolder: "e.g. claude-sonnet-5, gpt-5",
    });
    if (model === undefined) {
      return;
    }

    await vscode.workspace
      .getConfiguration("pycodeloop")
      .update("model", model, vscode.ConfigurationTarget.Workspace);

    this.postSettings();
    this.reload();
  }

  async toggleAutoApprove(next: boolean): Promise<void> {
    await vscode.workspace
      .getConfiguration("pycodeloop")
      .update("autoApprove", next, vscode.ConfigurationTarget.Workspace);

    this.postSettings();
    this.reload();
  }

  private onWebviewMessage(message: any): void {
    switch (message.type) {
      case "sendPrompt":
        this.ensureClient();
        this.client?.request("chat/send", {
          prompt: message.prompt,
          sessionKey: this.sessionKey,
          images: message.images,
        }).then((response) => {
          if (response.error) {
            this.post({ type: "error", message: response.error.message });
          } else {
            this.post({ type: "done", text: response.result?.text ?? "" });
          }
        });
        break;
      case "cancel":
        this.client?.notify("chat/cancel");
        break;
      case "confirmResponse":
        this.client?.notify("chat/confirmResponse", {
          id: message.id,
          answer: message.answer,
        });
        break;
      case "newSession":
        this.newSession();
        break;
      case "selectConfig":
        this.selectConfig();
        break;
      case "selectSession":
        this.selectSession();
        break;
      case "selectModel":
        this.selectModel(message.current ?? "");
        break;
      case "toggleAutoApprove":
        this.toggleAutoApprove(!!message.next);
        break;
      case "reload":
        this.reload();
        break;
      case "openSettings":
        vscode.commands.executeCommand("workbench.action.openSettings", "pycodeloop");
        break;
    }
  }

  private resolveSetting(value: string): string {
    const cwd = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? process.cwd();
    return value.replace(/\$\{workspaceFolder\}/g, cwd);
  }

  private ensureClient(): void {
    if (this.client) {
      return;
    }

    const config = vscode.workspace.getConfiguration("pycodeloop");
    const command = this.resolveSetting(config.get<string>("command", "pycodeloop"));
    const args = ["serve"];

    const provider = config.get<string>("provider", "");
    if (provider) {
      args.push("--provider", this.resolveSetting(provider));
    }
    const model = config.get<string>("model", "");
    if (model) {
      args.push("--model", model);
    }
    const url = config.get<string>("url", "");
    if (url) {
      args.push("--url", url);
    }
    if (!config.get<boolean>("skills", true)) {
      args.push("--no-skills");
    }
    if (config.get<boolean>("autoApprove", false)) {
      args.push("--yes");
    }

    const cwd =
      vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? process.cwd();

    const client = new RpcClient(command, args, cwd);
    for (const method of FORWARDED_NOTIFICATIONS) {
      client.on(method, (params) => {
        this.post({ type: method.replace("chat/", ""), ...params });
      });
    }
    client.on("ready", () => {
      this.loadHistory();
    });
    client.on("stderr", (text: string) => {
      this.post({ type: "stderr", text });
    });
    client.on("exit", ({ code }: { code: number | null }) => {
      this.post({ type: "processExit", code });
      this.client = undefined;
    });
    client.on("spawnError", (error: Error) => {
      this.post({
        type: "connectionError",
        message: `Couldn't start "${command}" (${error.message}).`,
      });
      this.client = undefined;
    });

    this.client = client;
  }

  private disposeClient(): void {
    this.client?.dispose();
    this.client = undefined;
  }

  private post(message: any): void {
    this.webviewView?.webview.postMessage(message);
  }

  private renderHtml(webview: vscode.Webview): string {
    const scriptUri = webview.asWebviewUri(
      vscode.Uri.joinPath(this.extensionUri, "media", "main.js")
    );
    const styleUri = webview.asWebviewUri(
      vscode.Uri.joinPath(this.extensionUri, "media", "main.css")
    );
    const nonce = crypto.randomBytes(16).toString("hex");

    return /* html */ `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource}; script-src 'nonce-${nonce}'; img-src ${webview.cspSource} data:;" />
  <link rel="stylesheet" href="${styleUri}" />
  <title>CodeLoop</title>
</head>
<body>
  <div id="toolbar">
    <div id="status">
      <span id="status-dot" class="dot"></span>
      <span id="status-text">Not connected</span>
    </div>
    <div id="toolbar-actions">
      <button id="new-session" class="secondary" title="New session">New</button>
      <div id="menu-anchor">
        <button id="menu-toggle" class="secondary" title="Configure">⚙</button>
        <div id="menu" hidden>
          <button id="menu-sessions" class="menu-item">Sessions…</button>
          <button id="menu-provider" class="menu-item">Provider Config…</button>
          <button id="menu-model" class="menu-item">Model…</button>
          <button id="menu-auto-approve" class="menu-item">
            <span id="menu-auto-approve-check">☐</span> Auto-approve tools
          </button>
          <button id="menu-reload" class="menu-item">Reload Connection</button>
          <button id="menu-settings" class="menu-item">Open Settings</button>
        </div>
      </div>
    </div>
  </div>
  <div id="messages"></div>
  <div id="composer">
    <div id="attachments" hidden></div>
    <textarea id="prompt" placeholder="Ask CodeLoop… (paste a screenshot to attach it)" rows="2" disabled></textarea>
    <input type="file" id="attach-file" accept="image/*" multiple hidden />
    <div id="composer-actions">
      <button id="attach" class="secondary" title="Attach image" disabled>📎</button>
      <span id="context-pill"></span>
      <button id="send" disabled>Send</button>
      <button id="cancel" disabled>Cancel</button>
    </div>
  </div>
  <script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
  }
}

export function activate(context: vscode.ExtensionContext): void {
  const provider = new ChatViewProvider(context.extensionUri, context.workspaceState);

  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider("pycodeloop.chat", provider, {
      webviewOptions: { retainContextWhenHidden: true },
    }),
    vscode.commands.registerCommand("pycodeloop.openChat", () => {
      vscode.commands.executeCommand("pycodeloop.chat.focus");
    }),
    vscode.commands.registerCommand("pycodeloop.newSession", () => {
      provider.newSession();
    }),
    vscode.commands.registerCommand("pycodeloop.selectConfig", () => {
      provider.selectConfig();
    }),
    vscode.commands.registerCommand("pycodeloop.selectSession", () => {
      provider.selectSession();
    })
  );
}

export function deactivate(): void {}
