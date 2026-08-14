export interface RpcMessage {
  jsonrpc: "2.0";
  id?: string | number;
  method?: string;
  params?: any;
  result?: any;
  error?: { code: number; message: string };
}

export function encodeRpcMessage(message: RpcMessage): string {
  return JSON.stringify(message) + "\n";
}

export function decodeRpcMessage(line: string): RpcMessage | undefined {
  const trimmed = line.trim();
  if (!trimmed) {
    return undefined;
  }
  try {
    return JSON.parse(trimmed);
  } catch {
    return undefined;
  }
}
