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
