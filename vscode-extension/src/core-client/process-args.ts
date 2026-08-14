export interface ServeArgsOptions {
  provider: string;
  model: string;
  url: string;
  skills: boolean;
  delegation: boolean;
  memory: boolean;
  autoApprove: boolean;
  mcpServers: string[];
  resolveSetting: (value: string) => string;
}

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
