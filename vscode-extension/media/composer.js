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
