export const ADD_MCP_SERVER_LABEL = "$(add) Add MCP server…";

const SERVER_ITEM_PREFIX = "$(server) ";

/** Formats configured server commands as QuickPick labels, "Add" pinned
 * first. Pure — the picker itself is a thin VS Code wrapper around this. */
export function toQuickPickLabels(servers: string[]): string[] {
  return [ADD_MCP_SERVER_LABEL, ...servers.map((server) => SERVER_ITEM_PREFIX + server)];
}

/** Recovers the raw server command from a label built by toQuickPickLabels.
 * Returns null for the "Add" entry — it isn't a server to remove. */
export function parseServerLabel(label: string): string | null {
  if (label === ADD_MCP_SERVER_LABEL) {
    return null;
  }
  return label.startsWith(SERVER_ITEM_PREFIX) ? label.slice(SERVER_ITEM_PREFIX.length) : label;
}

/** Returns a new list with `server` appended, without mutating the input. */
export function addServer(servers: string[], server: string): string[] {
  return [...servers, server];
}

/** Returns a new list with `server` removed, without mutating the input. */
export function removeServer(servers: string[], server: string): string[] {
  return servers.filter((s) => s !== server);
}
