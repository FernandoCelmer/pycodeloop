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

export class RpcClient extends EventEmitter {
  private process: ChildProcessWithoutNullStreams;
  private nextId = 1;
  private pending = new Map<string, (message: RpcMessage) => void>();

  constructor(command: string, args: string[], cwd: string, env?: Record<string, string>) {
    super();
    this.process = spawn(command, args, {
      cwd,
      env: env ? { ...process.env, ...env } : process.env,
    });

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

    this.process.on("error", (error) => {
      this.emit("spawnError", error);
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

  notify(method: string, params: Record<string, unknown> = {}): void {
    this.write({ jsonrpc: "2.0", method, params });
  }

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
