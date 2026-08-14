import * as vscode from "vscode";

const SECTION = "pycodeloop";

export interface PycodeloopSettings {
  command: string;
  provider: string;
  model: string;
  url: string;
  skills: boolean;
  delegation: boolean;
  memory: boolean;
  autoApprove: boolean;
  mcpServers: string[];
}

export function readSettings(): PycodeloopSettings {
  const config = vscode.workspace.getConfiguration(SECTION);
  return {
    command: config.get<string>("command", "pycodeloop") || "pycodeloop",
    provider: config.get<string>("provider", ""),
    model: config.get<string>("model", ""),
    url: config.get<string>("url", ""),
    skills: config.get<boolean>("skills", true),
    delegation: config.get<boolean>("delegation", false),
    memory: config.get<boolean>("memory", true),
    autoApprove: config.get<boolean>("autoApprove", false),
    mcpServers: config.get<string[]>("mcpServers", []),
  };
}

export function updateSetting<K extends keyof PycodeloopSettings>(
  key: K,
  value: PycodeloopSettings[K]
): Thenable<void> {
  return vscode.workspace
    .getConfiguration(SECTION)
    .update(key, value, vscode.ConfigurationTarget.Workspace);
}

export function currentWorkspaceFolder(): string {
  return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? process.cwd();
}
