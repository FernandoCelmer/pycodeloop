/** Substitutes VS Code's `${workspaceFolder}` variable in a setting value.
 * Pure — takes the workspace path as a parameter instead of reading it from
 * `vscode.workspace` so it can be unit tested without the VS Code API. */
export function resolveWorkspacePath(value: string, workspaceFolder: string): string {
  return value.replace(/\$\{workspaceFolder\}/g, workspaceFolder);
}
