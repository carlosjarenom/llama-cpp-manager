// ── llama.cpp Model Manager — Frontend ──────────────────────────

const MODELS = [
  {
    key: "27b",
    name: "Qwen3.6-27B",
    service: "llama-cpp-server",
    port: "8002",
    color: "#0099e6",
  },
  {
    key: "35b",
    name: "Qwen3.6-35B",
    service: "llama-cpp-server-35b",
    port: "8003",
    color: "#e67300",
  },
];

let refreshTimer = null;

// ── Backend calls via Tauri ─────────────────────────────────────
async function invokeTauri(cmd, args) {
  try {
    // Import Tauri invoke dynamically
    const { invoke } = await import("@tauri-apps/api/core");
    return await invoke(cmd, { command: cmd, args: args });
  } catch (err) {
    console.error(`Tauri ${cmd} failed:`, err);
    return { ok: false, error: String(err) };
  }
}

async function getServiceStatus(service) {
  const result = await invokeTauri("get_service_status", { service });
  if (!result.ok) return "not-found";
  return result.status || "not-found";
}

async function executeAction(service, action) {
  return invokeTauri("execute_service_action", { service, action });
}

// ── UI ──────────────────────────────────────────────────────────
function formatStatus(status, detail) {
  if (status === "active") return "✅ Running" + (detail ? ` (${detail})` : "");
  if (status === "inactive") return "⏹️ Stopped";
  return "❌ Not found";
}

function setButtonsState(btns, status) {
  btns.start.disabled = status !== "inactive";
  btns.stop.disabled = status !== "active";
  btns.restart.disabled = status === "not-found";
}

function buildCard(model) {
  const card = document.createElement("div");
  card.className = "card";
  card.id = `card-${model.key}`;

  card.innerHTML = `
    <div class="card-header">
      <div class="card-icon">🧠</div>
      <div class="card-info">
        <div class="card-name">${model.name}</div>
        <div class="card-port">Port ${model.port}</div>
      </div>
    </div>
    <div class="card-status" id="status-${model.key}">Loading…</div>
    <div class="card-btns">
      <button class="btn-start" id="start-${model.key}">▶ Start</button>
      <button class="btn-stop" id="stop-${model.key}">⏹ Stop</button>
      <button class="btn-restart" id="restart-${model.key}">↻ Restart</button>
      <button class="btn-log" id="log-${model.key}">📄 Log</button>
    </div>
  `;

  const btns = {
    start: card.querySelector(`#start-${model.key}`),
    stop: card.querySelector(`#stop-${model.key}`),
    restart: card.querySelector(`#restart-${model.key}`),
    log: card.querySelector(`#log-${model.key}`),
  };

  card.querySelector(`#start-${model.key}`).addEventListener("click", () => handleAction(model, "start", btns));
  card.querySelector(`#stop-${model.key}`).addEventListener("click", () => handleAction(model, "stop", btns));
  card.querySelector(`#restart-${model.key}`).addEventListener("click", () => handleAction(model, "restart", btns));
  card.querySelector(`#log-${model.key}`).addEventListener("click", () => handleLog(model));

  return card;
}

async function handleAction(model, action, btns) {
  if (action === "restart") {
    btns.restart.textContent = "↻ Restarting…";
    btns.restart.disabled = true;
  }

  await executeAction(model.service, action);
  await updateCardStatus(model);
  setButtonsState(btns, model._currentStatus || "not-found");

  if (action === "restart") {
    btns.restart.textContent = "↻ Restart";
    btns.restart.disabled = false;
  }
}

async function handleLog(model) {
  await invokeTauri("open_service_log", { service: model.service });
}

async function updateCardStatus(model) {
  const status = await getServiceStatus(model.service);
  model._currentStatus = status;
  const card = document.getElementById(`card-${model.key}`);
  const statusEl = card.querySelector(`#status-${model.key}`);
  statusEl.textContent = formatStatus(status);
}

async function refreshAll() {
  for (const model of MODELS) {
    await updateCardStatus(model);
  }

  // Set button states
  for (const model of MODELS) {
    const card = document.getElementById(`card-${model.key}`);
    const btns = {
      start: card.querySelector(".btn-start"),
      stop: card.querySelector(".btn-stop"),
      restart: card.querySelector(".btn-restart"),
    };
    setButtonsState(btns, model._currentStatus || "not-found");
  }

  // Update status bar
  const now = new Date();
  document.getElementById("status-bar").textContent =
    `Last update: ${now.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}`;
}

// ── Init ────────────────────────────────────────────────────────
async function init() {
  const container = document.getElementById("cards");

  for (const model of MODELS) {
    const card = buildCard(model);
    container.appendChild(card);
  }

  await refreshAll();

  // Auto-refresh every 5 seconds
  refreshTimer = setInterval(refreshAll, 5000);
}

init();
