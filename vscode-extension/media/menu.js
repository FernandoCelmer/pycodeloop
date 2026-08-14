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
