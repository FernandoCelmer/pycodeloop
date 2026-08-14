import * as vscode from "vscode";
import * as path from "path";
import { readSettings, updateSetting } from "../../services/settings.service";
import { API_KEY_SECRET, providerKeySecret } from "../../services/credentials.service";
import { PostMessage, ResolveSetting } from "../chat/chat.types";
import { PROVIDER_CATALOG, findProviderDef } from "./providerCatalog";
import { ADD_MCP_SERVER_LABEL, addServer, parseServerLabel, removeServer, toQuickPickLabels } from "./mcpServerList";

export class SettingsController {
  constructor(
    private readonly context: vscode.ExtensionContext,
    private readonly post: PostMessage,
    private readonly resolveSetting: ResolveSetting,
    private readonly readAuthFor: (provider: string) => {
      apiKeyEnv?: string;
      authHeader?: string;
      providerFile?: string;
    },
    private readonly reload: () => void
  ) {}

  async postSettings(): Promise<void> {
    await this.healStaleModel();
    const settings = readSettings();
    const apiKey = await this.context.secrets.get(API_KEY_SECRET);
    const auth = this.readAuthFor(settings.provider);
    this.post({
      type: "settings",
      model: settings.model,
      autoApprove: settings.autoApprove,
      skills: settings.skills,
      delegation: settings.delegation,
      memory: settings.memory,
      mcpServers: settings.mcpServers,
      hasApiKey: Boolean(apiKey),
      apiKeyEnv: auth.apiKeyEnv,
      authHeader: auth.authHeader,
      providerFile: auth.providerFile,
    });
  }

  async selectConfig(): Promise<void> {
    const picked = await vscode.window.showOpenDialog({
      canSelectMany: false,
      filters: { "Provider config": ["json"] },
      openLabel: "Use as provider config",
      defaultUri: vscode.workspace.workspaceFolders?.[0]?.uri,
    });
    const file = picked?.[0];
    if (!file) {
      return;
    }

    await updateSetting("provider", file.fsPath);
    await updateSetting("url", "");
    this.post({ type: "configChanged", path: file.fsPath });
    await this.postSettings();
    this.reload();
  }

  private providersDir(): string {
    return vscode.Uri.joinPath(this.context.extensionUri, "providers").fsPath;
  }

  private providerModelKey(id: string): string {
    return `pycodeloop.providerModel.${id}`;
  }

  private storedModelFor(def: (typeof PROVIDER_CATALOG)[number]): string {
    const stored = this.context.globalState.get<string>(this.providerModelKey(def.id));
    return stored && def.models.includes(stored) ? stored : def.defaultModel;
  }

  private async healStaleModel(): Promise<void> {
    const settings = readSettings();
    const def = findProviderDef(this.activeProviderId(settings.provider));
    if (!def || !settings.model || def.models.includes(settings.model)) {
      return;
    }
    await updateSetting("model", def.defaultModel);
    await this.context.globalState.update(this.providerModelKey(def.id), def.defaultModel);
  }

  private async pickModelFor(def: (typeof PROVIDER_CATALOG)[number]): Promise<string | undefined> {
    const current = this.storedModelFor(def);
    const modelItems = [...def.models.map((m) => ({ label: m })), { label: "Custom…" }];
    const modelPick = await vscode.window.showQuickPick(modelItems, {
      title: `${def.label} model`,
      placeHolder: `Current: ${current}`,
    });
    if (!modelPick) {
      return undefined;
    }
    if (modelPick.label !== "Custom…") {
      return modelPick.label;
    }
    return (
      (await vscode.window.showInputBox({
        title: `${def.label} model`,
        value: current,
        ignoreFocusOut: true,
      })) ?? undefined
    );
  }

  activeProviderId(providerSetting: string): string {
    if (!providerSetting) {
      return "";
    }
    const resolved = this.resolveSetting(providerSetting);
    if (resolved === "generic") {
      return "generic";
    }
    const dir = this.providersDir();
    for (const def of PROVIDER_CATALOG) {
      if (resolved === path.join(dir, def.file)) {
        return def.id;
      }
    }
    return "custom";
  }

  async openProviderGallery(): Promise<void> {
    await vscode.commands.executeCommand("pycodeloop.chat.focus");
    await this.showProviderGallery();
  }

  async showProviderGallery(): Promise<void> {
    const settings = readSettings();
    const activeId = this.activeProviderId(settings.provider);
    const activeHasKey = Boolean(await this.context.secrets.get(API_KEY_SECRET));

    const items = await Promise.all(
      PROVIDER_CATALOG.map(async (def) => {
        const isActive = def.id === activeId;
        const hasKey = def.local
          ? false
          : isActive
            ? activeHasKey
            : Boolean(await this.context.secrets.get(providerKeySecret(def.id)));
        return {
          id: def.id,
          label: def.label,
          description: def.description,
          model: isActive && settings.model ? settings.model : this.storedModelFor(def),
          local: def.local,
          active: isActive,
          connected: hasKey,
        };
      })
    );

    this.post({ type: "providers", items, activeId });
  }

