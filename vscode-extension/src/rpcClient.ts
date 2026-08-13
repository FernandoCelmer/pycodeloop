import { ChildProcessWithoutNullStreams, spawn } from "child_process";
import * as readline from "readline";
import { EventEmitter } from "events";

export interface RpcMessage {
  jsonrpc: "2.0";
  id?: string | number;
  method?: string;
  params?: any;
  result?: any;
  error?: { code: number; message: string };
}

/**
 * Talks JSON-RPC 2.0 to a `pycodeloop serve` child process over its
 * stdin/stdout — one JSON object per line in both directions. Requests
 * with an `id` resolve a promise on the matching response; everything
 * else (server notifications, and our own outgoing notifications) is
 * fire-and-forget, surfaced as EventEmitter events keyed by method name.
 */
export class RpcClient extends EventEmitter {
  private process: ChildProcessWithoutNullStreams;
  private nextId = 1;
  private pending = new Map<string, (message: RpcMessage) => void>();

  constructor(command: string, args: string[], cwd: string) {
    super();
    this.process = spawn(command, args, { cwd });

    const rl = readline.createInterface({ input: this.process.stdout });
    rl.on("line", (line) => {
      const trimmed = line.trim();
      if (!trimmed) {
        return;
      }
      let message: RpcMessage;
      try {
        message = JSON.parse(trimmed);
      } catch {
        return;
      }
      this.dispatch(message);
    });

    this.process.stderr.on("data", (chunk: Buffer) => {
      this.emit("stderr", chunk.toString());
    });

    this.process.on("exit", (code, signal) => {
      this.emit("exit", { code, signal });
    });
  }

  private dispatch(message: RpcMessage): void {
    if (message.id !== undefined && (message.result !== undefined || message.error)) {
      const resolver = this.pending.get(String(message.id));
      if (resolver) {
        this.pending.delete(String(message.id));
        resolver(message);
      }
      return;
    }
    if (message.method) {
      this.emit(message.method, message.params ?? {});
    }
  }

  /** Fire-and-forget notification — no response expected. */
  notify(method: string, params: Record<string, unknown> = {}): void {
    this.write({ jsonrpc: "2.0", method, params });
  }

  /** Request/response round trip, resolved when a matching `id` comes back. */
  request(method: string, params: Record<string, unknown> = {}): Promise<RpcMessage> {
    const id = String(this.nextId++);
    return new Promise((resolve) => {
      this.pending.set(id, resolve);
      this.write({ jsonrpc: "2.0", id, method, params });
    });
  }

  private write(message: RpcMessage): void {
    this.process.stdin.write(JSON.stringify(message) + "\n");
  }

  dispose(): void {
    this.pending.clear();
    this.process.kill();
  }
}
