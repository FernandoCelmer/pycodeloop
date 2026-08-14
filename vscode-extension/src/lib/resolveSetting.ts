export function resolveWorkspacePath(value: string, workspaceFolder: string): string {
  return value.replace(/\$\{workspaceFolder\}/g, workspaceFolder);
}