  async connectProvider(id: string): Promise<void> {
    if (id === "custom") {
      await this.selectConfig();
      await this.showProviderGallery();
      return;
    }

    if (id === "generic") {
      const current = readSettings();
      const url = await vscode.window.showInputBox({
        title: "Generic provider URL",
        prompt: "OpenAI-compatible chat/completions endpoint",
        value: current.provider === "generic" ? current.url : "",
        placeHolder: "https://api.example.com/v1/chat/completions",
        ignoreFocusOut: true,
      });
      if (!url) {
        return;
      }
      await updateSetting("provider", "generic");
      await updateSetting("url", url);
      await this.selectModel(readSettings().model);
      await this.showProviderGallery();
      return;
    }

    const def = findProviderDef(id);
    if (!def) {
      return;
    }

    const model = await this.pickModelFor(def);
    if (!model) {
      return;
    }
    await this.context.globalState.update(this.providerModelKey(def.id), model);

    if (!def.local) {
      const remembered = await this.context.secrets.get(providerKeySecret(def.id));
      if (remembered) {
        await this.context.secrets.store(API_KEY_SECRET, remembered);
      } else {
        const key = await vscode.window.showInputBox({
          title: `${def.label} API key`,
          prompt: `Stored securely, sent as ${def.file === "anthropic.json" ? "x-api-key" : "Authorization: Bearer …"}`,
          password: true,
          ignoreFocusOut: true,
        });
        const trimmed = key?.trim();
        if (trimmed) {
          await this.context.secrets.store(API_KEY_SECRET, trimmed);
          await this.context.secrets.store(providerKeySecret(def.id), trimmed);
        }
      }
    }

    const providerPath = path.join(this.providersDir(), def.file);
    await updateSetting("provider", providerPath);
    await updateSetting("url", "");
    await updateSetting("model", model);

    this.post({ type: "configChanged", path: providerPath });
    await this.postSettings();
    await this.showProviderGallery();
    this.reload();
  }

  async changeProviderModel(id: string): Promise<void> {
    const def = findProviderDef(id);
    if (!def) {
      return;
    }
    const model = await this.pickModelFor(def);
    if (!model) {
      return;
    }
    await this.context.globalState.update(this.providerModelKey(def.id), model);

    if (this.activeProviderId(readSettings().provider) === id) {
      await updateSetting("model", model);
      await this.postSettings();
      this.reload();
    }
    await this.showProviderGallery();
  }

  async disconnectProvider(id: string): Promise<void> {
    const def = findProviderDef(id);
    if (!def || def.local) {
      return;
    }
    await this.context.secrets.delete(providerKeySecret(id));
    const settings = readSettings();
    if (this.activeProviderId(settings.provider) === id) {
      await this.context.secrets.delete(API_KEY_SECRET);
      await this.postSettings();
      this.reload();
    }
    await this.showProviderGallery();
  }

  async selectModel(current: string): Promise<void> {
    const model = await vscode.window.showInputBox({
      title: "CodeLoop model override",
      prompt: "Model name (empty clears the override and uses the provider's default)",
      value: current,
      placeHolder: "e.g. claude-sonnet-5, gpt-5",
    });
    if (model === undefined) {
      return;
    }

    await updateSetting("model", model);
    await this.postSettings();
    this.reload();
  }

  async setApiKey(value: string, clear = false): Promise<void> {
    const activeId = this.activeProviderId(readSettings().provider);
    const remembersKey = activeId && activeId !== "generic" && activeId !== "custom";

    if (clear) {
      await this.context.secrets.delete(API_KEY_SECRET);
      if (remembersKey) {
        await this.context.secrets.delete(providerKeySecret(activeId));
      }
    } else {
      const trimmed = value.trim();
      if (!trimmed) {
        return;
      }
      await this.context.secrets.store(API_KEY_SECRET, trimmed);
      if (remembersKey) {
        await this.context.secrets.store(providerKeySecret(activeId), trimmed);
      }
    }
    await this.postSettings();
    this.reload();
  }

  async toggleAutoApprove(next: boolean): Promise<void> {
    await updateSetting("autoApprove", next);
    await this.postSettings();
    this.reload();
  }

  async toggleSkills(next: boolean): Promise<void> {
    await updateSetting("skills", next);
    await this.postSettings();
    this.reload();
  }

  async toggleDelegation(next: boolean): Promise<void> {
    await updateSetting("delegation", next);
    await this.postSettings();
    this.reload();
  }

  async toggleMemory(next: boolean): Promise<void> {
    await updateSetting("memory", next);
    await this.postSettings();
    this.reload();
  }

  async manageMcpServers(): Promise<void> {
    const servers = readSettings().mcpServers;

    const picked = await vscode.window.showQuickPick(toQuickPickLabels(servers), {
      title: "CodeLoop MCP servers",
      placeHolder: servers.length ? "Pick a server to remove, or add a new one" : "No MCP servers configured yet",
    });
    if (!picked) {
      return;
    }

    if (picked === ADD_MCP_SERVER_LABEL) {
      const command = await vscode.window.showInputBox({
        title: "MCP server launch command",
        prompt: "e.g. npx -y @modelcontextprotocol/server-filesystem .",
        placeHolder: "npx -y @modelcontextprotocol/server-filesystem .",
        ignoreFocusOut: true,
      });
      if (!command) {
        return;
      }
      await updateSetting("mcpServers", addServer(servers, command));
    } else {
      const removed = parseServerLabel(picked);
      if (!removed) {
        return;
      }
      const confirm = await vscode.window.showQuickPick(["Remove", "Cancel"], {
        title: `Remove "${removed}"?`,
      });
      if (confirm !== "Remove") {
        return;
      }
      await updateSetting("mcpServers", removeServer(servers, removed));
    }

    await this.postSettings();
    this.reload();
  }
}
