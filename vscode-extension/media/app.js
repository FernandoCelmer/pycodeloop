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
