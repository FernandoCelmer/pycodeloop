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
