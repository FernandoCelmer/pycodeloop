(function () {
  function renderFatalError(message) {
    const box = document.createElement("div");
    box.style.cssText =
      "margin:8px;padding:8px 10px;border:1px solid var(--vscode-errorForeground);" +
      "border-radius:6px;color:var(--vscode-errorForeground);white-space:pre-wrap;" +
      "font-family:var(--vscode-editor-font-family);font-size:0.85em;";
    box.textContent = "CodeLoop UI error:\n" + message;
    document.body.appendChild(box);
  }
  window.addEventListener("error", (event) => {
    renderFatalError((event.error && event.error.stack) || event.message);
  });
  window.addEventListener("unhandledrejection", (event) => {
    renderFatalError(String(event.reason && event.reason.stack ? event.reason.stack : event.reason));
  });

  const vscode = acquireVsCodeApi();

  const messagesEl = document.getElementById("messages");
  const promptEl = document.getElementById("prompt");
  const sendButton = document.getElementById("send");
  const cancelButton = document.getElementById("cancel");
  const newSessionButton = document.getElementById("new-session");
  const menuToggle = document.getElementById("menu-toggle");
  const menu = document.getElementById("menu");
  const menuSessions = document.getElementById("menu-sessions");
  const menuProvider = document.getElementById("menu-provider");
  const menuModel = document.getElementById("menu-model");
  const menuAutoApprove = document.getElementById("menu-auto-approve");
  const menuAutoApproveCheck = document.getElementById("menu-auto-approve-check");
  const menuReload = document.getElementById("menu-reload");
  const menuSettings = document.getElementById("menu-settings");
  const statusDot = document.getElementById("status-dot");
  const statusText = document.getElementById("status-text");
  const contextPill = document.getElementById("context-pill");
  const attachmentsEl = document.getElementById("attachments");
  const attachButton = document.getElementById("attach");
  const attachFileInput = document.getElementById("attach-file");

  let assistantTurn = null;
  let pendingAssistantText = "";
  const pendingToolCards = new Map(); // name -> array of card elements, FIFO
  let currentModel = "";
  let autoApprove = false;
  let pendingImages = []; // base64 PNG/JPEG data (no data: prefix)

  function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function escapeHtml(text) {
    return text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  // Minimal, safe-ish markdown: fenced code blocks, headings, lists, links,
  // inline code, bold/italic. Escapes HTML first so model output can never
  // inject markup.
  function renderInline(segment) {
    segment = escapeHtml(segment);
    segment = segment.replace(/`([^`]+)`/g, "<code>$1</code>");
    segment = segment.replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>");
    segment = segment.replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g, "<i>$1</i>");
    segment = segment.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2">$1</a>');
    return segment;
  }

  function renderTextBlock(text) {
    const lines = text.split("\n");
    let html = "";
    let listTag = null; // "ul" | "ol" | null
    const closeList = () => {
      if (listTag) {
        html += "</" + listTag + ">";
        listTag = null;
      }
    };
    for (const line of lines) {
      const heading = /^(#{1,6})\s+(.*)$/.exec(line);
      const bullet = /^[-*]\s+(.*)$/.exec(line);
      const numbered = /^\d+\.\s+(.*)$/.exec(line);
      if (heading) {
        closeList();
        const level = heading[1].length;
        html += "<h" + level + ">" + renderInline(heading[2]) + "</h" + level + ">";
      } else if (bullet) {
        if (listTag !== "ul") {
          closeList();
          html += "<ul>";
          listTag = "ul";
        }
        html += "<li>" + renderInline(bullet[1]) + "</li>";
      } else if (numbered) {
        if (listTag !== "ol") {
          closeList();
          html += "<ol>";
          listTag = "ol";
        }
        html += "<li>" + renderInline(numbered[1]) + "</li>";
      } else if (line.trim() === "") {
        closeList();
        html += "\n";
      } else {
        closeList();
        html += renderInline(line) + "\n";
      }
    }
    closeList();
    return html;
  }

  function renderMarkdown(raw) {
    // Guard against an unterminated fence mid-stream (odd backtick count):
    // render everything before the last opening ``` as-is and leave the
    // in-progress fence as plain text until it closes.
    const blocks = raw.split(/```(\w*\n[\s\S]*?)```/g);
    let html = "";
    for (let i = 0; i < blocks.length; i++) {
      if (i % 2 === 1) {
        html += "<pre><code>" + escapeHtml(blocks[i].replace(/^\w*\n/, "")) + "</code></pre>";
      } else {
        html += renderTextBlock(blocks[i]);
      }
    }
    return html;
  }

  function setStatus(state, text) {
    statusDot.className = "dot " + state;
    statusText.textContent = text;
    statusText.title = text;
  }

  function addSystemNote(text, isError) {
    const el = document.createElement("div");
    el.className = "system-note" + (isError ? " error" : "");
    el.textContent = text;
    messagesEl.appendChild(el);
    scrollToBottom();
    return el;
  }

  function addUserTurn(text, images) {
    const turn = document.createElement("div");
    turn.className = "turn user";

    if (images && images.length) {
      const strip = document.createElement("div");
      strip.className = "turn-attachments";
      strip.style.marginBottom = "6px";
      for (const base64 of images) {
        const thumb = document.createElement("div");
        thumb.className = "attachment-thumb";
        const img = document.createElement("img");
        img.src = "data:image/png;base64," + base64;
        thumb.appendChild(img);
        strip.appendChild(thumb);
      }
      turn.appendChild(strip);
    }

    if (text) {
      const bubble = document.createElement("div");
      bubble.className = "bubble";
      bubble.textContent = text;
      turn.appendChild(bubble);
    }

    messagesEl.appendChild(turn);
    scrollToBottom();
  }

  function ensureAssistantTurn() {
    if (assistantTurn) {
      return assistantTurn;
    }
    const turn = document.createElement("div");
    turn.className = "turn assistant";
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    turn.appendChild(bubble);
    messagesEl.appendChild(turn);
    assistantTurn = { turnEl: turn, bubbleEl: bubble, rawText: "" };
    scrollToBottom();
    return assistantTurn;
  }

  function appendAssistantDelta(delta) {
    pendingAssistantText += delta;
    if (!pendingAssistantText.trim()) {
      return;
    }
    const turn = ensureAssistantTurn();
    turn.rawText += pendingAssistantText;
    pendingAssistantText = "";
    turn.bubbleEl.innerHTML = renderMarkdown(turn.rawText);
    scrollToBottom();
  }

  function finishAssistantTurn(fallbackText) {
    pendingAssistantText = "";
    if (!assistantTurn) {
      if (fallbackText && fallbackText.trim()) {
        const turn = ensureAssistantTurn();
        turn.rawText = fallbackText;
        turn.bubbleEl.innerHTML = renderMarkdown(fallbackText);
      }
    } else if (!assistantTurn.rawText && fallbackText && fallbackText.trim()) {
      assistantTurn.rawText = fallbackText;
      assistantTurn.bubbleEl.innerHTML = renderMarkdown(fallbackText);
    } else if (!assistantTurn.rawText.trim()) {
      assistantTurn.turnEl.remove();
    }
    assistantTurn = null;
  }

  function addTurnMeta(text) {
    const el = document.createElement("div");
    el.className = "turn-meta";
    el.textContent = text;
    messagesEl.appendChild(el);
    scrollToBottom();
    return el;
  }

  const TOOL_ICONS = {
    read_file: "📄",
    write_file: "📝",
    edit_file: "✏️",
    delete_file: "🗑",
    list_dir: "📁",
    grep: "🔍",
    glob: "🔍",
    bash: "❯_",
    http_request: "🌐",
    web_fetch: "🌐",
    todo: "☑",
  };

  function toolIcon(name) {
    return TOOL_ICONS[name] || "🔧";
  }

  function argsPreview(args) {
    try {
      return JSON.stringify(args);
    } catch {
      return String(args);
    }
  }

  function renderToolCall(name, args) {
    const card = document.createElement("div");
    card.className = "tool-card";

    const header = document.createElement("div");
    header.className = "tool-card-header";

    const icon = document.createElement("span");
    icon.className = "tool-icon";
    icon.textContent = toolIcon(name);

    const nameEl = document.createElement("span");
    nameEl.className = "tool-name";
    nameEl.textContent = name;

    const preview = document.createElement("span");
    preview.className = "tool-args-preview";
    preview.textContent = argsPreview(args);

    const status = document.createElement("span");
    status.className = "tool-status pending";
    status.textContent = "●";

    header.appendChild(icon);
    header.appendChild(nameEl);
    header.appendChild(preview);
    header.appendChild(status);
    header.addEventListener("click", () => card.classList.toggle("expanded"));

    const body = document.createElement("div");
    body.className = "tool-card-body";

    const argsLabel = document.createElement("div");
    argsLabel.className = "section-label";
    argsLabel.textContent = "Arguments";
    const argsPre = document.createElement("pre");
    argsPre.textContent = JSON.stringify(args, null, 2);
    body.appendChild(argsLabel);
    body.appendChild(argsPre);

    card.appendChild(header);
    card.appendChild(body);
    messagesEl.appendChild(card);
    scrollToBottom();

    card.__status = status;
    card.__body = body;

    if (!pendingToolCards.has(name)) {
      pendingToolCards.set(name, []);
    }
    pendingToolCards.get(name).push(card);

    return card;
  }

  function resolveToolResult(name, result, isError) {
    const queue = pendingToolCards.get(name);
    const card = queue && queue.shift();
    if (!card) {
      return;
    }

    card.__status.textContent = isError ? "✗" : "✓";
    card.__status.className = "tool-status " + (isError ? "error" : "ok");

    const resultLabel = document.createElement("div");
    resultLabel.className = "section-label";
    resultLabel.textContent = isError ? "Error" : "Result";
    const resultPre = document.createElement("pre");
    resultPre.textContent = result.length > 4000 ? result.slice(0, 4000) + "…" : result;
    card.__body.appendChild(resultLabel);
    card.__body.appendChild(resultPre);
  }

  function renderHistory(messages) {
    const cardsById = new Map();

    for (const message of messages) {
      if (message.role === "user") {
        addUserTurn(
          typeof message.content === "string" ? message.content : String(message.content),
          message.images
        );
      } else if (message.role === "assistant") {
        if (message.content) {
          finishAssistantTurn(message.content);
        }
        for (const call of message.toolCalls || []) {
          cardsById.set(call.id, renderToolCall(call.name, call.arguments));
        }
      } else if (message.role === "tool") {
        const card = cardsById.get(message.toolCallId);
        if (!card) {
          continue;
        }
        card.__status.textContent = "✓";
        card.__status.className = "tool-status ok";
        const resultLabel = document.createElement("div");
        resultLabel.className = "section-label";
        resultLabel.textContent = "Result";
        const resultPre = document.createElement("pre");
        resultPre.textContent = message.content;
        card.__body.appendChild(resultLabel);
        card.__body.appendChild(resultPre);
      }
    }

    // renderToolCall() also queues each card in pendingToolCards (keyed by
    // name) for live toolResult matching — replayed cards are already
    // resolved above, so clear it or a later live result would wrongly
    // pop a stale historical card instead of the new one.
    pendingToolCards.clear();
    scrollToBottom();
  }

  function markToolAutoApproved(name) {
    // Wire order is toolCall -> (confirm gate) autoApproved -> toolResult,
    // so the card still waiting at the front of this name's queue is the
    // one being auto-approved right now.
    const queue = pendingToolCards.get(name);
    const card = queue && queue[0];
    if (!card) {
      return;
    }
    card.__status.title = "auto-approved";
    card.__status.classList.add("auto-approved");
  }

  function setBusy(busy) {
    sendButton.disabled = busy;
    cancelButton.disabled = !busy;
  }

  function setReady(ready) {
    promptEl.disabled = !ready;
    sendButton.disabled = !ready;
    attachButton.disabled = !ready;
    if (ready) {
      promptEl.focus();
    }
  }

  function clearStatusCards() {
    for (const box of messagesEl.querySelectorAll(".confirm-box.status-card")) {
      box.remove();
    }
  }

  function renderSetupCard(title, body) {
    const box = document.createElement("div");
    box.className = "confirm-box status-card";

    const heading = document.createElement("div");
    heading.className = "title";
    heading.textContent = title;
    box.appendChild(heading);

    if (body) {
      const desc = document.createElement("div");
      desc.className = "turn-meta";
      desc.textContent = body;
      box.appendChild(desc);
    }

    const actions = document.createElement("div");
    actions.className = "confirm-actions";

    const configure = document.createElement("button");
    configure.textContent = "Select Provider Config…";
    configure.addEventListener("click", () => {
      vscode.postMessage({ type: "selectConfig" });
    });

    const settings = document.createElement("button");
    settings.className = "secondary";
    settings.textContent = "Open Settings";
    settings.addEventListener("click", () => {
      vscode.postMessage({ type: "openSettings" });
    });

    actions.appendChild(configure);
    actions.appendChild(settings);
    box.appendChild(actions);

    messagesEl.appendChild(box);
    scrollToBottom();
    return box;
  }

  function renderCliMissingCard(command) {
    const box = document.createElement("div");
    box.className = "confirm-box status-card";

    const heading = document.createElement("div");
    heading.className = "title";
    heading.textContent = "CodeLoop CLI not found";
    box.appendChild(heading);

    const desc = document.createElement("div");
    desc.className = "turn-meta";
    desc.textContent = `"${command}" isn't on PATH. Install it and CodeLoop will connect automatically.`;
    box.appendChild(desc);

    const actions = document.createElement("div");
    actions.className = "confirm-actions";

    const install = document.createElement("button");
    install.textContent = "Install CodeLoop CLI";
    install.addEventListener("click", () => {
      vscode.postMessage({ type: "installCli" });
    });

    const settings = document.createElement("button");
    settings.className = "secondary";
    settings.textContent = "Open Settings";
    settings.addEventListener("click", () => {
      vscode.postMessage({ type: "openSettings" });
    });

    actions.appendChild(install);
    actions.appendChild(settings);
    box.appendChild(actions);

    messagesEl.appendChild(box);
    scrollToBottom();
    return box;
  }

  function renderConfirmRequest(params) {
    const box = document.createElement("div");
    box.className = "confirm-box";

    const title = document.createElement("div");
    title.className = "title";
    title.textContent = "Run tool: " + params.name + "?";
    box.appendChild(title);

    const preview = document.createElement("pre");
    preview.textContent = params.preview;
    box.appendChild(preview);

    const actions = document.createElement("div");
    actions.className = "confirm-actions";

    const approve = document.createElement("button");
    approve.textContent = "Approve";
    approve.addEventListener("click", () => {
      vscode.postMessage({ type: "confirmResponse", id: params.id, answer: true });
      box.remove();
    });

    const decline = document.createElement("button");
    decline.className = "secondary";
    decline.textContent = "Decline";
    decline.addEventListener("click", () => {
      vscode.postMessage({ type: "confirmResponse", id: params.id, answer: false });
      box.remove();
    });

    actions.appendChild(approve);
    actions.appendChild(decline);
    box.appendChild(actions);

    messagesEl.appendChild(box);
    scrollToBottom();
  }

  function shortProviderLabel(provider) {
    if (!provider) {
      return provider;
    }
    const parts = provider.split(/[\\/]/);
    return parts[parts.length - 1] || provider;
  }

  function renderAttachmentsPreview() {
    attachmentsEl.innerHTML = "";
    attachmentsEl.hidden = pendingImages.length === 0;
    pendingImages.forEach((base64, index) => {
      const thumb = document.createElement("div");
      thumb.className = "attachment-thumb";
      const img = document.createElement("img");
      img.src = "data:image/png;base64," + base64;
      const remove = document.createElement("button");
      remove.className = "remove";
      remove.textContent = "✕";
      remove.title = "Remove";
      remove.addEventListener("click", () => {
        pendingImages.splice(index, 1);
        renderAttachmentsPreview();
      });
      thumb.appendChild(img);
      thumb.appendChild(remove);
      attachmentsEl.appendChild(thumb);
    });
  }

  function addPendingImageFile(file) {
    if (!file.type.startsWith("image/")) {
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      const base64 = String(reader.result).split(",")[1];
      if (base64) {
        pendingImages.push(base64);
        renderAttachmentsPreview();
      }
    };
    reader.readAsDataURL(file);
  }

  function send() {
    const prompt = promptEl.value.trim();
    if (!prompt && !pendingImages.length) {
      return;
    }
    addUserTurn(prompt, pendingImages);
    promptEl.value = "";
    const images = pendingImages;
    pendingImages = [];
    renderAttachmentsPreview();
    assistantTurn = null;
    setBusy(true);
    vscode.postMessage({ type: "sendPrompt", prompt, images });
  }

  sendButton.addEventListener("click", send);
  cancelButton.addEventListener("click", () => {
    vscode.postMessage({ type: "cancel" });
  });
  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !cancelButton.disabled) {
      vscode.postMessage({ type: "cancel" });
    }
  });
  newSessionButton.addEventListener("click", () => {
    vscode.postMessage({ type: "newSession" });
  });
  promptEl.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      send();
    }
  });
  promptEl.addEventListener("paste", (event) => {
    const items = event.clipboardData ? event.clipboardData.items : [];
    for (const item of items) {
      if (item.kind === "file" && item.type.startsWith("image/")) {
        event.preventDefault();
        addPendingImageFile(item.getAsFile());
      }
    }
  });
  attachButton.addEventListener("click", () => attachFileInput.click());
  attachFileInput.addEventListener("change", () => {
    for (const file of attachFileInput.files) {
      addPendingImageFile(file);
    }
    attachFileInput.value = "";
  });

  // --- gear menu ---

  function closeMenu() {
    menu.hidden = true;
  }

  menuToggle.addEventListener("click", (event) => {
    event.stopPropagation();
    menu.hidden = !menu.hidden;
  });
  document.addEventListener("click", (event) => {
    if (!menu.hidden && !menu.contains(event.target) && event.target !== menuToggle) {
      closeMenu();
    }
  });
  menuSessions.addEventListener("click", () => {
    closeMenu();
    vscode.postMessage({ type: "selectSession" });
  });
  menuProvider.addEventListener("click", () => {
    closeMenu();
    vscode.postMessage({ type: "selectConfig" });
  });
  menuModel.addEventListener("click", () => {
    closeMenu();
    vscode.postMessage({ type: "selectModel", current: currentModel });
  });
  menuAutoApprove.addEventListener("click", () => {
    closeMenu();
    vscode.postMessage({ type: "toggleAutoApprove", next: !autoApprove });
  });
  menuReload.addEventListener("click", () => {
    closeMenu();
    vscode.postMessage({ type: "reload" });
  });
  menuSettings.addEventListener("click", () => {
    closeMenu();
    vscode.postMessage({ type: "openSettings" });
  });

  function applySettings(model, nextAutoApprove) {
    currentModel = model || "";
    autoApprove = !!nextAutoApprove;
    menuModel.title = currentModel ? "Current: " + currentModel : "Using provider default";
    menuAutoApproveCheck.textContent = autoApprove ? "☑" : "☐";
  }

  window.addEventListener("message", (event) => {
    const message = event.data;

    switch (message.type) {
      case "settings":
        applySettings(message.model, message.autoApprove);
        break;
      case "cliMissing":
        clearStatusCards();
        setStatus("", "CLI not found");
        renderCliMissingCard(message.command);
        break;
      case "needsSetup":
        clearStatusCards();
        setStatus("", "Not configured");
        renderSetupCard(
          "Set up a provider to start chatting",
          "Pick a provider config JSON file, or set pycodeloop.command/provider/model/url in Settings."
        );
        break;
      case "connecting":
        setStatus("connecting", "Connecting…");
        break;
      case "ready":
        setStatus("ready", shortProviderLabel(message.provider) + " · " + message.model);
        setReady(true);
        break;
      case "textDelta":
        appendAssistantDelta(message.delta);
        break;
      case "toolCall":
        renderToolCall(message.name, message.arguments);
        break;
      case "toolResult":
        resolveToolResult(message.name, message.result, message.isError);
        break;
      case "autoApproved":
        markToolAutoApproved(message.name);
        break;
      case "confirmRequest":
        renderConfirmRequest(message);
        break;
      case "usage":
        addTurnMeta(
          message.totalInputTokens + " in / " + message.totalOutputTokens +
            " out · " + message.elapsed.toFixed(1) + "s"
        );
        break;
      case "context": {
        const pct = message.limit ? Math.round((100 * message.used) / message.limit) : 0;
        contextPill.textContent = pct + "% context";
        contextPill.classList.toggle("high", pct >= 80);
        break;
      }
      case "compactStart":
        contextPill.textContent = "compacting…";
        contextPill.classList.add("compacting");
        break;
      case "compactEnd":
        contextPill.classList.remove("compacting");
        addSystemNote("Compacted — " + message.before + " → " + message.after + " messages");
        break;
      case "retry":
        addSystemNote("Retrying (" + message.attempt + "/3) — " + message.error, true);
        break;
      case "done":
        finishAssistantTurn(message.text);
        setBusy(false);
        break;
      case "error":
        finishAssistantTurn();
        addSystemNote(message.message, true);
        setBusy(false);
        break;
      case "connectionError":
        clearStatusCards();
        setStatus("error", "Not connected");
        setReady(false);
        setBusy(false);
        renderSetupCard(message.message, "Fix the setting below and try again.");
        break;
      case "processExit":
        setStatus("error", "Disconnected");
        setReady(false);
        addSystemNote("pycodeloop serve exited (code " + message.code + ")", true);
        setBusy(false);
        break;
      case "sessionReset":
        messagesEl.innerHTML = "";
        assistantTurn = null;
        pendingToolCards.clear();
        break;
      case "history":
        renderHistory(message.messages);
        break;
      case "configChanged":
        setStatus("connecting", "Reconnecting…");
        setReady(false);
        addSystemNote("Provider config set to " + message.path);
        break;
    }
  });
})();
