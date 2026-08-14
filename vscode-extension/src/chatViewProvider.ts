import * as vscode from "vscode";
import * as crypto from "crypto";
import * as cp from "child_process";
import * as fs from "fs";
import * as path from "path";
import { RpcClient } from "./rpcClient";
import { currentWorkspaceFolder, readSettings, updateSetting } from "./config/settings";
import { resolveWorkspacePath } from "./lib/resolveSetting";
import { buildServeArgs } from "./lib/serveArgs";
import { buildInstallCommand } from "./lib/installCommand";
import { API_KEY_SECRET, providerAuthFromJson, providerKeySecret, spawnEnvForApiKey } from "./lib/apiKey";
import { toSessionPickItems } from "./lib/sessionList";
import { PROVIDER_CATALOG, findProviderDef } from "./lib/providerCatalog";
import { ADD_MCP_SERVER_LABEL, addServer, parseServerLabel, removeServer, toQuickPickLabels } from "./lib/mcpServerList";
import { renderChatHtml } from "./webview/html";
import { WebviewMessage } from "./webview/messages";

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
    await this.ensureClient();
  }

  private async postSettings(): Promise<void> {
    const settings = readSettings();
    const apiKey = await this.context.secrets.get(API_KEY_SECRET);
    const auth = this.readProviderAuth(settings.provider);
    this.post({
      type: "settings",
      model: settings.model,
      autoApprove: settings.autoApprove,
      skills: settings.skills,
      delegation: settings.delegation,
      memory: settings.memory,
      mcpServers: settings.mcpServers,
      hasApiKey: Boolean(apiKey),
      apiKeyEnv: auth.apiKeyEnv,
      authHeader: auth.authHeader,
      providerFile: auth.providerFile,
    });
  }

  newSession(): void {
    this.sessionKey = crypto.randomUUID();
    this.context.workspaceState.update(SESSION_KEY_STATE, this.sessionKey);
    this.post({ type: "sessionReset" });
  }

  async selectSession(): Promise<void> {
    await this.ensureClient();
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
    await updateSetting("url", "");
    this.post({ type: "configChanged", path: file.fsPath });
    await this.postSettings();
    this.reload();
  }

  private providersDir(): string {
    return vscode.Uri.joinPath(this.context.extensionUri, "providers").fsPath;
  }

  private providerModelKey(id: string): string {
    return `pycodeloop.providerModel.${id}`;
  }

  private storedModelFor(def: (typeof PROVIDER_CATALOG)[number]): string {
    return this.context.globalState.get<string>(this.providerModelKey(def.id)) ?? def.defaultModel;
  }

  private async pickModelFor(def: (typeof PROVIDER_CATALOG)[number]): Promise<string | undefined> {
    const current = this.storedModelFor(def);
    const modelItems = [...def.models.map((m) => ({ label: m })), { label: "Custom…" }];
    const modelPick = await vscode.window.showQuickPick(modelItems, {
      title: `${def.label} model`,
      placeHolder: `Current: ${current}`,
    });
    if (!modelPick) {
      return undefined;
    }
    if (modelPick.label !== "Custom…") {
      return modelPick.label;
    }
    return (
      (await vscode.window.showInputBox({
        title: `${def.label} model`,
        value: current,
        ignoreFocusOut: true,
      })) ?? undefined
    );
  }

  private activeProviderId(providerSetting: string): string {
    if (!providerSetting) {
      return "";
    }
    const resolved = this.resolveSetting(providerSetting);
    if (resolved === "generic") {
      return "generic";
    }
    const dir = this.providersDir();
    for (const def of PROVIDER_CATALOG) {
      if (resolved === path.join(dir, def.file)) {
        return def.id;
      }
    }
    return "custom";
  }

  async openProviderGallery(): Promise<void> {
    await vscode.commands.executeCommand("pycodeloop.chat.focus");
    await this.showProviderGallery();
  }

  async showProviderGallery(): Promise<void> {
    const settings = readSettings();
    const activeId = this.activeProviderId(settings.provider);
    const activeHasKey = Boolean(await this.context.secrets.get(API_KEY_SECRET));

    const items = await Promise.all(
      PROVIDER_CATALOG.map(async (def) => {
        const isActive = def.id === activeId;
        const hasKey = def.local
          ? false
          : isActive
            ? activeHasKey
            : Boolean(await this.context.secrets.get(providerKeySecret(def.id)));
        return {
          id: def.id,
          label: def.label,
          description: def.description,
          model: isActive && settings.model ? settings.model : this.storedModelFor(def),
          local: def.local,
          active: isActive,
          connected: hasKey,
        };
      })
    );

    this.post({ type: "providers", items, activeId });
  }

  async connectProvider(id: string): Promise<void> {
    if (id === "custom") {
      await this.selectConfig();
      await this.showProviderGallery();
      return;
    }

    if (id === "generic") {
      const current = readSettings();
      const url = await vscode.window.showInputBox({
        title: "Generic provider URL",
        prompt: "OpenAI-compatible chat/completions endpoint",
        value: current.provider === "generic" ? current.url : "",
        placeHolder: "https://api.example.com/v1/chat/completions",
        ignoreFocusOut: true,
      });
      if (!url) {
        return;
      }
      await updateSetting("provider", "generic");
      await updateSetting("url", url);
      await this.selectModel(readSettings().model);
      await this.showProviderGallery();
      return;
    }

    const def = findProviderDef(id);
    if (!def) {
      return;
    }

    const model = await this.pickModelFor(def);
    if (!model) {
      return;
    }
    await this.context.globalState.update(this.providerModelKey(def.id), model);

    if (!def.local) {
      const remembered = await this.context.secrets.get(providerKeySecret(def.id));
      if (remembered) {
        await this.context.secrets.store(API_KEY_SECRET, remembered);
      } else {
        const key = await vscode.window.showInputBox({
          title: `${def.label} API key`,
          prompt: `Stored securely, sent as ${def.file === "anthropic.json" ? "x-api-key" : "Authorization: Bearer …"}`,
          password: true,
          ignoreFocusOut: true,
        });
        const trimmed = key?.trim();
        if (trimmed) {
          await this.context.secrets.store(API_KEY_SECRET, trimmed);
          await this.context.secrets.store(providerKeySecret(def.id), trimmed);
        }
      }
    }

    const providerPath = path.join(this.providersDir(), def.file);
    await updateSetting("provider", providerPath);
    await updateSetting("url", "");
    await updateSetting("model", model);

    this.post({ type: "configChanged", path: providerPath });
    await this.postSettings();
    await this.showProviderGallery();
    this.reload();
  }

  async changeProviderModel(id: string): Promise<void> {
    const def = findProviderDef(id);
    if (!def) {
      return;
    }
    const model = await this.pickModelFor(def);
    if (!model) {
      return;
    }
    await this.context.globalState.update(this.providerModelKey(def.id), model);

    if (this.activeProviderId(readSettings().provider) === id) {
      await updateSetting("model", model);
      await this.postSettings();
      this.reload();
    }
    await this.showProviderGallery();
  }

  async disconnectProvider(id: string): Promise<void> {
    const def = findProviderDef(id);
    if (!def || def.local) {
      return;
    }
    await this.context.secrets.delete(providerKeySecret(id));
    const settings = readSettings();
    if (this.activeProviderId(settings.provider) === id) {
      await this.context.secrets.delete(API_KEY_SECRET);
      await this.postSettings();
      this.reload();
    }
    await this.showProviderGallery();
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
    await this.postSettings();
    this.reload();
  }

  async setApiKey(value: string, clear = false): Promise<void> {
    const activeId = this.activeProviderId(readSettings().provider);
    const remembersKey = activeId && activeId !== "generic" && activeId !== "custom";

    if (clear) {
      await this.context.secrets.delete(API_KEY_SECRET);
      if (remembersKey) {
        await this.context.secrets.delete(providerKeySecret(activeId));
      }
    } else {
      const trimmed = value.trim();
      if (!trimmed) {
        return;
      }
      await this.context.secrets.store(API_KEY_SECRET, trimmed);
      if (remembersKey) {
        await this.context.secrets.store(providerKeySecret(activeId), trimmed);
      }
    }
    await this.postSettings();
    this.reload();
  }

  async toggleAutoApprove(next: boolean): Promise<void> {
    await updateSetting("autoApprove", next);
    await this.postSettings();
    this.reload();
  }

  async toggleSkills(next: boolean): Promise<void> {
    await updateSetting("skills", next);
    await this.postSettings();
    this.reload();
  }

  async toggleDelegation(next: boolean): Promise<void> {
    await updateSetting("delegation", next);
    await this.postSettings();
    this.reload();
  }

  async toggleMemory(next: boolean): Promise<void> {
    await updateSetting("memory", next);
    await this.postSettings();
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

    await this.postSettings();
    this.reload();
  }

  private onWebviewMessage(message: WebviewMessage): void {
    switch (message.type) {
      case "sendPrompt":
        void this.ensureClient().then(() => {
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
        });
        break;
      case "askAside":
        void this.ensureClient().then(() => {
          this.client
            ?.request("chat/ask", { prompt: message.prompt })
            .then((response) => {
              if (response.error) {
                this.post({ type: "asideError", id: message.id, message: response.error.message });
              } else {
                this.post({ type: "asideAnswer", id: message.id, text: response.result?.text ?? "" });
              }
            });
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
      case "showProviders":
        this.showProviderGallery();
        break;
      case "connectProvider":
        this.connectProvider(String(message.id ?? ""));
        break;
      case "changeProviderModel":
        this.changeProviderModel(String(message.id ?? ""));
        break;
      case "disconnectProvider":
        this.disconnectProvider(String(message.id ?? ""));
        break;
      case "selectSession":
        this.selectSession();
        break;
      case "selectModel":
        this.selectModel(message.current ?? "");
        break;
      case "setApiKey":
        this.setApiKey(String(message.value ?? ""), !!message.clear);
        break;
      case "toggleAutoApprove":
        this.toggleAutoApprove(!!message.next);
        break;
      case "toggleSkills":
        this.toggleSkills(!!message.next);
        break;
      case "toggleDelegation":
        this.toggleDelegation(!!message.next);
        break;
      case "toggleMemory":
        this.toggleMemory(!!message.next);
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

  private async ensureClient(): Promise<void> {
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
      delegation: settings.delegation,
      memory: settings.memory,
      autoApprove: settings.autoApprove,
      mcpServers: settings.mcpServers,
      resolveSetting: (value) => this.resolveSetting(value),
    });
    const apiKey = await this.context.secrets.get(API_KEY_SECRET);
    const env = spawnEnvForApiKey(apiKey, this.providerApiKeyEnvNames(settings.provider));

    const client = new RpcClient(command, args, currentWorkspaceFolder(), env);
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

  private readProviderAuth(provider: string): {
    apiKeyEnv?: string;
    authHeader?: string;
    providerFile?: string;
  } {
    const filePath = this.resolveSetting(provider);
    if (!filePath.endsWith(".json")) {
      return {};
    }
    const providerFile = path.basename(filePath);
    try {
      return { ...providerAuthFromJson(fs.readFileSync(filePath, "utf8")), providerFile };
    } catch {
      return { providerFile };
    }
  }

  private providerApiKeyEnvNames(provider: string): string[] {
    const envName = this.readProviderAuth(provider).apiKeyEnv;
    return envName ? [envName] : [];
  }

  private disposeClient(): void {
    this.client?.dispose();
    this.client = undefined;
  }

  private post(message: { type: string } & Record<string, unknown>): void {
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
