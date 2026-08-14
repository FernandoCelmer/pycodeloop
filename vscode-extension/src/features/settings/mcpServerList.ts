export const ADD_MCP_SERVER_LABEL = "$(add) Add MCP server…";

const SERVER_ITEM_PREFIX = "$(server) ";

export function toQuickPickLabels(servers: string[]): string[] {
  return [ADD_MCP_SERVER_LABEL, ...servers.map((server) => SERVER_ITEM_PREFIX + server)];
}

export function parseServerLabel(label: string): string | null {
  if (label === ADD_MCP_SERVER_LABEL) {
    return null;
  }
  return label.startsWith(SERVER_ITEM_PREFIX) ? label.slice(SERVER_ITEM_PREFIX.length) : label;
}

export function addServer(servers: string[], server: string): string[] {
  return [...servers, server];
}

export function removeServer(servers: string[], server: string): string[] {
  return servers.filter((s) => s !== server);
}
