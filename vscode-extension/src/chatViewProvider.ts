import * as vscode from "vscode";
import * as crypto from "crypto";
import * as cp from "child_process";
import { RpcClient } from "./rpcClient";
import { currentWorkspaceFolder, readSettings, updateSetting } from "./config/settings";
import { resolveWorkspacePath } from "./lib/resolveSetting";
import { buildServeArgs } from "./lib/serveArgs";
import { buildInstallCommand } from "./lib/installCommand";
import { toSessionPickItems } from "./lib/sessionList";
import { ADD_MCP_SERVER_LABEL, addServer, parseServerLabel, removeServer, toQuickPickLabels } from "./lib/mcpServerList";
import { renderChatHtml } from "./webview/html";

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

export class ChatViewProvider implements vscode.WebviewViewProvider {
  private webviewView: vscode.WebviewView | undefined;
  private client: RpcClient | undefined;
  private sessionKey: string;

  constructor(private readonly context: vscode.ExtensionContext) {
    this.sessionKey = context.workspaceState.get<string>(SESSION_KEY_STATE) ?? crypto.randomUUID();
  }

  private resolveSetting(value: string): string {
    return resolveWorkspacePath(value, currentWorkspaceFolder());
  }

  resolveWebviewView(webviewView: vscode.WebviewView): void {
    this.webviewView = webviewView;
    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [vscode.Uri.joinPath(this.context.extensionUri, "media")],
    };
    webviewView.webview.html = this.renderHtml(webviewView.webview);

    webviewView.webview.onDidReceiveMessage((message) => this.onWebviewMessage(message));
    webviewView.onDidDispose(() => this.disposeClient());

