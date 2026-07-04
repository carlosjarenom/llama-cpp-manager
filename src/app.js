// ── llama.cpp Model Manager ──────────────────────────────────────

const { invoke } = await import("@tauri-apps/api/core");

let models = [];
let refreshTimer = null;
let logModel = null; // currently viewing logs for this model

// ── Backend helpers ──────────────────────────────────────────────

async function loadModels() {
  models = await invoke("list_models");
}

async function checkService(service) {
  return await invoke("check_service", { service });
}

async function controlService(service, action) {
  return await invoke("control_service", { service, action });
}

async function healthCheck(port) {
  return await invoke("health_check", { port });
}

async function getLogs(service, lines = 50) {
  return await invoke("get_logs", { service, lines: lines ?? 50 });
}

// ── Status ───────────────────────────────────────────────────────

function statusBadge(status, health) {
  if (status === "active" && health === "ok")
    return '<span class="badge active">● Activo</span>';
  if (status === "active" && health === "error")
    return '<span class="badge degraded">● Activo (sin respuesta API)</span>';
  if (status === "inactive")
    return '<span class="badge inactive">○ Parado</span>';
  return '<span class="badge error">● Error</span>';
}

// ── Card rendering ───────────────────────────────────────────────

function buildCard(m) {
  const div = document.createElement("div");
  div.className = "card";
  div.dataset.key = m.key;

  const sizeMb = (m.model_path.length > 0) ? "" : "";

  div.innerHTML = `
    <div class="card-top">
      <div class="card-icon" style="background:${m.color}22; color:${m.color}">
        🧠
      </div>
      <div class="card-meta">
        <h2>${m.name}</h2>
        <div class="card-sub">Puerto ${m.port} · ${m.service}</div>
      </div>
      <div class="card-status">
        <div class="status-badge" id="badge-${m.key}">—</div>
        <div class="status-health" id="health-${m.key}"></div>
      </div>
    </div>
    <div class="card-path">
      <code title="${m.model_path}">${basename(m.model_path)}</code>
    </div>
    <div class="card-actions">
      <button class="btn btn-start" data-action="start" data-service="${m.service}" data-key="${m.key}">▶ Iniciar</button>
      <button class="btn btn-stop" data-action="stop" data-service="${m.service}" data-key="${m.key}">⏹ Parar</button>
      <button class="btn btn-restart" data-action="restart" data-service="${m.service}" data-key="${m.key}">↻ Reiniciar</button>
      <button class="btn btn-log" data-key="${m.key}" data-service="${m.service}">📋 Logs</button>
    </div>
  `;
  return div;
}

function basename(path) {
  const parts = path.split("/");
  const name = parts[parts.length - 1];
  return name.length > 40 ? "…" + name.slice(-37) : name;
}

// ── Actions ──────────────────────────────────────────────────────

async function doAction(service, action, key) {
  const card = document.querySelector(`.card[data-key="${key}"]`);
  const btn = card.querySelector(`[data-action="${action}"]`);
  const orig = btn.textContent;
  btn.disabled = true;
  btn.textContent = "⏳ …";

  try {
    const result = await controlService(service, action);
    if (result.ok === "false") {
      btn.textContent = "❌ Error";
      setTimeout(() => { btn.textContent = orig; btn.disabled = false; }, 2000);
    }
  } catch (e) {
    btn.textContent = "❌ Error";
    console.error(e);
    setTimeout(() => { btn.textContent = orig; btn.disabled = false; }, 2000);
  }

  await refreshAll();
}

async function viewLogs(service, key) {
  logModel = { service, key };

  document.getElementById("log-section").classList.remove("hidden");
  document.getElementById("log-title").textContent = `📋 Logs: ${service}`;
  const output = document.getElementById("log-output");
  output.textContent = "Cargando…";

  try {
    const log = await getLogs(service, 80);
    output.textContent = log || "(sin logs)";
  } catch (e) {
    output.textContent = `Error al cargar logs: ${e}`;
  }
}

// ── Refresh cycle ────────────────────────────────────────────────

async function refreshAll() {
  for (const m of models) {
    const card = document.querySelector(`.card[data-key="${m.key}"]`);
    if (!card) continue;

    // Service status
    let svc;
    try {
      svc = await checkService(m.service);
    } catch {
      svc = { status: "error" };
    }

    const badgeEl = document.getElementById(`badge-${m.key}`);
    const healthEl = document.getElementById(`health-${m.key}`);
    badgeEl.outerHTML = statusBadge(svc.status || "unknown", "");
    badgeEl = document.getElementById(`badge-${m.key}`);

    // Health check (only if service is active)
    if (svc.status === "active") {
      let hc;
      try {
        hc = await healthCheck(m.port);
      } catch {
        hc = { status: "error" };
      }
      healthEl.textContent = hc.status === "ok"
        ? "✓ API responde"
        : `✕ API no responde (puerto ${m.port})`;
      healthEl.className = `status-health ${hc.status === "ok" ? "ok" : "err"}`;
    } else {
      healthEl.textContent = "";
    }

    // Button states
    const btns = card.querySelectorAll(".card-actions .btn");
    btns.forEach(b => {
      const a = b.dataset.action;
      if (a === "start") b.disabled = svc.status === "active";
      else if (a === "stop") b.disabled = svc.status !== "active";
      else if (a === "restart") b.disabled = svc.status !== "active";
      else if (a === undefined) b.disabled = false; // log button
    });
  }

  // Status bar
  const now = new Date().toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  document.getElementById("status-bar").textContent = `Actualizado: ${now}`;

  // Refresh log view if open
  if (logModel) {
    const output = document.getElementById("log-output");
    try {
      output.textContent = await getLogs(logModel.service, 80);
    } catch {}
  }
}

// ── Init ─────────────────────────────────────────────────────────

async function init() {
  await loadModels();

  const container = document.getElementById("model-cards");
  container.innerHTML = "";
  for (const m of models) {
    container.appendChild(buildCard(m));
  }

  // Delegate button clicks
  container.addEventListener("click", async (e) => {
    const btn = e.target.closest("button[data-action]");
    if (btn) {
      await doAction(btn.dataset.service, btn.dataset.action, btn.dataset.key);
      return;
    }
    const logBtn = e.target.closest("button[data-service][data-key]:not([data-action])");
    if (logBtn) {
      await viewLogs(logBtn.dataset.service, logBtn.dataset.key);
    }
  });

  // Log panel actions
  document.getElementById("log-refresh").addEventListener("click", async () => {
    if (logModel) {
      const output = document.getElementById("log-output");
      output.textContent = "Cargando…";
      try {
        output.textContent = await getLogs(logModel.service, 80);
      } catch (e) {
        output.textContent = `Error: ${e}`;
      }
    }
  });
  document.getElementById("log-close").addEventListener("click", () => {
    document.getElementById("log-section").classList.add("hidden");
    logModel = null;
  });

  await refreshAll();
  refreshTimer = setInterval(refreshAll, 5000);
}

init();
