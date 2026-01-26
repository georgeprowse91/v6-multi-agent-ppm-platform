const sessionInfo = document.getElementById("session-info");
const statusOutput = document.getElementById("status-output");
const workflowOutput = document.getElementById("workflow-output");

const setStatus = (element, message, ok = true) => {
  element.textContent = message;
  element.className = ok ? "status ok" : "status error";
};

const loadSession = async () => {
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

const logout = async () => {
  await fetch("/logout", { method: "POST" });
  await loadSession();
  statusOutput.textContent = "";
  workflowOutput.textContent = "";
};

const loadStatus = async () => {
  const response = await fetch("/api/status");
  if (!response.ok) {
    const error = await response.json();
    setStatus(sessionInfo, error.detail || "Authentication required.", false);
    return;
  }
  const payload = await response.json();
  statusOutput.textContent = JSON.stringify(payload, null, 2);
};

const startWorkflow = async () => {
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

document.getElementById("login").addEventListener("click", login);
document.getElementById("logout").addEventListener("click", logout);
document.getElementById("load-status").addEventListener("click", loadStatus);
document.getElementById("start-workflow").addEventListener("click", startWorkflow);

loadSession();
