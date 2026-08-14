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
      <button id="new-session" class="secondary icon-btn" title="New session">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
      </button>
      <button id="menu-sessions" class="secondary" title="Sessions">Sessions</button>
      <button id="menu-provider" class="secondary" title="Select provider">Provider</button>
      <div id="menu-anchor">
        <button id="menu-toggle" class="secondary icon-btn" title="Settings">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="21" x2="5" y2="14"/><line x1="5" y1="10" x2="5" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="19" y1="21" x2="19" y2="16"/><line x1="19" y1="12" x2="19" y2="3"/><line x1="2" y1="14" x2="8" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="16" y1="16" x2="22" y2="16"/></svg>
        </button>
        <div id="menu" hidden>
          <button id="menu-api-key" class="menu-item"><span id="menu-api-key-label">API Key</span></button>
          <button id="menu-model" class="menu-item">Model</button>
          <button id="menu-auto-approve" class="menu-item">
            <span id="menu-auto-approve-check" class="check-box"></span> Auto-approve tools
          </button>
          <button id="menu-skills" class="menu-item">
            <span id="menu-skills-check" class="check-box"></span> Skills discovery
          </button>
          <button id="menu-delegation" class="menu-item">
            <span id="menu-delegation-check" class="check-box"></span> Sub-agent delegation
          </button>
          <button id="menu-memory" class="menu-item">
            <span id="menu-memory-check" class="check-box"></span> Project memory
          </button>
          <button id="menu-mcp" class="menu-item">MCP Servers</button>
          <button id="menu-reload" class="menu-item">Reload Connection</button>
          <button id="menu-settings" class="menu-item">Open Settings</button>
        </div>
      </div>
    </div>
  </div>
  <div id="messages"></div>
  <div id="provider-gallery" hidden>
    <div class="gallery-header">
      <button id="gallery-back" class="gallery-back">Back to chat</button>
      <h2 class="gallery-title">Connect a provider.</h2>
    </div>
    <div id="gallery-list" class="gallery-list"></div>
    <div class="gallery-footer">
      <button id="gallery-custom">Custom provider (URL or JSON)</button>
    </div>
  </div>
  <div id="session-gallery" hidden>
    <div class="gallery-header">
      <button id="session-gallery-back" class="gallery-back">Back to chat</button>
      <h2 class="gallery-title">Sessions.</h2>
    </div>
    <div id="session-list" class="gallery-list"></div>
    <div class="gallery-footer">
      <button id="session-gallery-new">New session</button>
    </div>
  </div>
  <div id="composer">
    <div id="attachments" hidden></div>
    <textarea id="prompt" placeholder="Ask CodeLoop… (paste a screenshot to attach it)" rows="2" disabled></textarea>
    <input type="file" id="attach-file" accept="image/*" multiple hidden />
    <div id="composer-actions">
      <button id="attach" class="secondary" title="Attach image" disabled>Attach</button>
      <span id="context-pill"></span>
      <button id="send" disabled>Send</button>
      <button id="cancel" disabled>Cancel</button>
    </div>
  </div>
  <script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
}
