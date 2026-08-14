import * as vscode from "vscode";
import * as crypto from "crypto";
import { resolveWorkspacePath } from "../../services/workspace.service";
import { currentWorkspaceFolder } from "../../services/settings.service";
import { ChatController } from "../../features/chat/chat.controller";
import { SessionsController } from "../../features/sessions/sessions.controller";
import { SettingsController } from "../../features/settings/settings.controller";
import { renderChatHtml } from "../webview/html";
import { WebviewMessage } from "../webview/messages";

export class ChatViewProvider implements vscode.WebviewViewProvider {
  private webviewView: vscode.WebviewView | undefined;
  private readonly chat: ChatController;
  private readonly sessions: SessionsController;
  private readonly settings: SettingsController;

  constructor(private readonly context: vscode.ExtensionContext) {
    this.chat = new ChatController(
      context,
      (message) => this.post(message),
      (value) => this.resolveSetting(value),
      () => this.sessions.loadHistory()
    );
    this.sessions = new SessionsController(
      context,
      (message) => this.post(message),
      () => this.chat.ensureClient(),
      () => this.chat.getClient()
    );
    this.settings = new SettingsController(
      context,
      (message) => this.post(message),
      (value) => this.resolveSetting(value),
      (provider) => this.chat.readAuthFor(provider),
      () => this.chat.reload()
    );
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
    webviewView.onDidDispose(() => this.chat.dispose());

    this.settings.postSettings();
    this.chat.startConnection();
  }

  newSession(): void {
    this.sessions.newSession();
  }

  showSessionGallery(): Promise<void> {
    return this.sessions.showSessionGallery();
  }

  openProviderGallery(): Promise<void> {
    return this.settings.openProviderGallery();
  }

  selectConfig(): Promise<void> {
    return this.settings.selectConfig();
  }

  private onWebviewMessage(message: WebviewMessage): void {
    switch (message.type) {
      case "sendPrompt":
        this.chat.sendPrompt(message.prompt, this.sessions.getSessionKey(), message.images);
        break;
      case "askAside":
        this.chat.askAside(message.id, message.prompt);
        break;
      case "cancel":
        this.chat.cancel();
        break;
      case "confirmResponse":
        this.chat.confirmResponse(message.id, message.answer);
        break;
      case "newSession":
        this.sessions.newSession();
        break;
      case "selectConfig":
        this.settings.selectConfig();
        break;
      case "showProviders":
        this.settings.showProviderGallery();
        break;
      case "connectProvider":
        this.settings.connectProvider(String(message.id ?? ""));
        break;
      case "changeProviderModel":
        this.settings.changeProviderModel(String(message.id ?? ""));
        break;
      case "disconnectProvider":
        this.settings.disconnectProvider(String(message.id ?? ""));
        break;
      case "showSessions":
        this.sessions.showSessionGallery();
        break;
      case "switchSession":
        this.sessions.switchSession(message.key);
        break;
      case "selectModel":
        this.settings.selectModel(message.current ?? "");
        break;
      case "setApiKey":
        this.settings.setApiKey(String(message.value ?? ""), !!message.clear);
        break;
      case "toggleAutoApprove":
        this.settings.toggleAutoApprove(!!message.next);
        break;
      case "toggleSkills":
        this.settings.toggleSkills(!!message.next);
        break;
      case "toggleDelegation":
        this.settings.toggleDelegation(!!message.next);
        break;
      case "toggleMemory":
        this.settings.toggleMemory(!!message.next);
        break;
      case "manageMcpServers":
        this.settings.manageMcpServers();
        break;
      case "reload":
        this.chat.reload();
        break;
      case "installCli":
        this.chat.installCli();
        break;
      case "openSettings":
        vscode.commands.executeCommand("workbench.action.openSettings", "pycodeloop");
        break;
    }
  }

  private post(message: { type: string } & Record<string, unknown>): void {
    this.webviewView?.webview.postMessage(message);
  }

  private static readonly SCRIPT_FILES = [
    "dom.js",
    "render-utils.js",
    "chat-turns.js",
    "chat-tools.js",
    "chat-apikey.js",
    "composer.js",
    "menu.js",
    "gallery.js",
    "app.js",
  ];

  private renderHtml(webview: vscode.Webview): string {
    const scriptUris = ChatViewProvider.SCRIPT_FILES.map((file) =>
      webview.asWebviewUri(vscode.Uri.joinPath(this.context.extensionUri, "media", file)).toString()
    );
    const styleUri = webview.asWebviewUri(vscode.Uri.joinPath(this.context.extensionUri, "media", "main.css"));

    return renderChatHtml({
      cspSource: webview.cspSource,
      scriptUris,
      styleUri: styleUri.toString(),
      nonce: crypto.randomBytes(16).toString("hex"),
    });
  }
}
