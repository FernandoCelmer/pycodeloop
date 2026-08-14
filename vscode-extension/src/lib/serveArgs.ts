export interface ServeArgsOptions {
  provider: string;
  model: string;
  url: string;
  skills: boolean;
  delegation: boolean;
  memory: boolean;
  autoApprove: boolean;
  mcpServers: string[];
  /** Resolves ${workspaceFolder} etc. in a setting value — injected so this
   * stays pure and doesn't need the VS Code API to be unit tested. */
  resolveSetting: (value: string) => string;
}

/** Builds the argv for `pycodeloop serve`, mirroring the CLI's own flags.
 * Pure function extracted from ChatViewProvider.ensureClient() so the
 * option-to-flag mapping can be unit tested without spawning a process. */
export function buildServeArgs(options: ServeArgsOptions): string[] {
  const args = ["serve"];

  if (options.provider) {
    args.push("--provider", options.resolveSetting(options.provider));
  }
  if (options.model) {
    args.push("--model", options.model);
  }
  if (options.url) {
    args.push("--url", options.url);
  }
  if (!options.skills) {
    args.push("--no-skills");
  }
  if (options.delegation) {
    args.push("--delegate");
  }
  if (!options.memory) {
    args.push("--no-memory");
  }
  if (options.autoApprove) {
    args.push("--yes");
  }
  for (const server of options.mcpServers) {
    args.push("--mcp", server);
  }

  return args;
}
