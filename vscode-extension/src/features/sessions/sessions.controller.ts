import * as vscode from "vscode";
import * as crypto from "crypto";
import { RpcClient } from "../../core-client/core-client";
import { sortByRecency } from "../../services/storage.service";
import { PostMessage } from "../chat/chat.types";
import { SessionListItem } from "./sessions.types";

const SESSION_KEY_STATE = "pycodeloop.sessionKey";

export class SessionsController {
  private sessionKey: string;

  constructor(
    private readonly context: vscode.ExtensionContext,
    private readonly post: PostMessage,
    private readonly ensureClient: () => Promise<void>,
    private readonly getClient: () => RpcClient | undefined
  ) {
    this.sessionKey = context.workspaceState.get<string>(SESSION_KEY_STATE) ?? crypto.randomUUID();
  }

  getSessionKey(): string {
    return this.sessionKey;
  }

  newSession(): void {
    this.sessionKey = crypto.randomUUID();
    this.context.workspaceState.update(SESSION_KEY_STATE, this.sessionKey);
    this.post({ type: "sessionReset" });
  }

  async showSessionGallery(): Promise<void> {
    await this.ensureClient();
    const client = this.getClient();
    if (!client) {
      return;
    }

    const response = await client.request("session/list");
    const sessions: SessionListItem[] = sortByRecency(response.result?.sessions ?? []);

    this.post({
      type: "sessions",
      items: sessions.map((session) => ({
        key: session.key,
        active: session.key === this.sessionKey,
        messageCount: session.message_count ?? 0,
        cwd: session.cwd,
        updatedAt: session.updated_at ? new Date(session.updated_at * 1000).toLocaleString() : undefined,
      })),
    });
  }

  async switchSession(key: string): Promise<void> {
    if (!key || key === this.sessionKey) {
      return;
    }

    this.sessionKey = key;
    await this.context.workspaceState.update(SESSION_KEY_STATE, this.sessionKey);
    this.post({ type: "sessionReset" });
    await this.loadHistory();
  }

  async loadHistory(): Promise<void> {
    const client = this.getClient();
    if (!client) {
      return;
    }
    const response = await client.request("session/load", { key: this.sessionKey });
    const messages = response.result?.messages ?? [];
    if (messages.length) {
      this.post({ type: "history", messages });
    }
  }
}
