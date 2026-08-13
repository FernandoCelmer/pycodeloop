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
];

class ChatViewProvider implements vscode.WebviewViewProvider {
  private webviewView: vscode.WebviewView | undefined;
  private client: RpcClient | undefined;
  private sessionKey = crypto.randomUUID();

  constructor(private readonly extensionUri: vscode.Uri) {}

  resolveWebviewView(webviewView: vscode.WebviewView): void {
    this.webviewView = webviewView;
    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [vscode.Uri.joinPath(this.extensionUri, "media")],
    };
    webviewView.webview.html = this.renderHtml(webviewView.webview);

    webviewView.webview.onDidReceiveMessage((message) => this.onWebviewMessage(message));
    webviewView.onDidDispose(() => this.disposeClient());

    this.ensureClient();
  }

  newSession(): void {
    this.sessionKey = crypto.randomUUID();
    this.post({ type: "sessionReset" });
  }

  private onWebviewMessage(message: any): void {
    switch (message.type) {
      case "sendPrompt":
        this.ensureClient();
        this.client?.request("chat/send", {
          prompt: message.prompt,
          sessionKey: this.sessionKey,
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
    }
  }

  private ensureClient(): void {
    if (this.client) {
      return;
    }

    const config = vscode.workspace.getConfiguration("pycodeloop");
    const command = config.get<string>("command", "pycodeloop");
    const args = ["serve"];

    const provider = config.get<string>("provider", "");
    if (provider) {
      args.push("--provider", provider);
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

    const cwd =
      vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? process.cwd();

    const client = new RpcClient(command, args, cwd);
    for (const method of FORWARDED_NOTIFICATIONS) {
      client.on(method, (params) => {
        this.post({ type: method.replace("chat/", ""), ...params });
      });
    }
    client.on("stderr", (text: string) => {
      this.post({ type: "stderr", text });
    });
    client.on("exit", ({ code }: { code: number | null }) => {
      this.post({ type: "processExit", code });
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
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource}; script-src 'nonce-${nonce}';" />
  <link rel="stylesheet" href="${styleUri}" />
  <title>CodeLoop</title>
</head>
<body>
  <div id="messages"></div>
  <div id="composer">
    <textarea id="prompt" placeholder="Ask CodeLoop…" rows="2"></textarea>
    <div id="composer-actions">
      <button id="send">Send</button>
      <button id="cancel" disabled>Cancel</button>
    </div>
  </div>
  <script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
  }
}

export function activate(context: vscode.ExtensionContext): void {
  const provider = new ChatViewProvider(context.extensionUri);

  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider("pycodeloop.chat", provider),
    vscode.commands.registerCommand("pycodeloop.openChat", () => {
      vscode.commands.executeCommand("pycodeloop.chat.focus");
    }),
    vscode.commands.registerCommand("pycodeloop.newSession", () => {
      provider.newSession();
    })
  );
}

export function deactivate(): void {}
