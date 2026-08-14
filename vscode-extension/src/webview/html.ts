export interface ChatHtmlOptions {
  cspSource: string;
  scriptUri: string;
  styleUri: string;
  nonce: string;
}

/** Renders the webview shell markup. Pure string template — the caller
 * resolves URIs/nonce via the VS Code API and passes plain strings in, so
 * this is unit-testable without a real webview. */
export function renderChatHtml(options: ChatHtmlOptions): string {
  const { cspSource, scriptUri, styleUri, nonce } = options;

  return /* html */ `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${cspSource}; script-src 'nonce-${nonce}'; img-src ${cspSource} data:;" />
  <link rel="stylesheet" href="${styleUri}" />
  <title>CodeLoop</title>
</head>
<body>
  <div id="toolbar">
    <div id="status">
      <span id="status-dot" class="dot"></span>
      <span id="status-text">Not connected</span>
    </div>
    <div id="toolbar-actions">
      <button id="new-session" class="secondary" title="New session">New</button>
      <div id="menu-anchor">
        <button id="menu-toggle" class="secondary" title="Configure">⚙</button>
        <div id="menu" hidden>
          <button id="menu-sessions" class="menu-item">Sessions…</button>
          <button id="menu-provider" class="menu-item">Provider Config…</button>
          <button id="menu-api-key" class="menu-item">API Key…</button>
          <button id="menu-model" class="menu-item">Model…</button>
          <button id="menu-auto-approve" class="menu-item">
            <span id="menu-auto-approve-check" class="check-box"></span> Auto-approve tools
          </button>
          <button id="menu-skills" class="menu-item">
            <span id="menu-skills-check" class="check-box"></span> Skills discovery
          </button>
          <button id="menu-mcp" class="menu-item">MCP Servers…</button>
          <button id="menu-reload" class="menu-item">Reload Connection</button>
          <button id="menu-settings" class="menu-item">Open Settings</button>
        </div>
      </div>
    </div>
  </div>
  <div id="messages"></div>
  <div id="composer">
    <div id="attachments" hidden></div>
    <textarea id="prompt" placeholder="Ask CodeLoop… (paste a screenshot to attach it)" rows="2" disabled></textarea>
    <input type="file" id="attach-file" accept="image/*" multiple hidden />
    <div id="composer-actions">
      <button id="attach" class="secondary" title="Attach image" disabled>📎</button>
      <span id="context-pill"></span>
      <button id="send" disabled>Send</button>
      <button id="cancel" disabled>Cancel</button>
    </div>
  </div>
  <script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
}
