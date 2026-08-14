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
  const menuApiKey = document.getElementById("menu-api-key");
  const menuApiKeyLabel = document.getElementById("menu-api-key-label");
  const menuModel = document.getElementById("menu-model");
  const menuAutoApprove = document.getElementById("menu-auto-approve");
  const menuAutoApproveCheck = document.getElementById("menu-auto-approve-check");
  const menuSkills = document.getElementById("menu-skills");
  const menuSkillsCheck = document.getElementById("menu-skills-check");
  const menuDelegation = document.getElementById("menu-delegation");
  const menuDelegationCheck = document.getElementById("menu-delegation-check");
  const menuMemory = document.getElementById("menu-memory");
  const menuMemoryCheck = document.getElementById("menu-memory-check");
  const menuMcp = document.getElementById("menu-mcp");
  const menuReload = document.getElementById("menu-reload");
  const menuSettings = document.getElementById("menu-settings");
  const statusDot = document.getElementById("status-dot");
  const statusText = document.getElementById("status-text");
  const contextPill = document.getElementById("context-pill");
  const attachmentsEl = document.getElementById("attachments");
  const attachButton = document.getElementById("attach");
  const attachFileInput = document.getElementById("attach-file");
  const providerGallery = document.getElementById("provider-gallery");
  const galleryBack = document.getElementById("gallery-back");
  const galleryList = document.getElementById("gallery-list");
  const galleryCustom = document.getElementById("gallery-custom");
  const sessionGallery = document.getElementById("session-gallery");
  const sessionGalleryBack = document.getElementById("session-gallery-back");
  const sessionList = document.getElementById("session-list");
  const sessionGalleryNew = document.getElementById("session-gallery-new");

  let assistantTurn = null;
  let pendingAssistantText = "";
  let isBusy = false;
  const pendingToolCards = new Map();
  let currentModel = "";
  let autoApprove = false;
  let skillsEnabled = true;
  let delegationEnabled = false;
  let memoryEnabled = true;
  let hasApiKey = false;
  let apiKeyEnv = "";
  let authHeader = "";
  let providerFile = "";
  let apiKeyCard = null;
  let apiKeyPromptHidden = false;
  let pendingImages = [];

  function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function escapeHtml(text) {
    return text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function renderInline(segment) {
    segment = escapeHtml(segment);
    segment = segment.replace(/`([^`]+)`/g, "<code>$1</code>");
    segment = segment.replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>");
    segment = segment.replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g, "<i>$1</i>");
    segment = segment.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2">$1</a>');
    return segment;
  }

  function isTableRow(line) {
    return /\|/.test(line) && line.trim() !== "";
  }

  function isTableSeparator(line) {
    return /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/.test(line);
  }

  function splitTableRow(line) {
    const trimmed = line.trim().replace(/^\|/, "").replace(/\|$/, "");
    return trimmed.split("|").map((cell) => cell.trim());
  }

  function renderTable(headerLine, bodyLines) {
    const headerCells = splitTableRow(headerLine);
    let html = "<table><thead><tr>";
    for (const cell of headerCells) {
      html += "<th>" + renderInline(cell) + "</th>";
    }
    html += "</tr></thead><tbody>";
    for (const row of bodyLines) {
      html += "<tr>";
      for (const cell of splitTableRow(row)) {
        html += "<td>" + renderInline(cell) + "</td>";
      }
      html += "</tr>";
    }
    html += "</tbody></table>";
    return html;
  }

  function renderTextBlock(text) {
    const lines = text.split("\n");
    let html = "";
    let listTag = null;
    const closeList = () => {
      if (listTag) {
        html += "</" + listTag + ">";
        listTag = null;
      }
    };
    let i = 0;
    while (i < lines.length) {
      const line = lines[i];

      if (isTableRow(line) && i + 1 < lines.length && isTableSeparator(lines[i + 1])) {
        closeList();
        const bodyLines = [];
        let j = i + 2;
        while (j < lines.length && isTableRow(lines[j]) && !isTableSeparator(lines[j])) {
          bodyLines.push(lines[j]);
          j++;
        }
        html += renderTable(line, bodyLines);
        i = j;
        continue;
      }

      const heading = /^(#{1,6})\s+(.*)$/.exec(line);
      const bullet = /^[-*]\s+(.*)$/.exec(line);
      const numbered = /^\d+\.\s+(.*)$/.exec(line);
      const rule = /^ {0,3}([-*_])(?: *\1){2,} *$/.test(line);
      if (rule) {
        closeList();
        html += "<hr>";
      } else if (heading) {
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
      i++;
    }
    closeList();
    return html;
  }

  function renderMarkdown(raw) {
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

  function parseApiError(text) {
    const match = /^HTTP Error (\d+): ([^:]+): ([\s\S]*)$/.exec(text);
    if (!match) {
      return null;
    }
    const [, status, reason, rest] = match;
    let detail = null;
    let friendly = null;
    try {
      detail = JSON.parse(rest);
      friendly = detail?.error?.message || detail?.message || null;
    } catch {
      detail = rest;
    }
    return { status, reason, friendly, raw: typeof detail === "string" ? detail : JSON.stringify(detail, null, 2) };
  }

  function addErrorNote(text) {
    const parsed = parseApiError(text);
    if (!parsed) {
      addSystemNote(text, true);
      return;
    }

    const box = document.createElement("div");
    box.className = "system-note error api-error";

    const summary = document.createElement("div");
    summary.className = "api-error-summary";
    summary.textContent = `API error ${parsed.status} (${parsed.reason})`;
    box.appendChild(summary);

    if (parsed.friendly) {
      const friendly = document.createElement("div");
      friendly.className = "api-error-friendly";
      friendly.textContent = parsed.friendly;
      box.appendChild(friendly);
    }

    const details = document.createElement("details");
    const summaryToggle = document.createElement("summary");
    summaryToggle.textContent = "Details";
    const pre = document.createElement("pre");
    pre.textContent = parsed.raw;
    details.appendChild(summaryToggle);
    details.appendChild(pre);
    box.appendChild(details);

    if (parsed.status === "401") {
      const actions = document.createElement("div");
      actions.className = "confirm-actions";
      const setKey = document.createElement("button");
      setKey.textContent = apiKeyEnv ? "Set " + apiKeyEnv : "Set API Key";
      setKey.addEventListener("click", () => {
        apiKeyPromptHidden = false;
        renderApiKeyCard();
      });
      actions.appendChild(setKey);
      box.appendChild(actions);
      apiKeyPromptHidden = false;
      renderApiKeyCard();
    }

    messagesEl.appendChild(box);
    scrollToBottom();
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

  const pendingAsides = new Map();

  function addAsideTurn(id, text) {
    const question = document.createElement("div");
    question.className = "turn user aside";
    const questionBubble = document.createElement("div");
    questionBubble.className = "bubble";
    questionBubble.textContent = text;
    question.appendChild(questionBubble);
    messagesEl.appendChild(question);

    const answer = document.createElement("div");
    answer.className = "turn assistant aside";
    const answerBubble = document.createElement("div");
    answerBubble.className = "bubble";
    answerBubble.textContent = "…";
    answer.appendChild(answerBubble);
    messagesEl.appendChild(answer);

    pendingAsides.set(id, answerBubble);
    scrollToBottom();
  }

  function resolveAsideTurn(id, text, isError) {
    const bubble = pendingAsides.get(id);
    if (!bubble) {
      return;
    }
    pendingAsides.delete(id);
    bubble.innerHTML = renderMarkdown(text);
    if (isError) {
      bubble.classList.add("error");
    }
    scrollToBottom();
  }

  let thinkingEl = null;
  let thinkingTimer = null;
  let thinkingStartedAt = 0;
  let activeDelegateCount = 0;

  function formatElapsed(seconds) {
    return seconds < 60 ? seconds + "s" : Math.floor(seconds / 60) + "m " + (seconds % 60) + "s";
  }

  function thinkingLabel() {
    return activeDelegateCount > 0
      ? activeDelegateCount + " sub-agent" + (activeDelegateCount > 1 ? "s" : "") + " working"
      : "Thinking";
  }

  function renderThinkingText() {
    if (!thinkingEl) {
      return;
    }
    const elapsed = Math.round((Date.now() - thinkingStartedAt) / 1000);
    thinkingEl.querySelector(".thinking-label").textContent = thinkingLabel() + "…";
    thinkingEl.querySelector(".thinking-elapsed").textContent = formatElapsed(elapsed);
  }

  function showThinkingIndicator() {
    if (thinkingEl) {
      renderThinkingText();
      return;
    }
    thinkingStartedAt = Date.now();
    const line = document.createElement("div");
    line.className = "thinking-line";
    line.innerHTML =
      '<span class="thinking-glyph">●</span>' +
      '<span class="thinking-label"></span>' +
      '<span class="thinking-elapsed"></span>';
    messagesEl.appendChild(line);
    thinkingEl = line;
    renderThinkingText();
    thinkingTimer = setInterval(renderThinkingText, 1000);
    scrollToBottom();
  }

  function hideThinkingIndicator() {
    if (thinkingTimer) {
      clearInterval(thinkingTimer);
      thinkingTimer = null;
    }
    if (thinkingEl) {
      thinkingEl.remove();
      thinkingEl = null;
    }
    activeDelegateCount = 0;
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
    hideThinkingIndicator();
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
    hideThinkingIndicator();
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
    delegate: "🤖",
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
    if (name === "delegate") {
      activeDelegateCount++;
      showThinkingIndicator();
    } else {
      hideThinkingIndicator();
    }
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
    card.__diffPreview = null;

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

    if (card.__diffPreview && !isError) {
      const { el, adds, removes } = renderDiffBlock(card.__diffPreview);
      const diffLabel = document.createElement("div");
      diffLabel.className = "section-label";
      diffLabel.textContent = diffSummary(adds, removes);
      card.__body.appendChild(diffLabel);
      card.__body.appendChild(el);
      card.classList.add("expanded");
    } else {
      const resultLabel = document.createElement("div");
      resultLabel.className = "section-label";
      resultLabel.textContent = isError ? "Error" : "Result";
      const resultPre = document.createElement("pre");
      resultPre.textContent = result.length > 4000 ? result.slice(0, 4000) + "…" : result;
      card.__body.appendChild(resultLabel);
      card.__body.appendChild(resultPre);
    }

    if (name === "delegate") {
      activeDelegateCount = Math.max(0, activeDelegateCount - 1);
      renderThinkingText();
    }

    const stillPending = [...pendingToolCards.values()].some((q) => q.length > 0);
    if (!stillPending && isBusy) {
      showThinkingIndicator();
    }
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

    pendingToolCards.clear();
    scrollToBottom();
  }

  function markToolAutoApproved(name) {
    const queue = pendingToolCards.get(name);
    const card = queue && queue[0];
    if (!card) {
      return;
    }
    card.__status.title = "auto-approved";
    card.__status.classList.add("auto-approved");
  }

  function setBusy(busy) {
    isBusy = busy;
    sendButton.disabled = false;
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
    configure.textContent = "Select Provider";
    configure.addEventListener("click", () => {
      vscode.postMessage({ type: "showProviders" });
    });

    const apiKey = document.createElement("button");
    apiKey.className = "secondary";
    apiKey.textContent = "Set API Key";
    apiKey.addEventListener("click", () => {
      renderApiKeyCard();
    });

    const settings = document.createElement("button");
    settings.className = "secondary";
    settings.textContent = "Open Settings";
    settings.addEventListener("click", () => {
      vscode.postMessage({ type: "openSettings" });
    });

    actions.appendChild(configure);
    actions.appendChild(apiKey);
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

  const DIFF_TOOLS = new Set(["write_file", "edit_file", "delete_file"]);

  function renderDiffBlock(diffText) {
    const pre = document.createElement("pre");
    pre.className = "diff-block";
    let adds = 0;
    let removes = 0;

    for (const line of diffText.split("\n")) {
      if (line.startsWith("+++") || line.startsWith("---")) {
        continue;
      }
      const row = document.createElement("div");
      if (line.startsWith("@@")) {
        row.className = "diff-hunk";
      } else if (line.startsWith("+")) {
        row.className = "diff-add";
        adds++;
      } else if (line.startsWith("-")) {
        row.className = "diff-remove";
        removes++;
      }
      row.textContent = line;
      pre.appendChild(row);
    }

    return { el: pre, adds, removes };
  }

  function diffSummary(adds, removes) {
    if (adds && removes) {
      return "+" + adds + " -" + removes;
    }
    if (adds) {
      return "Added " + adds + " line" + (adds === 1 ? "" : "s");
    }
    if (removes) {
      return "Removed " + removes + " line" + (removes === 1 ? "" : "s");
    }
    return "No changes";
  }

  function renderConfirmRequest(params) {
    if (DIFF_TOOLS.has(params.name)) {
      const queue = pendingToolCards.get(params.name);
      const card = queue && queue[queue.length - 1];
      if (card) {
        card.__diffPreview = params.preview;
      }
    }

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

  function dismissApiKeyCard() {
    if (apiKeyCard) {
      apiKeyCard.remove();
      apiKeyCard = null;
    }
  }

  function apiKeyHint() {
    const file = providerFile || "The provider config";
    const env = apiKeyEnv;
    const header = authHeader;
    if (env && header) {
      return (
        file +
        " sends this key in the " +
        header +
        " header. Paste it here. CodeLoop sets " +
        env +
        " when it starts pycodeloop serve — no terminal export."
      );
    }
    if (env) {
      return (
        file +
        " reads " +
        env +
        ". Paste the key here. CodeLoop sets that variable for pycodeloop serve — no terminal export."
      );
    }
    return "Paste the API key for this provider. CodeLoop stores it in the editor secret store.";
  }

  function renderApiKeyCard() {
    dismissApiKeyCard();

    const box = document.createElement("div");
    box.className = "confirm-box status-card";

    const title = document.createElement("div");
    title.className = "title";
    title.textContent = hasApiKey
      ? "Update API key?"
      : apiKeyEnv
        ? "API key required: " + apiKeyEnv
        : "Set API key?";
    box.appendChild(title);

    const hint = document.createElement("div");
    hint.className = "turn-meta";
    hint.textContent = apiKeyHint();
    box.appendChild(hint);

    const input = document.createElement("input");
    input.type = "password";
    input.autocomplete = "off";
    input.spellcheck = false;
    input.placeholder = apiKeyEnv || "sk-…";
    box.appendChild(input);

    const actions = document.createElement("div");
    actions.className = "confirm-actions";

    const save = document.createElement("button");
    save.textContent = hasApiKey ? "Update" : "Save";
    save.addEventListener("click", () => {
      const value = input.value.trim();
      if (!value) {
        return;
      }
      apiKeyPromptHidden = false;
      vscode.postMessage({ type: "setApiKey", value });
      dismissApiKeyCard();
    });

    const cancel = document.createElement("button");
    cancel.className = "secondary";
    cancel.textContent = "Decline";
    cancel.addEventListener("click", () => {
      apiKeyPromptHidden = true;
      dismissApiKeyCard();
    });

    actions.appendChild(save);
    if (hasApiKey) {
      const clear = document.createElement("button");
      clear.className = "secondary";
      clear.textContent = "Clear";
      clear.addEventListener("click", () => {
        vscode.postMessage({ type: "setApiKey", value: "", clear: true });
        dismissApiKeyCard();
      });
      actions.appendChild(clear);
    }
    actions.appendChild(cancel);
    box.appendChild(actions);

    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        event.stopPropagation();
        save.click();
      }
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        apiKeyPromptHidden = true;
        dismissApiKeyCard();
      }
    });

    messagesEl.appendChild(box);
    apiKeyCard = box;
    scrollToBottom();
    input.focus();
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
    const images = pendingImages;

    if (isBusy) {
      const id = "aside-" + Date.now() + "-" + Math.random().toString(36).slice(2);
      addAsideTurn(id, prompt);
      promptEl.value = "";
      pendingImages = [];
      renderAttachmentsPreview();
      vscode.postMessage({ type: "askAside", id, prompt });
      return;
    }

    addUserTurn(prompt, images);
    promptEl.value = "";
    commandMenu.hidden = true;
    pendingImages = [];
    renderAttachmentsPreview();
    assistantTurn = null;
    setBusy(true);
    showThinkingIndicator();
    vscode.postMessage({ type: "sendPrompt", prompt, images });
  }

  const SLASH_COMMANDS = [
    { name: "new", description: "Start a new session", run: () => vscode.postMessage({ type: "newSession" }) },
    { name: "sessions", description: "Switch to a saved session", run: () => vscode.postMessage({ type: "showSessions" }) },
    { name: "provider", description: "Select a provider (Anthropic, OpenAI, Gemini, Grok, …)", run: () => vscode.postMessage({ type: "showProviders" }) },
    { name: "key", description: "Set or update the API key", run: () => renderApiKeyCard() },
    { name: "model", description: "Set a model override", run: () => vscode.postMessage({ type: "selectModel", current: currentModel }) },
    {
      name: "auto-approve",
      description: "Toggle auto-approve for dangerous tools",
      run: () => vscode.postMessage({ type: "toggleAutoApprove", next: !autoApprove }),
    },
    {
      name: "skills",
      description: "Toggle Claude/Cursor/AGENTS.md skills discovery",
      run: () => vscode.postMessage({ type: "toggleSkills", next: !skillsEnabled }),
    },
    {
      name: "delegate",
      description: "Toggle sub-agent delegation (parallel, read-only sub-agents)",
      run: () => vscode.postMessage({ type: "toggleDelegation", next: !delegationEnabled }),
    },
    {
      name: "memory",
      description: "Toggle project memory (.pycodeloop/memory.md)",
      run: () => vscode.postMessage({ type: "toggleMemory", next: !memoryEnabled }),
    },
    { name: "mcp", description: "Add or remove MCP servers", run: () => vscode.postMessage({ type: "manageMcpServers" }) },
    { name: "reload", description: "Reload the pycodeloop connection", run: () => vscode.postMessage({ type: "reload" }) },
    { name: "settings", description: "Open CodeLoop settings", run: () => vscode.postMessage({ type: "openSettings" }) },
    {
      name: "help",
      description: "List available commands",
      run: () => addSystemNote(SLASH_COMMANDS.map((c) => "/" + c.name).join("  ")),
    },
  ];

  const commandMenu = document.createElement("div");
  commandMenu.id = "command-menu";
  commandMenu.hidden = true;
  promptEl.insertAdjacentElement("beforebegin", commandMenu);

  let commandMenuItems = [];
  let commandMenuIndex = 0;

  function filteredCommands() {
    const query = promptEl.value.slice(1).toLowerCase();
    return SLASH_COMMANDS.filter((c) => c.name.startsWith(query));
  }

  function renderCommandMenu() {
    commandMenu.innerHTML = "";
    commandMenuItems.forEach((cmd, i) => {
      const item = document.createElement("div");
      item.className = "command-item" + (i === commandMenuIndex ? " active" : "");
      const name = document.createElement("span");
      name.className = "command-name";
      name.textContent = "/" + cmd.name;
      const desc = document.createElement("span");
      desc.className = "command-desc";
      desc.textContent = cmd.description;
      item.appendChild(name);
      item.appendChild(desc);
      item.addEventListener("mousedown", (event) => {
        event.preventDefault();
        runCommand(cmd);
      });
      commandMenu.appendChild(item);
    });
  }

  function updateCommandMenu() {
    const isCommand = promptEl.value.startsWith("/") && !promptEl.value.includes(" ");
    commandMenuItems = isCommand ? filteredCommands() : [];
    if (!commandMenuItems.length) {
      commandMenu.hidden = true;
      return;
    }
    commandMenuIndex = Math.min(commandMenuIndex, commandMenuItems.length - 1);
    renderCommandMenu();
    commandMenu.hidden = false;
  }

  function runCommand(cmd) {
    promptEl.value = "";
    commandMenu.hidden = true;
    cmd.run();
  }

  promptEl.addEventListener("input", () => {
    commandMenuIndex = 0;
    updateCommandMenu();
  });

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
    if (!commandMenu.hidden) {
      if (event.key === "ArrowDown") {
        event.preventDefault();
        commandMenuIndex = (commandMenuIndex + 1) % commandMenuItems.length;
        renderCommandMenu();
        return;
      }
      if (event.key === "ArrowUp") {
        event.preventDefault();
        commandMenuIndex = (commandMenuIndex - 1 + commandMenuItems.length) % commandMenuItems.length;
        renderCommandMenu();
        return;
      }
      if (event.key === "Enter" || event.key === "Tab") {
        event.preventDefault();
        runCommand(commandMenuItems[commandMenuIndex]);
        return;
      }
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        commandMenu.hidden = true;
        return;
      }
    }
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
  function onMenuClick(button, action) {
    button.addEventListener("click", () => {
      closeMenu();
      action();
    });
  }

  onMenuClick(menuSessions, () => vscode.postMessage({ type: "showSessions" }));
  onMenuClick(menuProvider, () => vscode.postMessage({ type: "showProviders" }));
  onMenuClick(menuApiKey, () => renderApiKeyCard());
  onMenuClick(menuModel, () => vscode.postMessage({ type: "selectModel", current: currentModel }));
  onMenuClick(menuAutoApprove, () => vscode.postMessage({ type: "toggleAutoApprove", next: !autoApprove }));
  onMenuClick(menuSkills, () => vscode.postMessage({ type: "toggleSkills", next: !skillsEnabled }));
  onMenuClick(menuDelegation, () => vscode.postMessage({ type: "toggleDelegation", next: !delegationEnabled }));
  onMenuClick(menuMemory, () => vscode.postMessage({ type: "toggleMemory", next: !memoryEnabled }));
  onMenuClick(menuMcp, () => vscode.postMessage({ type: "manageMcpServers" }));
  onMenuClick(menuReload, () => vscode.postMessage({ type: "reload" }));
  onMenuClick(menuSettings, () => vscode.postMessage({ type: "openSettings" }));

  function applySettings(message) {
    currentModel = message.model || "";
    autoApprove = !!message.autoApprove;
    skillsEnabled = message.skills !== false;
    delegationEnabled = !!message.delegation;
    memoryEnabled = message.memory !== false;
    hasApiKey = !!message.hasApiKey;
    apiKeyEnv = message.apiKeyEnv || "";
    authHeader = message.authHeader || "";
    providerFile = message.providerFile || "";
    menuModel.title = currentModel ? "Current: " + currentModel : "Using provider default";
    menuAutoApproveCheck.classList.toggle("checked", autoApprove);
    menuSkillsCheck.classList.toggle("checked", skillsEnabled);
    menuDelegationCheck.classList.toggle("checked", delegationEnabled);
    menuMemoryCheck.classList.toggle("checked", memoryEnabled);
    menuApiKeyLabel.textContent = hasApiKey
      ? "API Key (saved)"
      : apiKeyEnv
        ? "API Key (" + apiKeyEnv + ")"
        : "API Key";
    if (!hasApiKey && apiKeyEnv && !apiKeyCard && !apiKeyPromptHidden) {
      renderApiKeyCard();
    }
  }

  function showProviderGallery() {
    hideSessionGallery();
    providerGallery.hidden = false;
  }

  function hideProviderGallery() {
    providerGallery.hidden = true;
  }

  galleryBack.addEventListener("click", hideProviderGallery);
  galleryCustom.addEventListener("click", () => {
    vscode.postMessage({ type: "connectProvider", id: "custom" });
  });

  function showSessionGallery() {
    hideProviderGallery();
    sessionGallery.hidden = false;
  }

  function hideSessionGallery() {
    sessionGallery.hidden = true;
  }

  sessionGalleryBack.addEventListener("click", hideSessionGallery);
  sessionGalleryNew.addEventListener("click", () => {
    vscode.postMessage({ type: "newSession" });
  });

  function renderSessionGallery(items) {
    showSessionGallery();
    sessionList.textContent = "";

    if (!items.length) {
      const empty = document.createElement("p");
      empty.className = "provider-desc";
      empty.textContent = "No saved sessions yet.";
      sessionList.appendChild(empty);
      return;
    }

    for (const item of items) {
      const card = document.createElement("div");
      card.className = "provider-card";
      if (item.active) {
        card.classList.add("active");
      }

      const head = document.createElement("div");
      head.className = "provider-card-head";

      const nameRow = document.createElement("div");
      nameRow.className = "provider-name-row";
      const dot = document.createElement("span");
      dot.className = "provider-dot";
      const name = document.createElement("span");
      name.className = "provider-name";
      name.textContent = item.key;
      nameRow.append(dot, name);

      const chip = document.createElement("span");
      chip.className = "provider-chip " + (item.active ? "connected" : "");
      chip.textContent = item.active ? "Active" : item.messageCount + " msgs";

      head.append(nameRow, chip);

      const body = document.createElement("div");
      body.className = "provider-card-body";

      const desc = document.createElement("p");
      desc.className = "provider-desc";
      desc.textContent =
        item.messageCount +
        " messages" +
        (item.cwd ? " · " + item.cwd : "") +
        (item.updatedAt ? " · " + item.updatedAt : "");

      const action = document.createElement("button");
      if (item.active) {
        action.className = "secondary";
        action.textContent = "Active";
      } else {
        action.textContent = "Switch";
        action.addEventListener("click", () => {
          vscode.postMessage({ type: "switchSession", key: item.key });
        });
      }

      body.append(desc, action);
      card.append(head, body);
      sessionList.appendChild(card);
    }
  }

  function renderProviderGallery(items) {
    showProviderGallery();
    galleryList.textContent = "";

    for (const item of items) {
      const card = document.createElement("div");
      card.className = "provider-card";
      if (item.active) {
        card.classList.add("active");
      }

      const head = document.createElement("div");
      head.className = "provider-card-head";

      const nameRow = document.createElement("div");
      nameRow.className = "provider-name-row";
      const dot = document.createElement("span");
      dot.className = "provider-dot";
      const name = document.createElement("span");
      name.className = "provider-name";
      name.textContent = item.label;
      nameRow.append(dot, name);

      const chip = document.createElement("span");
      chip.className = "provider-chip " + (item.local ? "local" : item.connected ? "connected" : "");
      chip.textContent = item.local ? "Local" : item.connected ? "Connected" : "Needs key";

      head.append(nameRow, chip);

      const body = document.createElement("div");
      body.className = "provider-card-body";

      const desc = document.createElement("p");
      desc.className = "provider-desc";
      desc.textContent = item.description;

      const actions = document.createElement("div");
      actions.className = "provider-card-actions";

      const modelBtn = document.createElement("button");
      modelBtn.className = "secondary provider-model-btn";
      modelBtn.innerHTML =
        '<span class="provider-model-label">Model</span><span class="provider-model-value"></span>';
      modelBtn.querySelector(".provider-model-value").textContent = item.model;
      modelBtn.title = "Change model for this provider";
      modelBtn.addEventListener("click", () => {
        vscode.postMessage({ type: "changeProviderModel", id: item.id });
      });

      const action = document.createElement("button");
      if (item.active) {
        action.className = "secondary";
        action.textContent = "Active";
      } else {
        action.textContent = "Connect";
        action.addEventListener("click", () => {
          vscode.postMessage({ type: "connectProvider", id: item.id });
        });
      }

      actions.append(modelBtn, action);
      body.append(desc, actions);
      card.append(head, body);
      galleryList.appendChild(card);
    }
  }

  window.addEventListener("message", (event) => {
    const message = event.data;

    switch (message.type) {
      case "settings":
        applySettings(message);
        break;
      case "providers":
        renderProviderGallery(message.items);
        break;
      case "sessions":
        renderSessionGallery(message.items);
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
          "Pick a ready-made provider — Anthropic, OpenAI, Gemini, Grok, Groq, or a local model. The key stays in CodeLoop, never a terminal export."
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
        addErrorNote(message.message);
        setBusy(false);
        break;
      case "asideAnswer":
        resolveAsideTurn(message.id, message.text, false);
        break;
      case "asideError":
        resolveAsideTurn(message.id, message.message, true);
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
        hideSessionGallery();
        messagesEl.innerHTML = "";
        assistantTurn = null;
        apiKeyCard = null;
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
