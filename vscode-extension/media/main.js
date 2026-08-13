(function () {
  const vscode = acquireVsCodeApi();

  const messagesEl = document.getElementById("messages");
  const promptEl = document.getElementById("prompt");
  const sendButton = document.getElementById("send");
  const cancelButton = document.getElementById("cancel");

  let assistantBubble = null;

  function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function addBubble(className, text) {
    const el = document.createElement("div");
    el.className = "msg " + className;
    el.textContent = text;
    messagesEl.appendChild(el);
    scrollToBottom();
    return el;
  }

  function setBusy(busy) {
    sendButton.disabled = busy;
    cancelButton.disabled = !busy;
  }

  function send() {
    const prompt = promptEl.value.trim();
    if (!prompt) {
      return;
    }
    addBubble("user", prompt);
    promptEl.value = "";
    assistantBubble = null;
    setBusy(true);
    vscode.postMessage({ type: "sendPrompt", prompt });
  }

  sendButton.addEventListener("click", send);
  cancelButton.addEventListener("click", () => {
    vscode.postMessage({ type: "cancel" });
  });
  promptEl.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      send();
    }
  });

  function renderToolCall(name, args) {
    const el = document.createElement("div");
    el.className = "tool-call";
    el.textContent = name + "(" + JSON.stringify(args) + ")";
    messagesEl.appendChild(el);
    scrollToBottom();
    return el;
  }

  function renderConfirmRequest(params) {
    const box = document.createElement("div");
    box.className = "confirm-box";

    const title = document.createElement("div");
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

  window.addEventListener("message", (event) => {
    const message = event.data;

    switch (message.type) {
      case "ready":
        addBubble("meta", "Connected — " + message.provider + "/" + message.model);
        break;
      case "textDelta":
        if (!assistantBubble) {
          assistantBubble = addBubble("assistant", "");
        }
        assistantBubble.textContent += message.delta;
        scrollToBottom();
        break;
      case "toolCall":
        renderToolCall(message.name, message.arguments);
        break;
      case "toolResult": {
        const el = renderToolCall(
          message.name,
          message.isError ? "error" : "ok"
        );
        if (message.isError) {
          el.classList.add("error");
        }
        break;
      }
      case "confirmRequest":
        renderConfirmRequest(message);
        break;
      case "usage":
        addBubble(
          "meta",
          message.totalInputTokens + " in / " + message.totalOutputTokens +
            " out · " + message.elapsed.toFixed(1) + "s"
        );
        break;
      case "context": {
        const pct = message.limit ? Math.round((100 * message.used) / message.limit) : 0;
        addBubble("meta", pct + "% context used");
        break;
      }
      case "compactStart":
        addBubble("meta", "Compacting context…");
        break;
      case "compactEnd":
        addBubble("meta", "Compacted — " + message.before + " → " + message.after + " messages");
        break;
      case "retry":
        addBubble("meta", "Retrying (" + message.attempt + "/3) — " + message.error);
        break;
      case "done":
        if (!assistantBubble || !assistantBubble.textContent) {
          addBubble("assistant", message.text);
        }
        assistantBubble = null;
        setBusy(false);
        break;
      case "error":
        addBubble("error", message.message);
        setBusy(false);
        break;
      case "processExit":
        addBubble("error", "pycodeloop serve exited (code " + message.code + ")");
        setBusy(false);
        break;
      case "sessionReset":
        messagesEl.innerHTML = "";
        assistantBubble = null;
        break;
    }
  });
})();
