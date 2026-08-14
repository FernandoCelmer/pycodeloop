import { ChildProcessWithoutNullStreams, spawn } from "child_process";
import * as readline from "readline";
import { EventEmitter } from "events";

export class CoreProcess extends EventEmitter {
  private process: ChildProcessWithoutNullStreams;

  constructor(command: string, args: string[], cwd: string, env?: Record<string, string>) {
    super();
    this.process = spawn(command, args, {
      cwd,
      env: env ? { ...process.env, ...env } : process.env,
    });

    const rl = readline.createInterface({ input: this.process.stdout });
    rl.on("line", (line) => this.emit("line", line));

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

  write(data: string): void {
    this.process.stdin.write(data);
  }

  kill(): void {
    this.process.kill();
  }
}
