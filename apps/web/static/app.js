const setStatus = (element, message, ok = true) => {
  element.textContent = message;
  element.classList.remove("ok", "error");
  element.classList.add(ok ? "ok" : "error");
};

const loadSession = async (sessionInfo) => {
  const response = await fetch("/session");
  const payload = await response.json();
  if (!payload.authenticated) {
    setStatus(sessionInfo, "Not signed in.", false);
    return payload;
  }
  setStatus(
    sessionInfo,
    `Signed in as ${payload.subject || "user"} (tenant: ${payload.tenant_id})`,
  );
  return payload;
};

const login = async () => {
  window.location.href = "/login";
};

const logout = async (sessionInfo, statusOutput, workflowOutput) => {
  await fetch("/logout", { method: "POST" });
  await loadSession(sessionInfo);
  if (statusOutput) {
    statusOutput.textContent = "";
  }
  if (workflowOutput) {
    workflowOutput.textContent = "";
  }
};

const loadStatus = async (sessionInfo, statusOutput) => {
  const response = await fetch("/api/status");
  if (!response.ok) {
    const error = await response.json();
    setStatus(sessionInfo, error.detail || "Authentication required.", false);
    return;
  }
  const payload = await response.json();
  statusOutput.textContent = JSON.stringify(payload, null, 2);
};

const startWorkflow = async (workflowOutput) => {
  const response = await fetch("/api/workflows/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      workflow_id: document.getElementById("workflow-id").value,
    }),
  });
  if (!response.ok) {
    const error = await response.json();
    workflowOutput.textContent = JSON.stringify(error, null, 2);
    return;
  }
  const payload = await response.json();
  workflowOutput.textContent = JSON.stringify(payload, null, 2);
};

const renderWorkspaceShell = () => {
  document.body.classList.add("workspace-body");
  document.body.innerHTML = `
    <div class="workspace-shell">
      <aside class="workspace-nav" aria-label="Workspace navigation">
        <div class="workspace-brand">
          <span>PPM Workspace</span>
        </div>
        <div class="workspace-session status" id="workspace-session">
          Checking session...
        </div>
        <div class="workspace-section">
          <h3>Methodology</h3>
          <ul>
            <li>Intake</li>
            <li>Planning</li>
            <li>Execution</li>
            <li>Review</li>
          </ul>
        </div>
        <div class="workspace-section">
          <h3>Monitoring</h3>
          <ul>
            <li>Signals</li>
            <li>Health</li>
            <li>Risks</li>
            <li>Dependencies</li>
          </ul>
        </div>
      </aside>
      <main class="workspace-main">
        <div class="workspace-tabs" role="tablist" aria-label="Canvas tabs">
          <button class="workspace-tab is-active" role="tab" aria-selected="true">
            Document
          </button>
          <button class="workspace-tab" role="tab" aria-selected="false">Tree</button>
          <button class="workspace-tab" role="tab" aria-selected="false">
            Timeline
          </button>
          <button class="workspace-tab" role="tab" aria-selected="false">
            Spreadsheet
          </button>
          <button class="workspace-tab" role="tab" aria-selected="false">
            Dashboard
          </button>
        </div>
        <section class="workspace-canvas" aria-live="polite">
          <p>Select a canvas tab to view its workspace.</p>
        </section>
      </main>
      <aside class="workspace-assistant" aria-label="Assistant panel">
        <h3>Assistant</h3>
        <p>Assistant will provide guidance here.</p>
      </aside>
    </div>
  `;
};

const initWorkspace = () => {
  renderWorkspaceShell();
  const sessionInfo = document.getElementById("workspace-session");
  loadSession(sessionInfo);
  const tabs = Array.from(document.querySelectorAll(".workspace-tab"));
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((item) => {
        item.classList.remove("is-active");
        item.setAttribute("aria-selected", "false");
      });
      tab.classList.add("is-active");
      tab.setAttribute("aria-selected", "true");
    });
  });
};

const initConsole = () => {
  const sessionInfo = document.getElementById("session-info");
  const statusOutput = document.getElementById("status-output");
  const workflowOutput = document.getElementById("workflow-output");

  document.getElementById("login").addEventListener("click", login);
  document
    .getElementById("logout")
    .addEventListener("click", () =>
      logout(sessionInfo, statusOutput, workflowOutput),
    );
  document
    .getElementById("load-status")
    .addEventListener("click", () => loadStatus(sessionInfo, statusOutput));
  document
    .getElementById("start-workflow")
    .addEventListener("click", () => startWorkflow(workflowOutput));

  loadSession(sessionInfo);
};

if (window.location.pathname === "/workspace") {
  initWorkspace();
} else {
  initConsole();
}
