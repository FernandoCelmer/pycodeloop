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
