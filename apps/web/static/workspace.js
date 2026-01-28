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
        <div class="workspace-section" id="methodology-nav">
          <h3>Methodology</h3>
        </div>
        <div class="workspace-section" id="monitoring-nav">
          <h3>Monitoring</h3>
        </div>
      </aside>
      <main class="workspace-main">
        <div class="workspace-tabs" role="tablist" aria-label="Canvas tabs">
          <button class="workspace-tab is-active" role="tab" aria-selected="true" data-canvas-tab="document">
            Document
          </button>
          <button class="workspace-tab" role="tab" aria-selected="false" data-canvas-tab="tree">Tree</button>
          <button class="workspace-tab" role="tab" aria-selected="false" data-canvas-tab="timeline">
            Timeline
          </button>
          <button class="workspace-tab" role="tab" aria-selected="false" data-canvas-tab="spreadsheet">
            Spreadsheet
          </button>
          <button class="workspace-tab" role="tab" aria-selected="false" data-canvas-tab="dashboard">
            Dashboard
          </button>
        </div>
        <section class="workspace-canvas" aria-live="polite">
          <p>Loading document canvas...</p>
        </section>
      </main>
      <aside class="workspace-assistant" aria-label="Activity guidance panel">
        <h3>Assistant</h3>
        <div id="activity-guidance">
          <p>Select an activity to view guidance.</p>
        </div>
      </aside>
    </div>
  `;
};

const initWorkspace = () => {
  renderWorkspaceShell();
  const sessionInfo = document.getElementById("workspace-session");
  loadSession(sessionInfo);
  const searchParams = new URLSearchParams(window.location.search);
  const projectId = searchParams.get("project_id") || "default";
  const urlMethodology = searchParams.get("methodology");
  const tabs = Array.from(document.querySelectorAll(".workspace-tab"));
  let workspaceState = null;
  let activityIndex = new Map();
  const documentState = {
    list: [],
    selected: null,
  };
  const timelineState = {
    milestones: [],
    editingId: null,
    exportPayload: null,
  };

  const setActiveTab = (targetTab) => {
    tabs.forEach((item) => {
      const isActive = item === targetTab;
      item.classList.toggle("is-active", isActive);
      item.setAttribute("aria-selected", isActive ? "true" : "false");
    });
  };

  const buildActivityIndex = (summary) => {
    const index = new Map();
    summary.stages.forEach((stage) => {
      stage.activities.forEach((activity) => {
        index.set(activity.id, { ...activity, stageId: stage.id });
      });
    });
    summary.monitoring.forEach((activity) => {
      index.set(activity.id, { ...activity, stageId: null });
    });
    return index;
  };

  const renderNavigation = (summary, currentActivityId) => {
    const methodologyNav = document.getElementById("methodology-nav");
    const monitoringNav = document.getElementById("monitoring-nav");
    const stageMarkup = summary.stages
      .map((stage) => {
        const activitiesMarkup = stage.activities
          .map((activity) => {
            const statusIcon = activity.completed
              ? "✅"
              : activity.access.allowed
                ? "🔓"
                : "🔒";
            const isSelected = activity.id === currentActivityId;
            return `
              <li>
                <button
                  class="workspace-activity${isSelected ? " is-selected" : ""}"
                  data-activity-id="${activity.id}"
                  data-stage-id="${stage.id}"
                  data-canvas-tab="${activity.recommended_canvas_tab}"
                >
                  ${statusIcon} ${activity.name}
                </button>
              </li>
            `;
          })
          .join("");
        return `
          <div class="workspace-stage" data-stage-id="${stage.id}">
            <div class="workspace-stage-header">
              <span>${stage.name}</span>
              <span>${stage.progress.percent}%</span>
            </div>
            <ul>${activitiesMarkup}</ul>
          </div>
        `;
      })
      .join("");

    methodologyNav.innerHTML = `
      <h3>${summary.name}</h3>
      ${stageMarkup}
    `;

    const monitoringMarkup = summary.monitoring
      .map((activity) => {
        const isSelected = activity.id === currentActivityId;
        return `
          <li>
            <button
              class="workspace-activity${isSelected ? " is-selected" : ""}"
              data-activity-id="${activity.id}"
              data-canvas-tab="${activity.recommended_canvas_tab}"
            >
              🔓 ${activity.name}
            </button>
          </li>
        `;
      })
      .join("");
    monitoringNav.innerHTML = `
      <h3>Monitoring</h3>
      <ul>${monitoringMarkup}</ul>
    `;
  };

  const renderGuidancePanel = (payload) => {
    const guidance = document.getElementById("activity-guidance");
    const activityId = payload.current_activity_id;
    const selectedActivity = payload.selected_activity;
    if (!activityId || !selectedActivity) {
      guidance.innerHTML = "<p>Select an activity to view guidance.</p>";
      return;
    }
    const activity = activityIndex.get(activityId) || selectedActivity;
    const access = payload.gating.current_activity_access;
    const blocked = access && !access.allowed;
    const missingList = blocked
      ? access.missing_prereqs
          .map((id) => activityIndex.get(id)?.name || id)
          .map((name) => `<li>${name}</li>`)
          .join("")
      : "";
    const nextRequiredId = payload.gating.next_required_activity_id;
    const showNextRequired = Boolean(nextRequiredId && activityIndex.has(nextRequiredId));
    const assistantPrompts = selectedActivity.assistant_prompts || [];
    const promptChips = assistantPrompts.length
      ? assistantPrompts
          .map(
            (prompt) => `
              <button type="button" class="assistant-chip" data-prompt="${prompt}">
                ${prompt}
              </button>
            `,
          )
          .join("")
      : "<p class=\"assistant-empty\">No prompts available for this activity.</p>";

    guidance.innerHTML = `
      <div class="workspace-guidance">
        <div class="assistant-context">
          <h4>${selectedActivity.name}</h4>
          <p class="assistant-label">What this is for</p>
          <p>${selectedActivity.description}</p>
        </div>
        ${
          blocked
            ? `
              <div class="workspace-blocked">
                <strong>Blocked because prerequisites are incomplete:</strong>
                <ul>${missingList}</ul>
              </div>
            `
            : ""
        }
        <div class="assistant-prompt-box">
          <label for="assistant-prompt">Prompt</label>
          <textarea id="assistant-prompt" rows="4" placeholder="Select a prompt chip or write your own."></textarea>
        </div>
        <div class="assistant-chips">
          <p class="assistant-label">Next-best-action prompts</p>
          <div class="assistant-chip-list">
            ${promptChips}
          </div>
        </div>
        <div class="assistant-actions">
          <button type="button" id="assistant-copy">Copy</button>
          <button type="button" id="assistant-clear">Clear</button>
        </div>
        <p class="assistant-status" id="assistant-status" role="status" aria-live="polite"></p>
        <div class="workspace-guidance-actions">
          ${
            showNextRequired
              ? `<button type="button" id="next-required" data-activity-id="${nextRequiredId}">
                  Go to next required activity
                </button>`
              : ""
          }
          ${
            selectedActivity.category === "methodology"
              ? `<button type="button" id="mark-complete" data-activity-id="${activity.id}">
                  Mark activity complete
                </button>`
              : ""
          }
        </div>
      </div>
    `;
  };

  const postSelection = async (payload) => {
    const response = await fetch(`/api/workspace/${projectId}/select`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      return null;
    }
    return response.json();
  };

  const renderDocumentList = () => {
    const listElement = document.getElementById("document-list");
    const statusElement = document.getElementById("document-list-status");
    if (!listElement || !statusElement) {
      return;
    }
    if (!documentState.list.length) {
      listElement.innerHTML = "";
      statusElement.textContent = "No documents yet.";
      return;
    }
    statusElement.textContent = `${documentState.list.length} document(s).`;
    listElement.innerHTML = documentState.list
      .map(
        (doc) => `
          <li>
            <button type="button" class="document-list-item" data-document-id="${doc.document_id}">
              <span class="document-name">${doc.name}</span>
              <span class="document-meta">
                <span>${doc.classification}</span>
                <span>${doc.created_at}</span>
                <span>Retain until ${doc.retention_until}</span>
              </span>
            </button>
          </li>
        `,
      )
      .join("");

    document.querySelectorAll(".document-list-item").forEach((button) => {
      button.addEventListener("click", async () => {
        const documentId = button.dataset.documentId;
        if (!documentId) {
          return;
        }
        await loadDocumentDetail(documentId);
      });
    });
  };

  const renderDocumentDetail = (doc) => {
    const detailElement = document.getElementById("document-detail");
    if (!detailElement) {
      return;
    }
    if (!doc) {
      detailElement.innerHTML = "<p>Select a document to view details.</p>";
      return;
    }
    const advisories = (doc.advisories || []).map((item) => `<li>${item}</li>`).join("");
    const metadata = doc.metadata ? JSON.stringify(doc.metadata, null, 2) : "{}";
    detailElement.innerHTML = `
      <div class="document-detail-card">
        <h3>${doc.name}</h3>
        <dl>
          <div>
            <dt>Classification</dt>
            <dd>${doc.classification}</dd>
          </div>
          <div>
            <dt>Retention days</dt>
            <dd>${doc.retention_days}</dd>
          </div>
          <div>
            <dt>Created</dt>
            <dd>${doc.created_at}</dd>
          </div>
          <div>
            <dt>Retain until</dt>
            <dd>${doc.retention_until}</dd>
          </div>
        </dl>
        <div>
          <h4>Advisories</h4>
          ${advisories ? `<ul>${advisories}</ul>` : "<p>No advisories.</p>"}
        </div>
        <div>
          <h4>Metadata</h4>
          <pre>${metadata}</pre>
        </div>
        <div>
          <h4>Content preview</h4>
          <pre>${doc.content || ""}</pre>
        </div>
      </div>
    `;
  };

  const setDocumentMessage = (message, isError = false) => {
    const messageElement = document.getElementById("document-message");
    if (!messageElement) {
      return;
    }
    messageElement.textContent = message;
    messageElement.classList.toggle("is-error", isError);
  };

  const setPolicyMessage = (title, items = []) => {
    const policyElement = document.getElementById("document-policy");
    if (!policyElement) {
      return;
    }
    if (!title) {
      policyElement.innerHTML = "";
      return;
    }
    const list = items.length ? `<ul>${items.map((item) => `<li>${item}</li>`).join("")}</ul>` : "";
    policyElement.innerHTML = `<strong>${title}</strong>${list}`;
  };

  const loadDocumentList = async () => {
    const statusElement = document.getElementById("document-list-status");
    if (statusElement) {
      statusElement.textContent = "Loading documents...";
    }
    const response = await fetch("/api/document-canvas/documents");
    if (!response.ok) {
      if (statusElement) {
        statusElement.textContent = "Unable to load documents.";
      }
      return;
    }
    const payload = await response.json();
    documentState.list = payload
      .slice()
      .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    renderDocumentList();
    if (documentState.selected) {
      const match = documentState.list.find(
        (item) => item.document_id === documentState.selected.document_id,
      );
      if (match) {
        documentState.selected = { ...documentState.selected, ...match };
      }
    }
  };

  const loadDocumentDetail = async (documentId) => {
    const response = await fetch(`/api/document-canvas/documents/${documentId}`);
    if (!response.ok) {
      setDocumentMessage("Unable to load document details.", true);
      return;
    }
    const payload = await response.json();
    documentState.selected = payload;
    renderDocumentDetail(payload);
  };

  const renderDocumentCanvas = () => {
    const canvas = document.querySelector(".workspace-canvas");
    if (!canvas) {
      return;
    }
    canvas.innerHTML = `
      <div class="document-canvas">
        <section class="document-form-card">
          <h3>Create document</h3>
          <form id="document-create-form">
            <label>
              Name
              <input type="text" id="document-name" required />
            </label>
            <label>
              Content
              <textarea id="document-content" rows="6" required></textarea>
            </label>
            <label>
              Classification
              <select id="document-classification" required>
                <option value="">Select...</option>
                <option value="internal">Internal</option>
                <option value="confidential">Confidential</option>
                <option value="restricted">Restricted</option>
              </select>
            </label>
            <label>
              Retention days
              <input type="number" id="document-retention" min="1" max="3650" value="90" required />
            </label>
            <label>
              Metadata (JSON)
              <textarea id="document-metadata" rows="4" placeholder='{"source": "..."}'></textarea>
            </label>
            <button type="submit">Create document</button>
            <p class="document-message" id="document-message" role="status" aria-live="polite"></p>
            <div class="document-policy" id="document-policy"></div>
          </form>
        </section>
        <section class="document-columns">
          <div class="document-list-panel">
            <div class="document-list-header">
              <h3>Documents</h3>
              <p id="document-list-status" class="document-list-status"></p>
            </div>
            <ul id="document-list" class="document-list"></ul>
          </div>
          <div class="document-detail" id="document-detail">
            <p>Select a document to view details.</p>
          </div>
        </section>
      </div>
    `;

    const form = document.getElementById("document-create-form");
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      setDocumentMessage("");
      setPolicyMessage("");

      const name = document.getElementById("document-name").value.trim();
      const content = document.getElementById("document-content").value.trim();
      const classification = document.getElementById("document-classification").value;
      const retentionDays = Number(
        document.getElementById("document-retention").value,
      );
      const metadataValue = document.getElementById("document-metadata").value.trim();

      if (!name || !content || !classification) {
        setDocumentMessage("Name, content, and classification are required.", true);
        return;
      }

      let metadata = {};
      if (metadataValue) {
        try {
          metadata = JSON.parse(metadataValue);
        } catch (error) {
          setDocumentMessage("Metadata must be valid JSON.", true);
          return;
        }
      }

      const response = await fetch("/api/document-canvas/documents", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          content,
          classification,
          retention_days: retentionDays,
          metadata,
        }),
      });

      const payload = await response.json();
      if (!response.ok) {
        if (response.status === 403) {
          const reasons =
            payload?.detail?.reasons || payload?.reasons || ["Policy denied."];
          setDocumentMessage("Upload blocked.", true);
          setPolicyMessage("Policy reasons", reasons);
          return;
        }
        setDocumentMessage(payload?.detail || "Unable to create document.", true);
        return;
      }

      const advisories = payload.advisories || [];
      setDocumentMessage("Created.");
      setPolicyMessage(advisories.length ? "Advisories" : "", advisories);
      document.getElementById("document-name").value = "";
      document.getElementById("document-content").value = "";
      document.getElementById("document-classification").value = "";
      document.getElementById("document-metadata").value = "";
      documentState.selected = payload;
      renderDocumentDetail(payload);
      await loadDocumentList();
    });

    loadDocumentList();
  };

  const setTimelineMessage = (message, isError = false) => {
    const messageElement = document.getElementById("timeline-message");
    if (!messageElement) {
      return;
    }
    messageElement.textContent = message;
    messageElement.classList.toggle("is-error", isError);
  };

  const renderTimelineList = () => {
    const listElement = document.getElementById("timeline-list");
    const emptyElement = document.getElementById("timeline-empty");
    if (!listElement) {
      return;
    }
    listElement.innerHTML = "";
    if (!timelineState.milestones.length) {
      if (emptyElement) {
        emptyElement.classList.remove("is-hidden");
      }
      return;
    }
    if (emptyElement) {
      emptyElement.classList.add("is-hidden");
    }
    timelineState.milestones.forEach((milestone) => {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${milestone.date}</td>
        <td>${milestone.title}</td>
        <td class="timeline-status ${milestone.status}">${milestone.status.replace("_", " ")}</td>
        <td>${milestone.owner || "—"}</td>
        <td class="timeline-actions">
          <button type="button" data-action="edit">Edit</button>
          <button type="button" data-action="delete">Delete</button>
        </td>
      `;
      row.querySelectorAll("button").forEach((button) => {
        button.addEventListener("click", async () => {
          const action = button.dataset.action;
          if (action === "edit") {
            timelineState.editingId = milestone.milestone_id;
            const form = document.getElementById("timeline-form");
            if (form) {
              form.dataset.editing = "true";
            }
            document.getElementById("timeline-title").value = milestone.title;
            document.getElementById("timeline-date").value = milestone.date;
            document.getElementById("timeline-status").value = milestone.status;
            document.getElementById("timeline-owner").value = milestone.owner || "";
            document.getElementById("timeline-notes").value = milestone.notes || "";
            document.getElementById("timeline-submit").textContent = "Save changes";
            document.getElementById("timeline-cancel").classList.remove("is-hidden");
          }
          if (action === "delete") {
            const confirmed = window.confirm(
              `Delete milestone \"${milestone.title}\"?`,
            );
            if (!confirmed) {
              return;
            }
            const response = await fetch(
              `/api/timeline/${projectId}/milestones/${milestone.milestone_id}`,
              { method: "DELETE" },
            );
            if (!response.ok) {
              setTimelineMessage("Unable to delete milestone.", true);
              return;
            }
            setTimelineMessage("Milestone deleted.");
            await loadTimeline();
          }
        });
      });
      listElement.appendChild(row);
    });
  };

  const loadTimeline = async () => {
    const statusElement = document.getElementById("timeline-list-status");
    if (statusElement) {
      statusElement.textContent = "Loading milestones...";
    }
    const response = await fetch(`/api/timeline/${projectId}`);
    if (!response.ok) {
      if (statusElement) {
        statusElement.textContent = "Unable to load milestones.";
      }
      return;
    }
    const payload = await response.json();
    timelineState.milestones = payload.milestones || [];
    if (statusElement) {
      statusElement.textContent = `${timelineState.milestones.length} milestones`;
    }
    renderTimelineList();
  };

  const resetTimelineForm = () => {
    timelineState.editingId = null;
    const form = document.getElementById("timeline-form");
    if (form) {
      form.dataset.editing = "false";
    }
    document.getElementById("timeline-title").value = "";
    document.getElementById("timeline-date").value = "";
    document.getElementById("timeline-status").value = "planned";
    document.getElementById("timeline-owner").value = "";
    document.getElementById("timeline-notes").value = "";
    document.getElementById("timeline-submit").textContent = "Add milestone";
    document.getElementById("timeline-cancel").classList.add("is-hidden");
  };

  const renderTimelineCanvas = () => {
    const canvas = document.querySelector(".workspace-canvas");
    if (!canvas) {
      return;
    }
    canvas.innerHTML = `
      <div class="timeline-canvas">
        <section class="timeline-form-card">
          <h3>Add milestone</h3>
          <form id="timeline-form" data-editing="false">
            <label>
              Title
              <input type="text" id="timeline-title" required />
            </label>
            <label>
              Date
              <input type="date" id="timeline-date" required />
            </label>
            <label>
              Status
              <select id="timeline-status" required>
                <option value="planned">Planned</option>
                <option value="at_risk">At risk</option>
                <option value="complete">Complete</option>
              </select>
            </label>
            <label>
              Owner
              <input type="text" id="timeline-owner" />
            </label>
            <label>
              Notes
              <textarea id="timeline-notes" rows="3"></textarea>
            </label>
            <div class="timeline-form-actions">
              <button type="submit" id="timeline-submit">Add milestone</button>
              <button type="button" class="secondary is-hidden" id="timeline-cancel">
                Cancel
              </button>
            </div>
            <p class="timeline-message" id="timeline-message" role="status" aria-live="polite"></p>
          </form>
        </section>
        <section class="timeline-list-panel">
          <div class="timeline-list-header">
            <h3>Milestones</h3>
            <p id="timeline-list-status" class="timeline-list-status"></p>
          </div>
          <p id="timeline-empty" class="timeline-empty">No milestones yet.</p>
          <table class="timeline-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Title</th>
                <th>Status</th>
                <th>Owner</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody id="timeline-list"></tbody>
          </table>
        </section>
        <section class="timeline-export">
          <div class="timeline-export-header">
            <h3>Export JSON</h3>
            <div class="timeline-export-actions">
              <button type="button" id="timeline-export">Refresh export</button>
              <button type="button" class="secondary" id="timeline-export-copy">Copy JSON</button>
            </div>
          </div>
          <pre id="timeline-export-output">{}</pre>
        </section>
      </div>
    `;

    const form = document.getElementById("timeline-form");
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      setTimelineMessage("");

      const title = document.getElementById("timeline-title").value.trim();
      const date = document.getElementById("timeline-date").value;
      const status = document.getElementById("timeline-status").value;
      const owner = document.getElementById("timeline-owner").value.trim();
      const notes = document.getElementById("timeline-notes").value.trim();

      if (!title || !date || !status) {
        setTimelineMessage("Title, date, and status are required.", true);
        return;
      }

      const payload = {
        title,
        date,
        status,
        owner: owner || null,
        notes: notes || null,
      };

      const isEditing = Boolean(timelineState.editingId);
      const url = isEditing
        ? `/api/timeline/${projectId}/milestones/${timelineState.editingId}`
        : `/api/timeline/${projectId}/milestones`;
      const response = await fetch(url, {
        method: isEditing ? "PATCH" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const responseBody = await response.json().catch(() => ({}));
      if (!response.ok) {
        setTimelineMessage(
          responseBody?.detail || "Unable to save milestone.",
          true,
        );
        return;
      }
      setTimelineMessage(isEditing ? "Milestone updated." : "Milestone added.");
      resetTimelineForm();
      await loadTimeline();
    });

    const cancelButton = document.getElementById("timeline-cancel");
    cancelButton.addEventListener("click", () => {
      resetTimelineForm();
    });

    const exportButton = document.getElementById("timeline-export");
    const exportOutput = document.getElementById("timeline-export-output");
    const exportCopy = document.getElementById("timeline-export-copy");

    const refreshExport = async () => {
      const response = await fetch(`/api/timeline/${projectId}/export`);
      if (!response.ok) {
        setTimelineMessage("Unable to export timeline.", true);
        return;
      }
      const payload = await response.json();
      timelineState.exportPayload = payload;
      if (exportOutput) {
        exportOutput.textContent = JSON.stringify(payload, null, 2);
      }
    };

    exportButton.addEventListener("click", refreshExport);
    exportCopy.addEventListener("click", async () => {
      if (!navigator.clipboard) {
        setTimelineMessage("Clipboard access is unavailable in this browser.", true);
        return;
      }
      const content = exportOutput?.textContent || "";
      if (!content.trim()) {
        setTimelineMessage("Nothing to copy yet.", true);
        return;
      }
      try {
        await navigator.clipboard.writeText(content);
        setTimelineMessage("Export copied to clipboard.");
      } catch (error) {
        setTimelineMessage("Unable to copy export.", true);
      }
    });

    resetTimelineForm();
    loadTimeline();
    refreshExport();
  };

  const renderPlaceholder = (tabName) => {
    const canvas = document.querySelector(".workspace-canvas");
    if (!canvas) {
      return;
    }
    canvas.innerHTML = `<p>${tabName} canvas is not available in this view.</p>`;
  };

  const renderCanvas = (tabName) => {
    if (tabName === "document") {
      renderDocumentCanvas();
      renderDocumentDetail(documentState.selected);
    } else if (tabName === "timeline") {
      renderTimelineCanvas();
    } else if (tabName) {
      renderPlaceholder(tabName);
    }
  };

  const updateWorkspaceUI = (payload) => {
    workspaceState = payload;
    activityIndex = buildActivityIndex(payload.methodology_map_summary);
    const currentTab = tabs.find(
      (tab) => tab.dataset.canvasTab === payload.current_canvas_tab,
    );
    if (currentTab) {
      setActiveTab(currentTab);
    }
    renderNavigation(payload.methodology_map_summary, payload.current_activity_id);
    renderGuidancePanel(payload);
    renderCanvas(payload.current_canvas_tab);
    attachActivityHandlers();
  };

  const attachActivityHandlers = () => {
    document.querySelectorAll(".workspace-activity").forEach((button) => {
      button.addEventListener("click", async () => {
        const activityId = button.dataset.activityId;
        if (!activityId || !activityIndex.has(activityId)) {
          return;
        }
        const activity = activityIndex.get(activityId);
        const response = await postSelection({
          current_canvas_tab: activity.recommended_canvas_tab,
          current_stage_id: activity.stageId,
          current_activity_id: activity.id,
          methodology: workspaceState?.methodology || urlMethodology || null,
        });
        if (response) {
          updateWorkspaceUI(response);
        }
      });
    });

    const nextRequiredButton = document.getElementById("next-required");
    if (nextRequiredButton) {
      nextRequiredButton.addEventListener("click", async () => {
        const targetId = nextRequiredButton.dataset.activityId;
        if (!targetId || !activityIndex.has(targetId)) {
          return;
        }
        const activity = activityIndex.get(targetId);
        const response = await postSelection({
          current_canvas_tab: activity.recommended_canvas_tab,
          current_stage_id: activity.stageId,
          current_activity_id: activity.id,
          methodology: workspaceState?.methodology || urlMethodology || null,
        });
        if (response) {
          updateWorkspaceUI(response);
        }
      });
    }

    const markCompleteButton = document.getElementById("mark-complete");
    if (markCompleteButton) {
      markCompleteButton.addEventListener("click", async () => {
        const activityId = markCompleteButton.dataset.activityId;
        if (!activityId) {
          return;
        }
        const response = await fetch(
          `/api/workspace/${projectId}/activity-completion`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ activity_id: activityId, completed: true }),
          },
        );
        if (!response.ok) {
          return;
        }
        const payload = await response.json();
        updateWorkspaceUI(payload);
      });
    }

    const promptBox = document.getElementById("assistant-prompt");
    const status = document.getElementById("assistant-status");
    const setAssistantStatus = (message, isError = false) => {
      if (!status) {
        return;
      }
      status.textContent = message;
      status.classList.toggle("is-error", isError);
    };

    document.querySelectorAll(".assistant-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        if (!promptBox) {
          return;
        }
        promptBox.value = chip.dataset.prompt || chip.textContent.trim();
        setAssistantStatus("");
      });
    });

    const copyButton = document.getElementById("assistant-copy");
    if (copyButton) {
      copyButton.addEventListener("click", async () => {
        if (!promptBox) {
          return;
        }
        const text = promptBox.value.trim();
        if (!text) {
          setAssistantStatus("Add a prompt before copying.", true);
          return;
        }
        if (!navigator.clipboard) {
          setAssistantStatus("Clipboard access is unavailable in this browser.", true);
          return;
        }
        try {
          await navigator.clipboard.writeText(promptBox.value);
          setAssistantStatus("Copied to clipboard.");
        } catch (error) {
          setAssistantStatus("Unable to copy to clipboard.", true);
        }
      });
    }

    const clearButton = document.getElementById("assistant-clear");
    if (clearButton) {
      clearButton.addEventListener("click", () => {
        if (!promptBox) {
          return;
        }
        promptBox.value = "";
        setAssistantStatus("Prompt cleared.");
      });
    }
  };

  const loadWorkspaceState = async () => {
    const response = await fetch(`/api/workspace/${projectId}`);
    if (!response.ok) {
      return;
    }
    const payload = await response.json();
    if (urlMethodology && payload.methodology !== urlMethodology) {
      const updated = await postSelection({
        current_canvas_tab: payload.current_canvas_tab,
        current_stage_id: payload.current_stage_id,
        current_activity_id: payload.current_activity_id,
        methodology: urlMethodology,
      });
      if (updated) {
        updateWorkspaceUI(updated);
        return;
      }
    }
    updateWorkspaceUI(payload);
  };

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      setActiveTab(tab);
      if (!workspaceState) {
        return;
      }
      postSelection({
        current_canvas_tab: tab.dataset.canvasTab,
        current_stage_id: workspaceState.current_stage_id,
        current_activity_id: workspaceState.current_activity_id,
        methodology: workspaceState.methodology,
      }).then((payload) => {
        if (payload) {
          updateWorkspaceUI(payload);
        }
      });
    });
  });

  loadWorkspaceState();
};

if (window.location.pathname === "/workspace") {
  initWorkspace();
}