    this.postSettings();
    this.startConnection();
  }

  private async startConnection(): Promise<void> {
    if (!readSettings().provider) {
      this.post({ type: "needsSetup" });
      return;
    }
    if (!(await this.hasCli())) {
      this.post({ type: "cliMissing", command: this.resolveSetting(readSettings().command) });
      return;
    }
    this.post({ type: "connecting" });
    this.ensureClient();
  }

  private postSettings(): void {
    const settings = readSettings();
    this.post({
      type: "settings",
      model: settings.model,
      autoApprove: settings.autoApprove,
      skills: settings.skills,
      mcpServers: settings.mcpServers,
    });
  }

  newSession(): void {
    this.sessionKey = crypto.randomUUID();
    this.context.workspaceState.update(SESSION_KEY_STATE, this.sessionKey);
    this.post({ type: "sessionReset" });
  }

  async selectSession(): Promise<void> {
    this.ensureClient();
    if (!this.client) {
      return;
    }

    const response = await this.client.request("session/list");
    const sessions = response.result?.sessions ?? [];

    if (!sessions.length) {
      vscode.window.showInformationMessage("No saved CodeLoop sessions yet.");
      return;
    }

    const picked = await vscode.window.showQuickPick(toSessionPickItems(sessions, this.sessionKey), {
      title: "CodeLoop sessions",
      placeHolder: "Switch to a saved session",
    });
    if (!picked || picked.key === this.sessionKey) {
      return;
    }

    this.sessionKey = picked.key;
    await this.context.workspaceState.update(SESSION_KEY_STATE, this.sessionKey);
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
    this.startConnection();
  }

  private async hasCli(): Promise<boolean> {
    const command = this.resolveSetting(readSettings().command);
    return new Promise((resolve) => {
      cp.exec(`"${command}" --help`, (error) => resolve(!error));
    });
  }

  async installCli(): Promise<void> {
    const installCmd = buildInstallCommand(process.platform);
    await vscode.window.withProgress(
      { location: vscode.ProgressLocation.Notification, title: "Installing CodeLoop CLI…" },
      () =>
        new Promise<void>((resolve) => {
          cp.exec(installCmd, { timeout: 180000 }, (error, _stdout, stderr) => {
            if (error) {
              vscode.window
                .showErrorMessage(
                  `Couldn't install pycodeloop automatically: ${stderr || error.message}. ` +
                    `Run this yourself: ${installCmd}`,
                  "Copy command"
                )
                .then((choice) => {
                  if (choice === "Copy command") {
                    vscode.env.clipboard.writeText(installCmd);
                  }
                });
            } else {
              vscode.window.showInformationMessage("CodeLoop CLI installed.");
              this.reload();
            }
            resolve();
          });
        })
    );
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

    await updateSetting("provider", file.fsPath);
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

    await updateSetting("model", model);
    this.postSettings();
    this.reload();
  }

  async toggleAutoApprove(next: boolean): Promise<void> {
    await updateSetting("autoApprove", next);
    this.postSettings();
    this.reload();
  }

  async toggleSkills(next: boolean): Promise<void> {
    await updateSetting("skills", next);
    this.postSettings();
    this.reload();
  }

  async manageMcpServers(): Promise<void> {
    const servers = readSettings().mcpServers;

    const picked = await vscode.window.showQuickPick(toQuickPickLabels(servers), {
      title: "CodeLoop MCP servers",
      placeHolder: servers.length ? "Pick a server to remove, or add a new one" : "No MCP servers configured yet",
    });
    if (!picked) {
      return;
    }

    if (picked === ADD_MCP_SERVER_LABEL) {
      const command = await vscode.window.showInputBox({
        title: "MCP server launch command",
        prompt: "e.g. npx -y @modelcontextprotocol/server-filesystem .",
        placeHolder: "npx -y @modelcontextprotocol/server-filesystem .",
        ignoreFocusOut: true,
      });
      if (!command) {
        return;
      }
      await updateSetting("mcpServers", addServer(servers, command));
    } else {
      const removed = parseServerLabel(picked);
      if (!removed) {
        return;
      }
      const confirm = await vscode.window.showQuickPick(["Remove", "Cancel"], {
        title: `Remove "${removed}"?`,
      });
      if (confirm !== "Remove") {
        return;
      }
      await updateSetting("mcpServers", removeServer(servers, removed));
    }

    this.postSettings();
    this.reload();
  }

  private onWebviewMessage(message: any): void {
    switch (message.type) {
      case "sendPrompt":
        this.ensureClient();
        this.client
          ?.request("chat/send", {
            prompt: message.prompt,
            sessionKey: this.sessionKey,
            images: message.images,
          })
          .then((response) => {
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
        this.client?.notify("chat/confirmResponse", { id: message.id, answer: message.answer });
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
      case "toggleSkills":
        this.toggleSkills(!!message.next);
        break;
      case "manageMcpServers":
        this.manageMcpServers();
        break;
      case "reload":
        this.reload();
        break;
      case "installCli":
        this.installCli();
        break;
      case "openSettings":
        vscode.commands.executeCommand("workbench.action.openSettings", "pycodeloop");
        break;
    }
  }

  private ensureClient(): void {
    if (this.client) {
      return;
    }

    const settings = readSettings();
    const command = this.resolveSetting(settings.command);
    const args = buildServeArgs({
      provider: settings.provider,
      model: settings.model,
      url: settings.url,
      skills: settings.skills,
      autoApprove: settings.autoApprove,
      mcpServers: settings.mcpServers,
      resolveSetting: (value) => this.resolveSetting(value),
    });

    const client = new RpcClient(command, args, currentWorkspaceFolder());
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
    client.on("spawnError", (error: NodeJS.ErrnoException) => {
      if (error.code === "ENOENT") {
        this.post({ type: "cliMissing", command });
      } else {
        this.post({ type: "connectionError", message: `Couldn't start "${command}" (${error.message}).` });
      }
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
    const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(this.context.extensionUri, "media", "main.js"));
    const styleUri = webview.asWebviewUri(vscode.Uri.joinPath(this.context.extensionUri, "media", "main.css"));

    return renderChatHtml({
      cspSource: webview.cspSource,
      scriptUri: scriptUri.toString(),
      styleUri: styleUri.toString(),
      nonce: crypto.randomBytes(16).toString("hex"),
    });
  }
}
