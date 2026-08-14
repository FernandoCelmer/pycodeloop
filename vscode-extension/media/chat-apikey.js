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
