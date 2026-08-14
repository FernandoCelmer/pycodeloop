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
