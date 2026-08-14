import * as vscode from "vscode";
import { ChatViewProvider } from "./chatViewProvider";

export function activate(context: vscode.ExtensionContext): void {
  const provider = new ChatViewProvider(context);

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
    vscode.commands.registerCommand("pycodeloop.selectProvider", () => {
      provider.openProviderGallery();
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
