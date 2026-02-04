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
    <a class="skip-link" href="#workspace-main">Skip to main content</a>
    <div class="workspace-shell">
      <header class="workspace-topbar" role="banner">
        <div class="workspace-topbar-brand">PPM Workspace</div>
        <nav class="workspace-topbar-links" aria-label="Workspace links">
          <a class="workspace-top-link" href="/">Console</a>
        </nav>
        <button
          type="button"
          class="workspace-nav-toggle"
          id="workspace-nav-toggle"
          aria-label="Toggle workspace navigation"
          aria-controls="workspace-nav"
          aria-expanded="false"
        >
          Menu
        </button>
      </header>
      <button
        type="button"
        class="workspace-nav-overlay"
        id="workspace-nav-overlay"
        aria-label="Close navigation menu"
      ></button>
      <aside class="workspace-nav" id="workspace-nav" aria-label="Workspace navigation">
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
      <main class="workspace-main" id="workspace-main">
        <div class="workspace-tabs" role="tablist" aria-label="Canvas tabs">
          <button
            class="workspace-tab is-active"
            role="tab"
            aria-selected="true"
            aria-controls="workspace-canvas"
            data-canvas-tab="document"
            id="canvas-tab-document"
            tabindex="0"
          >
            Document
          </button>
          <button
            class="workspace-tab"
            role="tab"
            aria-selected="false"
            aria-controls="workspace-canvas"
            data-canvas-tab="tree"
            id="canvas-tab-tree"
            tabindex="-1"
          >
            Tree
          </button>
          <button
            class="workspace-tab"
            role="tab"
            aria-selected="false"
            aria-controls="workspace-canvas"
            data-canvas-tab="timeline"
            id="canvas-tab-timeline"
            tabindex="-1"
          >
            Timeline
          </button>
          <button
            class="workspace-tab"
            role="tab"
            aria-selected="false"
            aria-controls="workspace-canvas"
            data-canvas-tab="spreadsheet"
            id="canvas-tab-spreadsheet"
            tabindex="-1"
          >
            Spreadsheet
          </button>
          <button
            class="workspace-tab"
            role="tab"
            aria-selected="false"
            aria-controls="workspace-canvas"
            data-canvas-tab="dashboard"
            id="canvas-tab-dashboard"
            tabindex="-1"
          >
            Dashboard
          </button>
        </div>
        <section
          class="workspace-canvas"
          id="workspace-canvas"
          role="tabpanel"
          aria-live="polite"
          aria-labelledby="canvas-tab-document"
        >
          <p>Loading document canvas...</p>
        </section>
      </main>
      <aside class="workspace-assistant" aria-label="Activity guidance panel">
        <div class="assistant-panel">
          <h3>Assistant</h3>
          <div id="activity-guidance">
            <p>Select an activity to view guidance.</p>
          </div>
        </div>
        <section class="workspace-templates" aria-label="Template gallery">
          <h3>Templates</h3>
          <div class="templates-toolbar">
            <div class="templates-tabs" role="tablist" aria-label="Template filters">
              <button class="template-tab is-active" role="tab" aria-selected="true" data-template-filter="all">
                All
              </button>
              <button class="template-tab" role="tab" aria-selected="false" data-template-filter="document">
                Documents
              </button>
              <button class="template-tab" role="tab" aria-selected="false" data-template-filter="spreadsheet">
                Spreadsheets
              </button>
            </div>
            <label class="templates-search" for="template-search">
              <span>Search</span>
              <input id="template-search" type="search" placeholder="Search templates" />
            </label>
          </div>
          <div class="templates-body">
            <div class="templates-list" id="template-list">
              <p class="templates-empty">Loading templates...</p>
            </div>
            <div class="templates-detail" id="template-detail">
              <p>Select a template to see details.</p>
            </div>
          </div>
          <p class="templates-status" id="template-status" role="status"></p>
        </section>
        <section class="workspace-agents" aria-label="Agent gallery">
          <div class="agents-header">
            <h3>Agents</h3>
            <span class="agents-role" id="agents-role"></span>
          </div>
          <div class="agents-toolbar">
            <label class="agents-search" for="agents-search">
              <span>Search</span>
              <input id="agents-search" type="search" placeholder="Search agents" />
            </label>
          </div>
          <div class="agents-list" id="agents-list">
            <p class="agents-empty">Loading agent gallery...</p>
          </div>
          <p class="agents-status" id="agents-status" role="status"></p>
        </section>
        <section class="workspace-connectors" aria-label="Connector gallery">
          <div class="connectors-header">
            <h3>Connectors</h3>
            <button type="button" class="connectors-refresh" id="connectors-refresh">
              Refresh
            </button>
          </div>
          <div class="connectors-body">
            <div class="connectors-panel">
              <h4>Available connector types</h4>
              <div class="connectors-list" id="connector-type-list">
                <p class="connectors-empty">Loading connector types...</p>
              </div>
            </div>
            <div class="connectors-panel">
              <h4>Your connector instances</h4>
              <div class="connectors-list" id="connector-instance-list">
                <p class="connectors-empty">Loading connector instances...</p>
              </div>
            </div>
          </div>
          <p class="connectors-status" id="connector-status" role="status"></p>
        </section>
        <div class="connector-modal is-hidden" id="connector-modal" aria-hidden="true">
          <div
            class="connector-modal-card"
            role="dialog"
            aria-modal="true"
            aria-labelledby="connector-modal-title"
          >
            <div class="connector-modal-header">
              <h4 id="connector-modal-title">Add connector</h4>
              <button type="button" class="connector-modal-close" id="connector-modal-close">
                Close
              </button>
            </div>
            <form id="connector-modal-form">
              <label class="connector-field">
                <span>Version</span>
                <input type="text" id="connector-version" required />
              </label>
              <label class="connector-field">
                <span>Instance URL (optional)</span>
                <input type="text" id="connector-instance-url" placeholder="https://..." />
              </label>
              <label class="connector-field">
                <span>Notes (optional)</span>
                <textarea id="connector-notes" rows="3" placeholder="Describe this instance"></textarea>
              </label>
              <div class="connector-modal-actions">
                <button type="submit" class="connector-primary">Create instance</button>
                <button type="button" class="connector-secondary" id="connector-modal-cancel">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
        <div class="agent-modal is-hidden" id="agent-modal" aria-hidden="true">
          <div
            class="agent-modal-card"
            role="dialog"
            aria-modal="true"
            aria-labelledby="agent-modal-title"
            aria-describedby="agent-modal-description"
          >
            <div class="agent-modal-header">
              <h4 id="agent-modal-title">Configure agent</h4>
              <button type="button" class="agent-modal-close" id="agent-modal-close">
                Close
              </button>
            </div>
            <div class="agent-modal-body">
              <p class="agent-modal-description" id="agent-modal-description"></p>
              <label class="agent-field">
                <span>Configuration (JSON object)</span>
                <textarea id="agent-modal-config" rows="8" placeholder="{ }"></textarea>
              </label>
              <p class="agent-modal-status" id="agent-modal-status"></p>
              <div class="agent-modal-actions">
                <button type="button" class="agent-modal-primary" id="agent-modal-save">
                  Save configuration
                </button>
                <button type="button" class="agent-modal-secondary" id="agent-modal-reset">
                  Reset to defaults
                </button>
              </div>
            </div>
          </div>
        </div>
      </aside>
    </div>
  `;
};

const initWorkspace = () => {
  renderWorkspaceShell();
  const workspaceShell = document.querySelector(".workspace-shell");
  const navToggle = document.getElementById("workspace-nav-toggle");
  const navOverlay = document.getElementById("workspace-nav-overlay");
  const closeWorkspaceNav = () => {
    if (!workspaceShell) {
      return;
    }
    workspaceShell.classList.remove("is-nav-open");
    if (navToggle) {
      navToggle.setAttribute("aria-expanded", "false");
    }
    if (navOverlay) {
      navOverlay.setAttribute("aria-hidden", "true");
    }
  };
  const openWorkspaceNav = () => {
    if (!workspaceShell) {
      return;
    }
    workspaceShell.classList.add("is-nav-open");
    if (navToggle) {
      navToggle.setAttribute("aria-expanded", "true");
    }
    if (navOverlay) {
      navOverlay.setAttribute("aria-hidden", "false");
    }
  };
  if (navOverlay) {
    navOverlay.setAttribute("aria-hidden", "true");
    navOverlay.addEventListener("click", () => closeWorkspaceNav());
  }
  if (navToggle) {
    navToggle.addEventListener("click", () => {
      if (workspaceShell?.classList.contains("is-nav-open")) {
        closeWorkspaceNav();
      } else {
        openWorkspaceNav();
      }
    });
  }
  const sessionInfo = document.getElementById("workspace-session");
  let session = null;
  loadSession(sessionInfo).then((payload) => {
    session = payload;
    loadAgentGallery();
  });
  const searchParams = new URLSearchParams(window.location.search);
  const projectId = searchParams.get("project_id") || "default";
  const urlMethodology = searchParams.get("methodology");
  const tabs = Array.from(document.querySelectorAll(".workspace-tab"));
  let workspaceState = null;
  const assistantTranscript = [];
  let activityIndex = new Map();
  const documentState = {
    list: [],
    selected: null,
  };
  const timelineState = {
    milestones: [],
    editingId: null,
    exportPayload: null,
    highlightMilestoneId: null,
  };
  const spreadsheetState = {
    sheets: [],
    selectedSheetId: null,
    sheet: null,
    rows: [],
  };
  const treeState = {
    nodes: [],
    collapsed: new Set(),
    highlightMilestoneId: null,
  };
  const dashboardState = {
    errors: {
      health: "",
      trends: "",
      quality: "",
      portfolio: "",
      lifecycle: "",
    },
    charts: new Map(),
    chartLoader: null,
  };
  const templatesState = {
    list: [],
    selected: null,
    filter: "all",
    query: "",
  };
  const connectorsState = {
    types: [],
    instances: [],
    selectedType: null,
    status: "",
  };
  const agentsState = {
    agents: [],
    query: "",
    expanded: new Set(),
    selected: null,
  };

  const setActiveTab = (targetTab) => {
    const canvas = document.getElementById("workspace-canvas");
    tabs.forEach((item) => {
      const isActive = item === targetTab;
      item.classList.toggle("is-active", isActive);
      item.setAttribute("aria-selected", isActive ? "true" : "false");
      item.setAttribute("tabindex", isActive ? "0" : "-1");
      if (isActive && canvas && item.id) {
        canvas.setAttribute("aria-labelledby", item.id);
      }
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
        const progressValue = Math.round(stage.progress.percent);
        const isComplete = progressValue >= 100;
        const isAccessible = stage.activities.some(
          (activity) => activity.access.allowed,
        );
        const progressStatus = isComplete
          ? "complete"
          : isAccessible
            ? "in-progress"
            : "locked";
        const activitiesMarkup = stage.activities
          .map((activity) => {
            const statusIcon = activity.completed
              ? "Complete"
              : activity.access.allowed
                ? "Available"
                : "Locked";
            const isSelected = activity.id === currentActivityId;
            return `
              <li>
                <button
                  class="workspace-activity${isSelected ? " is-selected" : ""}"
                  data-activity-id="${activity.id}"
                  data-stage-id="${stage.id}"
                  data-canvas-tab="${activity.recommended_canvas_tab}"
                  aria-pressed="${isSelected ? "true" : "false"}"
                  aria-label="${activity.name} activity"
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
              <div class="workspace-stage-title">
                <span>${stage.name}</span>
                <span class="workspace-stage-percent">${progressValue}%</span>
              </div>
              <div
                class="workspace-stage-progress"
                role="progressbar"
                aria-label="${stage.name} progress"
                aria-valuemin="0"
                aria-valuemax="100"
                aria-valuenow="${progressValue}"
              >
                <span
                  class="workspace-stage-progress-bar is-${progressStatus}"
                  style="width: ${progressValue}%"
                ></span>
              </div>
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
              aria-pressed="${isSelected ? "true" : "false"}"
              aria-label="${activity.name} activity"
            >
              Available ${activity.name}
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
              <button
                type="button"
                class="assistant-chip"
                data-prompt="${prompt}"
                aria-label="Use prompt: ${prompt}"
              >
                ${prompt}
              </button>
            `,
          )
          .join("")
      : "<p class=\"assistant-empty\">No prompts available for this activity.</p>";
    const researchButtons = [];
    if (activity.id === "monitoring-risks") {
      researchButtons.push(
        '<button type="button" id="research-risks" class="assistant-research">Research risks</button>',
      );
    }
    if (activity.id === "monitoring-vendors") {
      researchButtons.push(
        '<button type="button" id="research-vendor" class="assistant-research">Research vendor</button>',
      );
    }
    if (activity.id === "monitoring-compliance") {
      researchButtons.push(
        '<button type="button" id="research-compliance" class="assistant-research">Monitor regulations</button>',
      );
    }
    const researchMarkup = researchButtons.length
      ? `<div class="assistant-research-actions">${researchButtons.join("")}</div>`
      : "";

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
          <button type="button" id="assistant-send" disabled>Send</button>
        </div>
        ${researchMarkup}
        <p class="assistant-status" id="assistant-status" role="status" aria-live="polite"></p>
        <div class="assistant-transcript">
          <div class="assistant-transcript-header">
            <span>Transcript</span>
            <span class="assistant-transcript-hint">Session-only</span>
          </div>
          <div class="assistant-transcript-body" id="assistant-transcript">
            <p class="assistant-transcript-empty" id="assistant-transcript-empty">
              No assistant messages yet.
            </p>
          </div>
        </div>
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

  const getTreeFolders = () =>
    treeState.nodes.filter((node) => node.type === "folder");

  const buildParentOptions = (selectedId) => {
    const options = [`<option value=\"\">Root</option>`];
    getTreeFolders().forEach((node) => {
      const selected = node.node_id === selectedId ? "selected" : "";
      options.push(`<option value=\"${node.node_id}\" ${selected}>${node.title}</option>`);
    });
    return options.join("");
  };

  const refreshTreeParentSelects = () => {
    document.querySelectorAll("[data-tree-parent-select]").forEach((select) => {
      const selectedValue = select.dataset.selectedParent || select.value || "";
      select.innerHTML = buildParentOptions(selectedValue);
      select.value = selectedValue;
    });
  };

  const renderTreeList = () => {
    const list = document.getElementById("tree-list");
    if (!list) {
      return;
    }
    const childrenByParent = new Map();
    treeState.nodes.forEach((node) => {
      const key = node.parent_id || "root";
      if (!childrenByParent.has(key)) {
        childrenByParent.set(key, []);
      }
      childrenByParent.get(key).push(node);
    });
    childrenByParent.forEach((children) => {
      children.sort((a, b) => {
        if (a.sort_order !== b.sort_order) {
          return a.sort_order - b.sort_order;
        }
        return a.title.localeCompare(b.title);
      });
    });

    const buildRow = (node, depth) => {
      const hasChildren = childrenByParent.has(node.node_id);
      const isCollapsed = treeState.collapsed.has(node.node_id);
      const iconMap = {
        folder: "Folder",
        document: "Document",
        sheet: "Sheet",
        milestone: "Milestone",
        note: "Note",
      };
      const toggle = node.type === "folder"
        ? `<button type=\"button\" class=\"tree-toggle\" data-action=\"toggle\" aria-label=\"Toggle\" data-node-id=\"${node.node_id}\">
            ${hasChildren ? (isCollapsed ? "▶" : "▼") : "•"}
          </button>`
        : "<span class=\"tree-toggle-placeholder\"></span>";
      const noteText = node.type === "note" && node.ref?.text
        ? `<div class=\"tree-note\">${node.ref.text}</div>`
        : "";
      const titleButton = ["document", "sheet", "milestone"].includes(node.type)
        ? `<button type=\"button\" class=\"tree-title-link\" data-action=\"open\" data-node-id=\"${node.node_id}\">${node.title}</button>`
        : `<span class=\"tree-title\">${node.title}</span>`;
      return `
        <li class=\"tree-node\" data-node-id=\"${node.node_id}\" style=\"--tree-depth: ${depth};\">
          <div class=\"tree-node-row\">
            ${toggle}
            <span class=\"tree-icon\">${iconMap[node.type] || "Package"}</span>
            <div class=\"tree-title-group\">
              ${titleButton}
              <span class=\"tree-meta\">${node.type}</span>
              ${noteText}
            </div>
            <div class=\"tree-actions\">
              <button type=\"button\" class=\"secondary\" data-action=\"rename\" data-node-id=\"${node.node_id}\">Rename</button>
              <button type=\"button\" class=\"secondary\" data-action=\"delete\" data-node-id=\"${node.node_id}\">Delete</button>
            </div>
          </div>
          <div class=\"tree-move-row\">\n            <label>\n              Parent\n              <select class=\"tree-move-parent\" data-node-id=\"${node.node_id}\" data-tree-parent-select data-selected-parent=\"${node.parent_id || ""}\">\n                ${buildParentOptions(node.parent_id)}\n              </select>\n            </label>\n            <label>\n              Sort\n              <input type=\"number\" class=\"tree-move-sort\" data-node-id=\"${node.node_id}\" value=\"${node.sort_order}\" />\n            </label>\n            <button type=\"button\" class=\"secondary\" data-action=\"move\" data-node-id=\"${node.node_id}\">Move</button>\n          </div>\n        </li>\n      `;
    };

    const buildTree = (parentId, depth) => {
      const key = parentId || "root";
      const children = childrenByParent.get(key) || [];
      return children
        .map((child) => {
          const rows = [buildRow(child, depth)];
          const isCollapsed = treeState.collapsed.has(child.node_id);
          if (child.type === "folder" && !isCollapsed) {
            rows.push(buildTree(child.node_id, depth + 1));
          }
          return rows.join("");
        })
        .join("");
    };

    list.innerHTML = buildTree(null, 0) || "<li class=\"tree-empty\">No tree nodes yet.</li>";

    list.querySelectorAll("[data-action=\"toggle\"]").forEach((button) => {
      button.addEventListener("click", () => {
        const nodeId = button.dataset.nodeId;
        if (!nodeId) {
          return;
        }
        if (treeState.collapsed.has(nodeId)) {
          treeState.collapsed.delete(nodeId);
        } else {
          treeState.collapsed.add(nodeId);
        }
        renderTreeList();
      });
    });

    list.querySelectorAll("[data-action=\"rename\"]").forEach((button) => {
      button.addEventListener("click", async () => {
        const nodeId = button.dataset.nodeId;
        if (!nodeId) {
          return;
        }
        const node = treeState.nodes.find((item) => item.node_id === nodeId);
        const title = window.prompt("Rename node", node?.title || "");
        if (!title || !title.trim()) {
          return;
        }
        await updateTreeNode(nodeId, { title: title.trim() });
      });
    });

    list.querySelectorAll("[data-action=\"delete\"]").forEach((button) => {
      button.addEventListener("click", async () => {
        const nodeId = button.dataset.nodeId;
        if (!nodeId) {
          return;
        }
        const node = treeState.nodes.find((item) => item.node_id === nodeId);
        const confirmed = window.confirm(`Delete node \"${node?.title || ""}\"?`);
        if (!confirmed) {
          return;
        }
        await deleteTreeNode(nodeId);
      });
    });

    list.querySelectorAll("[data-action=\"move\"]").forEach((button) => {
      button.addEventListener("click", async () => {
        const nodeId = button.dataset.nodeId;
        if (!nodeId) {
          return;
        }
        const parentSelect = list.querySelector(
          `.tree-move-parent[data-node-id=\"${nodeId}\"]`,
        );
        const sortInput = list.querySelector(
          `.tree-move-sort[data-node-id=\"${nodeId}\"]`,
        );
        const newParentId = parentSelect ? parentSelect.value || null : null;
        const newSortOrder = sortInput ? Number(sortInput.value) : 0;
        await moveTreeNode(nodeId, {
          new_parent_id: newParentId,
          new_sort_order: Number.isNaN(newSortOrder) ? 0 : newSortOrder,
        });
      });
    });

    list.querySelectorAll("[data-action=\"open\"]").forEach((button) => {
      button.addEventListener("click", async () => {
        const nodeId = button.dataset.nodeId;
        const node = treeState.nodes.find((item) => item.node_id === nodeId);
        if (!node || !node.ref) {
          return;
        }
        if (node.type === "document" && node.ref.document_id) {
          await openLinkedArtifact({ document_id: node.ref.document_id });
        }
        if (node.type === "sheet" && node.ref.sheet_id) {
          await openLinkedArtifact({ sheet_id: node.ref.sheet_id });
        }
        if (node.type === "milestone" && node.ref.milestone_id) {
          await openLinkedArtifact({ milestone_id: node.ref.milestone_id });
        }
      });
    });
  };

  const setTreeStatus = (message, isError = false) => {
    const element = document.getElementById("tree-status");
    if (!element) {
      return;
    }
    element.textContent = message;
    element.classList.toggle("is-error", isError);
  };

  const loadTreeNodes = async () => {
    setTreeStatus("Loading tree...");
    const response = await fetch(`/api/tree/${projectId}`);
    if (!response.ok) {
      setTreeStatus("Unable to load tree.", true);
      return;
    }
    const payload = await response.json();
    treeState.nodes = payload.nodes || [];
    setTreeStatus(`${treeState.nodes.length} node(s).`);
    renderTreeList();
    refreshTreeParentSelects();
  };

  const createTreeNode = async (payload) => {
    setTreeStatus("");
    const response = await fetch(`/api/tree/${projectId}/nodes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      setTreeStatus(result?.detail || "Unable to create node.", true);
      return;
    }
    setTreeStatus("Node created.");
    await loadTreeNodes();
  };

  const updateTreeNode = async (nodeId, payload) => {
    setTreeStatus("");
    const response = await fetch(`/api/tree/${projectId}/nodes/${nodeId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      setTreeStatus(result?.detail || "Unable to update node.", true);
      return;
    }
    setTreeStatus("Node updated.");
    await loadTreeNodes();
  };

  const moveTreeNode = async (nodeId, payload) => {
    setTreeStatus("");
    const response = await fetch(`/api/tree/${projectId}/nodes/${nodeId}/move`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      setTreeStatus(result?.detail || "Unable to move node.", true);
      return;
    }
    setTreeStatus("Node moved.");
    await loadTreeNodes();
  };

  const deleteTreeNode = async (nodeId) => {
    setTreeStatus("");
    const response = await fetch(`/api/tree/${projectId}/nodes/${nodeId}`, {
      method: "DELETE",
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      setTreeStatus(result?.detail || "Unable to delete node.", true);
      return;
    }
    setTreeStatus(`Deleted ${result.deleted_count || 0} node(s).`);
    await loadTreeNodes();
  };

  const openLinkedArtifact = async (openRef) => {
    if (!workspaceState) {
      return;
    }
    let targetTab = "document";
    if (openRef.sheet_id) {
      targetTab = "spreadsheet";
    } else if (openRef.milestone_id) {
      targetTab = "timeline";
    } else if (openRef.document_id) {
      targetTab = "document";
    }
    const response = await postSelection({
      current_canvas_tab: targetTab,
      current_stage_id: workspaceState.current_stage_id,
      current_activity_id: workspaceState.current_activity_id,
      methodology: workspaceState.methodology,
      open_ref: openRef,
    });
    if (response) {
      updateWorkspaceUI(response);
    }
  };

  const setTemplateStatus = (message, isError = false) => {
    const status = document.getElementById("template-status");
    if (!status) {
      return;
    }
    status.textContent = message;
    status.classList.toggle("is-error", isError);
  };

  const renderTemplateList = () => {
    const list = document.getElementById("template-list");
    if (!list) {
      return;
    }
    if (!templatesState.list.length) {
      list.innerHTML = "<p class=\"templates-empty\">No templates found.</p>";
      return;
    }
    list.innerHTML = templatesState.list
      .map(
        (template) => `
          <button type="button" class="template-item${
            templatesState.selected?.template_id === template.template_id
              ? " is-selected"
              : ""
          }" data-template-id="${template.template_id}">
            <span class="template-name">${escapeHtml(template.name)}</span>
            <span class="template-type">${escapeHtml(template.type)}</span>
          </button>
        `,
      )
      .join("");

    list.querySelectorAll(".template-item").forEach((button) => {
      button.addEventListener("click", () => {
        const templateId = button.dataset.templateId;
        const match = templatesState.list.find(
          (item) => item.template_id === templateId,
        );
        if (!match) {
          return;
        }
        templatesState.selected = match;
        renderTemplateList();
        renderTemplateDetail();
      });
    });
  };

  const renderTemplateDetail = () => {
    const detail = document.getElementById("template-detail");
    if (!detail) {
      return;
    }
    const template = templatesState.selected;
    if (!template) {
      detail.innerHTML = "<p>Select a template to see details.</p>";
      return;
    }
    const tags = template.tags.length
      ? template.tags
          .map((tag) => `<span class="template-tag">${escapeHtml(tag)}</span>`)
          .join("")
      : "<span class=\"template-tag is-muted\">No tags</span>";
    detail.innerHTML = `
      <div class="template-detail-card">
        <p class="template-detail-type">${escapeHtml(template.type)}</p>
        <h4>${escapeHtml(template.name)}</h4>
        <p class="template-detail-description">${escapeHtml(template.description)}</p>
        <div class="template-tags">${tags}</div>
        <button type="button" class="template-instantiate" id="template-instantiate">
          Instantiate
        </button>
      </div>
    `;

    const instantiateButton = document.getElementById("template-instantiate");
    if (instantiateButton) {
      instantiateButton.addEventListener("click", () => {
        instantiateTemplate();
      });
    }
  };

  const loadTemplates = async () => {
    const params = new URLSearchParams();
    params.set("gallery", "true");
    if (templatesState.filter !== "all") {
      params.set("type", templatesState.filter);
    }
    if (templatesState.query) {
      params.set("q", templatesState.query);
    }
    setTemplateStatus("Loading templates...");
    const response = await fetch(`/api/templates?${params.toString()}`);
    if (!response.ok) {
      setTemplateStatus("Unable to load templates.", true);
      return;
    }
    const payload = await response.json();
    templatesState.list = payload;
    if (
      templatesState.selected &&
      !templatesState.list.find(
        (item) => item.template_id === templatesState.selected?.template_id,
      )
    ) {
      templatesState.selected = null;
    }
    if (!templatesState.selected && templatesState.list.length) {
      templatesState.selected = templatesState.list[0];
    }
    renderTemplateList();
    renderTemplateDetail();
    setTemplateStatus(
      templatesState.list.length
        ? `${templatesState.list.length} template(s).`
        : "No templates found.",
    );
  };

  const instantiateTemplate = async () => {
    if (!templatesState.selected) {
      return;
    }
    const templateId = templatesState.selected.template_id;
    setTemplateStatus("Instantiating template...");
    const parameters = session?.subject ? { user: session.subject } : {};
    const response = await fetch(`/api/templates/${templateId}/instantiate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_id: projectId, parameters }),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      setTemplateStatus(payload?.detail || "Unable to instantiate template.", true);
      return;
    }
    setTemplateStatus("Template instantiated.");
    const openRef = {};
    if (payload.created_type === "document" && payload.document_id) {
      openRef.document_id = payload.document_id;
    }
    if (payload.created_type === "spreadsheet" && payload.sheet_id) {
      openRef.sheet_id = payload.sheet_id;
    }
    if (Object.keys(openRef).length) {
      await openLinkedArtifact(openRef);
    }
  };


  const setAgentStatus = (message, isError = false) => {
    const status = document.getElementById("agents-status");
    if (!status) {
      return;
    }
    status.textContent = message;
    status.classList.toggle("is-error", isError);
  };

  const isAgentAdmin = () => {
    const roles = session?.roles || [];
    if (typeof roles === "string") {
      return ["tenant_owner", "portfolio_admin"].includes(roles);
    }
    return roles.some((role) => ["tenant_owner", "portfolio_admin"].includes(role));
  };

  const renderAgentGallery = () => {
    const list = document.getElementById("agents-list");
    if (!list) {
      return;
    }
    if (!agentsState.agents.length) {
      list.innerHTML = '<p class="agents-empty">No agents available.</p>';
      return;
    }
    const query = agentsState.query.toLowerCase();
    const filtered = agentsState.agents.filter((agent) => {
      if (!query) {
        return true;
      }
      const haystack = `${agent.name} ${agent.description} ${agent.outputs.join(" ")}`.toLowerCase();
      return haystack.includes(query);
    });
    if (!filtered.length) {
      list.innerHTML = '<p class="agents-empty">No matching agents.</p>';
      return;
    }
    const grouped = filtered.reduce((acc, agent) => {
      const category = agent.category || "Uncategorized";
      acc[category] = acc[category] || [];
      acc[category].push(agent);
      return acc;
    }, {});
    list.innerHTML = Object.keys(grouped)
      .sort()
      .map((category) => {
        const isExpanded = agentsState.expanded.has(category);
        const cards = grouped[category]
          .map((agent) => {
            const outputs = agent.outputs.length
              ? agent.outputs
                  .map((output) => `<span class="agent-chip">${escapeHtml(output)}</span>`)
                  .join(" ")
              : '<span class="agent-chip is-muted">Outputs not listed</span>';
            const requiredBadge = agent.required ? '<span class="agent-badge">Required</span>' : "";
            return `
              <div class="agent-card" data-agent-id="${escapeHtml(agent.agent_id)}">
                <div class="agent-card-header">
                  <div>
                    <h5>${escapeHtml(agent.name)}</h5>
                    <div class="agent-card-meta">
                      ${requiredBadge}
                      <span>${escapeHtml(agent.agent_id)}</span>
                    </div>
                  </div>
                  <label class="agent-toggle">
                    <input type="checkbox" ${agent.enabled ? "checked" : ""} ${
                      !isAgentAdmin() || agent.required ? "disabled" : ""
                    } />
                    <span>Enabled</span>
                  </label>
                </div>
                <p class="agent-description">${escapeHtml(agent.description)}</p>
                <div class="agent-outputs">${outputs}</div>
                <div class="agent-actions">
                  <button type="button" class="agent-configure" ${
                    !isAgentAdmin() ? "disabled" : ""
                  }>Configure</button>
                  <button type="button" class="agent-sample">View sample outputs</button>
                </div>
              </div>
            `;
          })
          .join("");
        return `
          <div class="agent-category" data-category="${escapeHtml(category)}">
            <button type="button" class="agent-category-toggle" aria-expanded="${
              isExpanded ? "true" : "false"
            }">
              <span>${escapeHtml(category)}</span>
              <span class="agent-category-count">${grouped[category].length}</span>
            </button>
            <div class="agent-category-body${isExpanded ? "" : " is-collapsed"}">
              ${cards}
            </div>
          </div>
        `;
      })
      .join("");

    list.querySelectorAll(".agent-category-toggle").forEach((button) => {
      button.addEventListener("click", () => {
        const category = button.parentElement?.dataset.category;
        if (!category) {
          return;
        }
        if (agentsState.expanded.has(category)) {
          agentsState.expanded.delete(category);
        } else {
          agentsState.expanded.add(category);
        }
        renderAgentGallery();
      });
    });

    list.querySelectorAll(".agent-toggle input").forEach((input) => {
      input.addEventListener("change", async (event) => {
        const card = event.target.closest(".agent-card");
        const agentId = card?.dataset.agentId;
        if (!agentId) {
          return;
        }
        const enabled = event.target.checked;
        await patchAgentSetting(agentId, { enabled });
      });
    });

    list.querySelectorAll(".agent-configure").forEach((button) => {
      button.addEventListener("click", () => {
        const card = button.closest(".agent-card");
        const agentId = card?.dataset.agentId;
        if (!agentId) {
          return;
        }
        const agent = agentsState.agents.find((item) => item.agent_id === agentId);
        if (agent) {
          openAgentModal(agent);
        }
      });
    });

    list.querySelectorAll(".agent-sample").forEach((button) => {
      button.addEventListener("click", async () => {
        const agentId = button.closest(".agent-card")?.dataset?.agentId;
        if (!agentId) return;
        setAgentStatus("Loading sample outputs...");
        try {
          const response = await fetch(`/api/agent-samples/${agentId}`);
          if (response.ok) {
            const data = await response.json();
            setAgentStatus(`Sample outputs: ${JSON.stringify(data.samples || []).slice(0, 100)}...`);
          } else {
            setAgentStatus("Sample outputs require agent activation.");
          }
        } catch {
          setAgentStatus("Sample outputs require agent activation.");
        }
      });
    });
  };

  const loadAgentGallery = async () => {
    const roleLabel = document.getElementById("agents-role");
    if (roleLabel) {
      roleLabel.textContent = isAgentAdmin() ? "Admin access" : "Read-only";
    }
    setAgentStatus("Loading agent gallery...");
    const response = await fetch(`/api/agent-gallery/${projectId}`);
    if (!response.ok) {
      setAgentStatus("Unable to load agent settings.", true);
      return;
    }
    const payload = await response.json();
    agentsState.agents = payload.agents || [];
    if (!agentsState.expanded.size) {
      agentsState.agents.forEach((agent) => agentsState.expanded.add(agent.category));
    }
    renderAgentGallery();
    setAgentStatus(
      agentsState.agents.length ? `${agentsState.agents.length} agent(s) loaded.` : "No agents available.",
    );
  };

  const patchAgentSetting = async (agentId, body) => {
    setAgentStatus("Saving agent changes...");
    const response = await fetch(`/api/agent-gallery/${projectId}/agents/${agentId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      setAgentStatus(payload?.detail || "Unable to update agent.", true);
      await loadAgentGallery();
      return;
    }
    agentsState.agents = agentsState.agents.map((agent) =>
      agent.agent_id === agentId ? { ...agent, ...payload } : agent,
    );
    renderAgentGallery();
    setAgentStatus("Agent updated.");
  };

  const openAgentModal = (agent) => {
    const modal = document.getElementById("agent-modal");
    const title = document.getElementById("agent-modal-title");
    const description = document.getElementById("agent-modal-description");
    const configField = document.getElementById("agent-modal-config");
    const status = document.getElementById("agent-modal-status");
    if (!modal || !title || !description || !configField) {
      return;
    }
    agentsState.selected = agent;
    title.textContent = `Configure ${agent.name}`;
    description.textContent = agent.description;
    configField.value = JSON.stringify(agent.config || {}, null, 2);
    if (status) {
      status.textContent = "";
      status.classList.remove("is-error");
    }
    modal.classList.remove("is-hidden");
    modal.setAttribute("aria-hidden", "false");
  };

  const closeAgentModal = () => {
    const modal = document.getElementById("agent-modal");
    if (!modal) {
      return;
    }
    modal.classList.add("is-hidden");
    modal.setAttribute("aria-hidden", "true");
    agentsState.selected = null;
  };

  const attachAgentHandlers = () => {
    const searchInput = document.getElementById("agents-search");
    if (searchInput) {
      searchInput.addEventListener("input", () => {
        agentsState.query = searchInput.value.trim();
        renderAgentGallery();
      });
    }
    const closeButton = document.getElementById("agent-modal-close");
    if (closeButton) {
      closeButton.addEventListener("click", () => closeAgentModal());
    }
    const saveButton = document.getElementById("agent-modal-save");
    if (saveButton) {
      saveButton.addEventListener("click", async () => {
        if (!agentsState.selected) {
          return;
        }
        const configField = document.getElementById("agent-modal-config");
        const status = document.getElementById("agent-modal-status");
        if (!configField) {
          return;
        }
        let parsed = {};
        try {
          parsed = configField.value.trim() ? JSON.parse(configField.value) : {};
        } catch (error) {
          if (status) {
            status.textContent = "Invalid JSON: please enter an object.";
            status.classList.add("is-error");
          }
          return;
        }
        if (parsed === null || Array.isArray(parsed) || typeof parsed !== "object") {
          if (status) {
            status.textContent = "Configuration must be a JSON object.";
            status.classList.add("is-error");
          }
          return;
        }
        if (status) {
          status.textContent = "Saving configuration...";
          status.classList.remove("is-error");
        }
        await patchAgentSetting(agentsState.selected.agent_id, { config: parsed });
        closeAgentModal();
      });
    }
    const resetButton = document.getElementById("agent-modal-reset");
    if (resetButton) {
      resetButton.addEventListener("click", async () => {
        const status = document.getElementById("agent-modal-status");
        if (status) {
          status.textContent = "Resetting to defaults...";
          status.classList.remove("is-error");
        }
        const response = await fetch(`/api/agent-gallery/${projectId}/reset-defaults`, {
          method: "POST",
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          if (status) {
            status.textContent = payload?.detail || "Unable to reset defaults.";
            status.classList.add("is-error");
          }
          return;
        }
        agentsState.agents = payload.agents || [];
        renderAgentGallery();
        if (status) {
          status.textContent = "Defaults restored.";
        }
        closeAgentModal();
      });
    }
    const modal = document.getElementById("agent-modal");
    if (modal) {
      modal.addEventListener("click", (event) => {
        if (event.target === modal) {
          closeAgentModal();
        }
      });
    }
  };

  const setConnectorStatus = (message, isError = false) => {
    const status = document.getElementById("connector-status");
    if (!status) {
      return;
    }
    status.textContent = message;
    status.classList.toggle("is-error", isError);
  };

  const formatConnectorTimestamp = (value) => {
    if (!value) {
      return "—";
    }
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
      return value;
    }
    return parsed.toLocaleString();
  };

  const updateInstanceState = (updated) => {
    connectorsState.instances = connectorsState.instances.map((instance) =>
      instance.connector_id === updated.connector_id ? updated : instance,
    );
  };

  const renderConnectorTypes = () => {
    const list = document.getElementById("connector-type-list");
    if (!list) {
      return;
    }
    if (!connectorsState.types.length) {
      list.innerHTML = "<p class=\"connectors-empty\">No connector types available.</p>";
      return;
    }
    list.innerHTML = connectorsState.types
      .map((type) => {
        const credentials = type.credentials_required?.length
          ? `<p class=\"connector-credentials\"><strong>Credentials required:</strong> ${type.credentials_required
              .map((item) => escapeHtml(item))
              .join(", ")}</p>`
          : `<p class=\"connector-credentials is-muted\">${escapeHtml(
              type.credentials_note || "See docs for required credentials.",
            )}</p>`;
        const defaultVersion = type.default_version
          ? `<span class=\"connector-badge\">v${escapeHtml(type.default_version)}</span>`
          : "";
        return `
          <div class="connector-card">
            <div class="connector-card-header">
              <div>
                <h5>${escapeHtml(type.name)}</h5>
                <p class="connector-meta">${escapeHtml(type.status)} • ${escapeHtml(
          type.certification,
        )}</p>
              </div>
              <div class="connector-card-actions">
                ${defaultVersion}
                <button type="button" class="connector-add" data-connector-id="${escapeHtml(
          type.id,
        )}">Add</button>
              </div>
            </div>
            ${credentials}
          </div>
        `;
      })
      .join("");

    list.querySelectorAll(".connector-add").forEach((button) => {
      button.addEventListener("click", () => {
        const connectorId = button.dataset.connectorId;
        if (!connectorId) {
          return;
        }
        const selected = connectorsState.types.find((item) => item.id === connectorId);
        if (!selected) {
          return;
        }
        openConnectorModal(selected);
      });
    });
  };

  const renderConnectorInstances = () => {
    const list = document.getElementById("connector-instance-list");
    if (!list) {
      return;
    }
    if (!connectorsState.instances.length) {
      list.innerHTML = "<p class=\"connectors-empty\">No connector instances yet.</p>";
      return;
    }
    list.innerHTML = connectorsState.instances
      .map((instance) => {
        const metadata = instance.metadata || {};
        const connectorType = metadata.connector_type_id || instance.name || "unknown";
        const enabledLabel = instance.enabled ? "Enabled" : "Disabled";
        return `
          <div class="connector-instance-card">
            <div class="connector-card-header">
              <div>
                <h5>${escapeHtml(connectorType)}</h5>
                <p class="connector-meta">ID: ${escapeHtml(instance.connector_id)}</p>
              </div>
              <label class="connector-toggle">
                <input type="checkbox" data-connector-id="${escapeHtml(
          instance.connector_id,
        )}" ${instance.enabled ? "checked" : ""} />
                <span>${enabledLabel}</span>
              </label>
            </div>
            <div class="connector-instance-grid">
              <div><span>Version</span><strong>${escapeHtml(instance.version)}</strong></div>
              <div><span>Health</span><strong>${escapeHtml(
          instance.health_status || "unknown",
        )}</strong></div>
              <div><span>Last checked</span><strong>${escapeHtml(
          formatConnectorTimestamp(instance.last_checked),
        )}</strong></div>
            </div>
            <div class="connector-instance-actions">
              <label>
                <span>Mark health</span>
                <select data-health-id="${escapeHtml(instance.connector_id)}">
                  ${["healthy", "degraded", "unhealthy", "unknown"]
                    .map(
                      (status) =>
                        `<option value="${status}"${
                          status === (instance.health_status || "unknown") ? " selected" : ""
                        }>${status}</option>`,
                    )
                    .join("")}
                </select>
              </label>
              <button type="button" class="connector-refresh" data-refresh-id="${escapeHtml(
          instance.connector_id,
        )}">
                Refresh health
              </button>
            </div>
          </div>
        `;
      })
      .join("");

    list.querySelectorAll(".connector-toggle input").forEach((input) => {
      input.addEventListener("change", () => {
        const connectorId = input.dataset.connectorId;
        if (!connectorId) {
          return;
        }
        updateConnectorInstance(connectorId, { enabled: input.checked });
      });
    });

    list.querySelectorAll("select[data-health-id]").forEach((select) => {
      select.addEventListener("change", () => {
        const connectorId = select.dataset.healthId;
        if (!connectorId) {
          return;
        }
        updateConnectorInstance(connectorId, { health_status: select.value });
      });
    });

    list.querySelectorAll(".connector-refresh").forEach((button) => {
      button.addEventListener("click", () => {
        const connectorId = button.dataset.refreshId;
        if (!connectorId) {
          return;
        }
        refreshConnectorHealth(connectorId);
      });
    });
  };

  const loadConnectorTypes = async () => {
    setConnectorStatus("Loading connectors...");
    const response = await fetch("/api/connector-gallery/types");
    if (!response.ok) {
      setConnectorStatus("Unable to load connector types.", true);
      return;
    }
    const payload = await response.json();
    connectorsState.types = payload;
    renderConnectorTypes();
    setConnectorStatus("Connector types loaded.");
  };

  const loadConnectorInstances = async () => {
    const response = await fetch("/api/connector-gallery/instances");
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      setConnectorStatus(payload?.detail || "Unable to load connector instances.", true);
      connectorsState.instances = [];
      renderConnectorInstances();
      return;
    }
    connectorsState.instances = payload;
    renderConnectorInstances();
    setConnectorStatus(`Loaded ${connectorsState.instances.length} connector instance(s).`);
  };

  const updateConnectorInstance = async (connectorId, payload) => {
    setConnectorStatus("Updating connector...");
    const response = await fetch(`/api/connector-gallery/instances/${connectorId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      setConnectorStatus(result?.detail || "Unable to update connector.", true);
      return;
    }
    updateInstanceState(result);
    renderConnectorInstances();
    setConnectorStatus("Connector updated.");
  };

  const refreshConnectorHealth = async (connectorId) => {
    setConnectorStatus("Refreshing health status...");
    const response = await fetch(
      `/api/connector-gallery/instances/${connectorId}/health`,
    );
    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      setConnectorStatus(result?.detail || "Unable to refresh health.", true);
      return;
    }
    updateInstanceState(result);
    renderConnectorInstances();
    setConnectorStatus("Health status refreshed.");
  };

  const openConnectorModal = (type) => {
    const modal = document.getElementById("connector-modal");
    const title = document.getElementById("connector-modal-title");
    const versionInput = document.getElementById("connector-version");
    const instanceUrlInput = document.getElementById("connector-instance-url");
    const notesInput = document.getElementById("connector-notes");
    if (!modal || !title || !versionInput || !instanceUrlInput || !notesInput) {
      return;
    }
    connectorsState.selectedType = type;
    title.textContent = `Add ${type.name}`;
    versionInput.value = type.default_version || "1.0.0";
    instanceUrlInput.value = "";
    notesInput.value = "";
    modal.classList.remove("is-hidden");
    modal.setAttribute("aria-hidden", "false");
    versionInput.focus();
  };

  const closeConnectorModal = () => {
    const modal = document.getElementById("connector-modal");
    if (!modal) {
      return;
    }
    modal.classList.add("is-hidden");
    modal.setAttribute("aria-hidden", "true");
  };

  const attachConnectorHandlers = () => {
    const refreshButton = document.getElementById("connectors-refresh");
    if (refreshButton) {
      refreshButton.addEventListener("click", () => {
        loadConnectorTypes();
        loadConnectorInstances();
      });
    }
    const modal = document.getElementById("connector-modal");
    const closeButton = document.getElementById("connector-modal-close");
    const cancelButton = document.getElementById("connector-modal-cancel");
    const form = document.getElementById("connector-modal-form");
    if (closeButton) {
      closeButton.addEventListener("click", () => closeConnectorModal());
    }
    if (cancelButton) {
      cancelButton.addEventListener("click", () => closeConnectorModal());
    }
    if (modal) {
      modal.addEventListener("click", (event) => {
        if (event.target === modal) {
          closeConnectorModal();
        }
      });
    }
    if (form) {
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (!connectorsState.selectedType) {
          return;
        }
        const versionInput = document.getElementById("connector-version");
        const instanceUrlInput = document.getElementById("connector-instance-url");
        const notesInput = document.getElementById("connector-notes");
        if (!versionInput || !instanceUrlInput || !notesInput) {
          return;
        }
        const metadata = {};
        if (instanceUrlInput.value.trim()) {
          metadata.instance_url = instanceUrlInput.value.trim();
        }
        if (notesInput.value.trim()) {
          metadata.notes = notesInput.value.trim();
        }
        setConnectorStatus("Registering connector instance...");
        const response = await fetch("/api/connector-gallery/instances", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            connector_type_id: connectorsState.selectedType.id,
            version: versionInput.value.trim() || "1.0.0",
            enabled: true,
            metadata,
          }),
        });
        const result = await response.json().catch(() => ({}));
        if (!response.ok) {
          setConnectorStatus(result?.detail || "Unable to create connector instance.", true);
          return;
        }
        closeConnectorModal();
        setConnectorStatus("Connector instance created.");
        await loadConnectorInstances();
      });
    }
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
    if (workspaceState?.last_opened_document_id) {
      loadDocumentDetail(workspaceState.last_opened_document_id);
    }
  };

  const renderTreeCanvas = () => {
    const canvas = document.querySelector(".workspace-canvas");
    if (!canvas) {
      return;
    }
    canvas.innerHTML = `
      <div class="tree-canvas">
        <section class="tree-controls">
          <div class="tree-control-card">
            <h3>New Folder</h3>
            <form id="tree-folder-form">
              <label>
                Title
                <input type="text" id="tree-folder-title" required />
              </label>
              <label>
                Parent
                <select id="tree-folder-parent" data-tree-parent-select></select>
              </label>
              <label>
                Sort order
                <input type="number" id="tree-folder-sort" value="0" />
              </label>
              <button type="submit">Create folder</button>
            </form>
          </div>
          <div class="tree-control-card">
            <h3>Link Document</h3>
            <form id="tree-document-form">
              <label>
                Title
                <input type="text" id="tree-document-title" required />
              </label>
              <label>
                Document ID
                <input type="text" id="tree-document-id" required />
              </label>
              <label>
                Parent
                <select id="tree-document-parent" data-tree-parent-select></select>
              </label>
              <label>
                Sort order
                <input type="number" id="tree-document-sort" value="0" />
              </label>
              <button type="submit">Link document</button>
            </form>
          </div>
          <div class="tree-control-card">
            <h3>Link Sheet</h3>
            <form id="tree-sheet-form">
              <label>
                Title
                <input type="text" id="tree-sheet-title" required />
              </label>
              <label>
                Sheet ID
                <input type="text" id="tree-sheet-id" required />
              </label>
              <label>
                Parent
                <select id="tree-sheet-parent" data-tree-parent-select></select>
              </label>
              <label>
                Sort order
                <input type="number" id="tree-sheet-sort" value="0" />
              </label>
              <button type="submit">Link sheet</button>
            </form>
          </div>
          <div class="tree-control-card">
            <h3>Link Milestone</h3>
            <form id="tree-milestone-form">
              <label>
                Title
                <input type="text" id="tree-milestone-title" required />
              </label>
              <label>
                Milestone ID
                <input type="text" id="tree-milestone-id" required />
              </label>
              <label>
                Parent
                <select id="tree-milestone-parent" data-tree-parent-select></select>
              </label>
              <label>
                Sort order
                <input type="number" id="tree-milestone-sort" value="0" />
              </label>
              <button type="submit">Link milestone</button>
            </form>
          </div>
          <div class="tree-control-card">
            <h3>New Note</h3>
            <form id="tree-note-form">
              <label>
                Title
                <input type="text" id="tree-note-title" required />
              </label>
              <label>
                Note text
                <textarea id="tree-note-text" rows="3"></textarea>
              </label>
              <label>
                Parent
                <select id="tree-note-parent" data-tree-parent-select></select>
              </label>
              <label>
                Sort order
                <input type="number" id="tree-note-sort" value="0" />
              </label>
              <button type="submit">Create note</button>
            </form>
          </div>
        </section>
        <section class="tree-list-panel">
          <div class="tree-list-header">
            <div>
              <h3>Artifact tree</h3>
              <p class="tree-list-subtitle">Folders and linked items for this project.</p>
            </div>
            <button type="button" class="secondary" id="tree-refresh">Refresh</button>
          </div>
          <ul id="tree-list" class="tree-list"></ul>
          <p id="tree-status" class="tree-status" role="status" aria-live="polite"></p>
        </section>
      </div>
    `;

    const attachForm = (formId, buildPayload, onSuccess) => {
      const form = document.getElementById(formId);
      if (!form) {
        return;
      }
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const payload = buildPayload();
        if (!payload) {
          return;
        }
        await createTreeNode(payload);
        if (onSuccess) {
          onSuccess();
        }
      });
    };

    attachForm(
      "tree-folder-form",
      () => {
        const title = document.getElementById("tree-folder-title").value.trim();
        if (!title) {
          setTreeStatus("Folder title is required.", true);
          return null;
        }
        return {
          type: "folder",
          title,
          parent_id: document.getElementById("tree-folder-parent").value || null,
          sort_order: Number(document.getElementById("tree-folder-sort").value) || 0,
        };
      },
      () => {
        document.getElementById("tree-folder-title").value = "";
      },
    );

    attachForm(
      "tree-document-form",
      () => {
        const title = document.getElementById("tree-document-title").value.trim();
        const documentId = document.getElementById("tree-document-id").value.trim();
        if (!title || !documentId) {
          setTreeStatus("Document title and ID are required.", true);
          return null;
        }
        return {
          type: "document",
          title,
          parent_id: document.getElementById("tree-document-parent").value || null,
          sort_order: Number(document.getElementById("tree-document-sort").value) || 0,
          ref: { document_id: documentId },
        };
      },
      () => {
        document.getElementById("tree-document-title").value = "";
        document.getElementById("tree-document-id").value = "";
      },
    );

    attachForm(
      "tree-sheet-form",
      () => {
        const title = document.getElementById("tree-sheet-title").value.trim();
        const sheetId = document.getElementById("tree-sheet-id").value.trim();
        if (!title || !sheetId) {
          setTreeStatus("Sheet title and ID are required.", true);
          return null;
        }
        return {
          type: "sheet",
          title,
          parent_id: document.getElementById("tree-sheet-parent").value || null,
          sort_order: Number(document.getElementById("tree-sheet-sort").value) || 0,
          ref: { sheet_id: sheetId },
        };
      },
      () => {
        document.getElementById("tree-sheet-title").value = "";
        document.getElementById("tree-sheet-id").value = "";
      },
    );

    attachForm(
      "tree-milestone-form",
      () => {
        const title = document.getElementById("tree-milestone-title").value.trim();
        const milestoneId = document
          .getElementById("tree-milestone-id")
          .value.trim();
        if (!title || !milestoneId) {
          setTreeStatus("Milestone title and ID are required.", true);
          return null;
        }
        return {
          type: "milestone",
          title,
          parent_id: document.getElementById("tree-milestone-parent").value || null,
          sort_order: Number(document.getElementById("tree-milestone-sort").value) || 0,
          ref: { milestone_id: milestoneId },
        };
      },
      () => {
        document.getElementById("tree-milestone-title").value = "";
        document.getElementById("tree-milestone-id").value = "";
      },
    );

    attachForm(
      "tree-note-form",
      () => {
        const title = document.getElementById("tree-note-title").value.trim();
        const text = document.getElementById("tree-note-text").value.trim();
        if (!title) {
          setTreeStatus("Note title is required.", true);
          return null;
        }
        return {
          type: "note",
          title,
          parent_id: document.getElementById("tree-note-parent").value || null,
          sort_order: Number(document.getElementById("tree-note-sort").value) || 0,
          ref: text ? { text } : null,
        };
      },
      () => {
        document.getElementById("tree-note-title").value = "";
        document.getElementById("tree-note-text").value = "";
      },
    );

    const refreshButton = document.getElementById("tree-refresh");
    refreshButton.addEventListener("click", () => {
      loadTreeNodes();
    });

    refreshTreeParentSelects();
    loadTreeNodes();
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
      const highlight =
        timelineState.highlightMilestoneId === milestone.milestone_id
          ? " is-highlighted"
          : "";
      const row = document.createElement("tr");
      row.className = highlight.trim();
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

    timelineState.highlightMilestoneId =
      workspaceState?.last_opened_milestone_id || null;
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

  const setSpreadsheetMessage = (message, isError = false) => {
    const element = document.getElementById("spreadsheet-message");
    if (!element) {
      return;
    }
    element.textContent = message;
    element.classList.toggle("is-error", isError);
  };

  const setSpreadsheetCreateMessage = (message, isError = false) => {
    const element = document.getElementById("spreadsheet-create-message");
    if (!element) {
      return;
    }
    element.textContent = message;
    element.classList.toggle("is-error", isError);
  };

  const setSpreadsheetImportMessage = (message, isError = false) => {
    const element = document.getElementById("spreadsheet-import-message");
    if (!element) {
      return;
    }
    element.textContent = message;
    element.classList.toggle("is-error", isError);
  };

  const renderSpreadsheetSheetOptions = () => {
    const select = document.getElementById("spreadsheet-sheet-select");
    if (!select) {
      return;
    }
    select.innerHTML = "";
    if (!spreadsheetState.sheets.length) {
      const option = document.createElement("option");
      option.value = "";
      option.textContent = "No sheets yet";
      select.appendChild(option);
      return;
    }
    spreadsheetState.sheets.forEach((sheet) => {
      const option = document.createElement("option");
      option.value = sheet.sheet_id;
      option.textContent = sheet.name;
      select.appendChild(option);
    });
    select.value = spreadsheetState.selectedSheetId || spreadsheetState.sheets[0].sheet_id;
  };

  const loadSpreadsheetSheet = async (sheetId) => {
    if (!sheetId) {
      spreadsheetState.sheet = null;
      spreadsheetState.rows = [];
      renderSpreadsheetTable();
      return;
    }
    const response = await fetch(
      `/api/spreadsheets/${projectId}/sheets/${sheetId}`,
    );
    if (!response.ok) {
      setSpreadsheetMessage("Unable to load sheet.", true);
      return;
    }
    const payload = await response.json();
    spreadsheetState.sheet = payload.sheet;
    spreadsheetState.rows = payload.rows || [];
    renderSpreadsheetTable();
  };

  const loadSpreadsheetSheets = async () => {
    const response = await fetch(`/api/spreadsheets/${projectId}/sheets`);
    if (!response.ok) {
      setSpreadsheetMessage("Unable to load sheets.", true);
      return;
    }
    const payload = await response.json();
    spreadsheetState.sheets = payload || [];
    if (
      !spreadsheetState.selectedSheetId ||
      !spreadsheetState.sheets.some(
        (sheet) => sheet.sheet_id === spreadsheetState.selectedSheetId,
      )
    ) {
      spreadsheetState.selectedSheetId =
        spreadsheetState.sheets[0]?.sheet_id || null;
    }
    renderSpreadsheetSheetOptions();
    await loadSpreadsheetSheet(spreadsheetState.selectedSheetId);
  };

  const renderSpreadsheetTable = () => {
    const wrapper = document.getElementById("spreadsheet-table-wrapper");
    const title = document.getElementById("spreadsheet-sheet-title");
    if (!wrapper) {
      return;
    }
    if (!spreadsheetState.sheet) {
      wrapper.innerHTML = "<p class=\"spreadsheet-empty\">Create a sheet to get started.</p>";
      if (title) {
        title.textContent = "Spreadsheet";
      }
      return;
    }
    const columns = spreadsheetState.sheet.columns || [];
    if (title) {
      title.textContent = spreadsheetState.sheet.name;
    }
    const headerCells = columns
      .map(
        (column) => `
          <th>
            <div class="spreadsheet-header-cell">
              <span>${column.name}</span>
              <span class="spreadsheet-header-meta">${column.type}${column.required ? " *" : ""}</span>
            </div>
          </th>
        `,
      )
      .join("");
    const newRowCells = columns
      .map((column) => {
        if (column.type === "bool") {
          return `
            <td>
              <input
                type="checkbox"
                class="spreadsheet-cell-input"
                data-column-id="${column.column_id}"
                data-column-type="${column.type}"
              />
            </td>
          `;
        }
        const inputType =
          column.type === "date"
            ? "date"
            : column.type === "number"
              ? "number"
              : "text";
        return `
          <td>
            <input
              type="${inputType}"
              class="spreadsheet-cell-input"
              data-column-id="${column.column_id}"
              data-column-type="${column.type}"
            />
          </td>
        `;
      })
      .join("");
    const rowsMarkup = spreadsheetState.rows
      .map((row) => {
        const cells = columns
          .map((column) => {
            const cellValue = row.values[column.column_id];
            if (column.type === "bool") {
              return `
                <td>
                  <input
                    type="checkbox"
                    class="spreadsheet-cell-input"
                    data-row-id="${row.row_id}"
                    data-column-id="${column.column_id}"
                    data-column-type="${column.type}"
                    ${cellValue ? "checked" : ""}
                  />
                </td>
              `;
            }
            const inputType =
              column.type === "date"
                ? "date"
                : column.type === "number"
                  ? "number"
                  : "text";
            const displayValue =
              cellValue === null || cellValue === undefined ? "" : cellValue;
            return `
              <td>
                <input
                  type="${inputType}"
                  class="spreadsheet-cell-input"
                  data-row-id="${row.row_id}"
                  data-column-id="${column.column_id}"
                  data-column-type="${column.type}"
                  value="${displayValue}"
                />
              </td>
            `;
          })
          .join("");
        return `
          <tr data-row-id="${row.row_id}">
            ${cells}
            <td>
              <button type="button" class="secondary" data-action="delete" data-row-id="${row.row_id}">
                Delete
              </button>
            </td>
          </tr>
        `;
      })
      .join("");
    wrapper.innerHTML = `
      <form id="spreadsheet-row-form">
        <table class="spreadsheet-table">
          <thead>
            <tr>
              ${headerCells}
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr class="spreadsheet-new-row">
              ${newRowCells}
              <td>
                <button type="submit">Add row</button>
              </td>
            </tr>
            ${rowsMarkup}
          </tbody>
        </table>
      </form>
    `;

    const rowForm = document.getElementById("spreadsheet-row-form");
    rowForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      setSpreadsheetMessage("");
      const values = {};
      rowForm
        .querySelectorAll(".spreadsheet-new-row .spreadsheet-cell-input")
        .forEach((input) => {
          const columnId = input.dataset.columnId;
          const columnType = input.dataset.columnType;
          if (!columnId) {
            return;
          }
          if (columnType === "bool") {
            values[columnId] = input.checked;
          } else {
            values[columnId] = input.value;
          }
        });

      const response = await fetch(
        `/api/spreadsheets/${projectId}/sheets/${spreadsheetState.sheet.sheet_id}/rows`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ values }),
        },
      );
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        setSpreadsheetMessage(
          payload?.detail || "Unable to add row.",
          true,
        );
        return;
      }
      setSpreadsheetMessage("Row added.");
      rowForm
        .querySelectorAll(".spreadsheet-new-row .spreadsheet-cell-input")
        .forEach((input) => {
          if (input.type === "checkbox") {
            input.checked = false;
          } else {
            input.value = "";
          }
        });
      await loadSpreadsheetSheet(spreadsheetState.sheet.sheet_id);
    });

    wrapper.querySelectorAll("input[data-row-id]").forEach((input) => {
      input.addEventListener("change", async () => {
        setSpreadsheetMessage("");
        const rowId = input.dataset.rowId;
        const columnId = input.dataset.columnId;
        const columnType = input.dataset.columnType;
        if (!rowId || !columnId) {
          return;
        }
        const value =
          columnType === "bool" ? input.checked : input.value;
        const response = await fetch(
          `/api/spreadsheets/${projectId}/sheets/${spreadsheetState.sheet.sheet_id}/rows/${rowId}`,
          {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ values: { [columnId]: value } }),
          },
        );
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          setSpreadsheetMessage(
            payload?.detail || "Unable to update row.",
            true,
          );
          return;
        }
        setSpreadsheetMessage("Row updated.");
      });
    });

    wrapper.querySelectorAll("button[data-action=\"delete\"]").forEach((button) => {
      button.addEventListener("click", async () => {
        const rowId = button.dataset.rowId;
        if (!rowId) {
          return;
        }
        const confirmed = window.confirm("Delete this row?");
        if (!confirmed) {
          return;
        }
        const response = await fetch(
          `/api/spreadsheets/${projectId}/sheets/${spreadsheetState.sheet.sheet_id}/rows/${rowId}`,
          { method: "DELETE" },
        );
        if (!response.ok) {
          setSpreadsheetMessage("Unable to delete row.", true);
          return;
        }
        setSpreadsheetMessage("Row deleted.");
        await loadSpreadsheetSheet(spreadsheetState.sheet.sheet_id);
      });
    });
  };

  const addSpreadsheetColumnRow = (container) => {
    const row = document.createElement("div");
    row.classList.add("spreadsheet-column-row");
    row.innerHTML = `
      <input type="text" placeholder="Column name" required />
      <select>
        <option value="text">Text</option>
        <option value="number">Number</option>
        <option value="date">Date</option>
        <option value="bool">Bool</option>
      </select>
      <label class="spreadsheet-required">
        <input type="checkbox" />
        Required
      </label>
      <button type="button" class="secondary" data-action="remove-column">Remove</button>
    `;
    row
      .querySelector("[data-action=\"remove-column\"]")
      .addEventListener("click", () => {
        if (container.children.length <= 1) {
          setSpreadsheetCreateMessage("At least one column is required.", true);
          return;
        }
        row.remove();
      });
    container.appendChild(row);
  };

  const renderSpreadsheetCanvas = () => {
    const canvas = document.querySelector(".workspace-canvas");
    if (!canvas) {
      return;
    }
    canvas.innerHTML = `
      <div class="spreadsheet-canvas">
        <section class="spreadsheet-header">
          <div class="spreadsheet-sheet-select">
            <label for="spreadsheet-sheet-select">Sheet</label>
            <select id="spreadsheet-sheet-select"></select>
            <button type="button" class="secondary" id="spreadsheet-new-sheet">New sheet</button>
          </div>
          <div class="spreadsheet-actions">
            <button type="button" id="spreadsheet-export">Export CSV</button>
          </div>
        </section>
        <section class="spreadsheet-create-panel is-hidden" id="spreadsheet-create-panel">
          <h3>Create sheet</h3>
          <form id="spreadsheet-create-form">
            <label>
              Sheet name
              <input type="text" id="spreadsheet-sheet-name" required />
            </label>
            <div class="spreadsheet-columns" id="spreadsheet-columns"></div>
            <div class="spreadsheet-column-actions">
              <button type="button" class="secondary" id="spreadsheet-add-column">Add column</button>
            </div>
            <div class="spreadsheet-form-actions">
              <button type="submit">Create sheet</button>
              <button type="button" class="secondary" id="spreadsheet-cancel-create">
                Cancel
              </button>
            </div>
            <p class="spreadsheet-message" id="spreadsheet-create-message" role="status"></p>
          </form>
        </section>
        <section class="spreadsheet-table-panel">
          <div class="spreadsheet-table-header">
            <h3 id="spreadsheet-sheet-title">Spreadsheet</h3>
          </div>
          <div id="spreadsheet-table-wrapper" class="spreadsheet-table-wrapper"></div>
          <p class="spreadsheet-message" id="spreadsheet-message" role="status"></p>
        </section>
        <section class="spreadsheet-import">
          <h3>Import CSV</h3>
          <form id="spreadsheet-import-form">
            <textarea id="spreadsheet-import-text" rows="6" placeholder="Paste CSV content..."></textarea>
            <div class="spreadsheet-import-actions">
              <button type="submit">Import CSV</button>
            </div>
            <p class="spreadsheet-message" id="spreadsheet-import-message" role="status"></p>
          </form>
        </section>
      </div>
    `;

    if (workspaceState?.last_opened_sheet_id) {
      spreadsheetState.selectedSheetId = workspaceState.last_opened_sheet_id;
    }
    const select = document.getElementById("spreadsheet-sheet-select");
    select.addEventListener("change", async () => {
      spreadsheetState.selectedSheetId = select.value || null;
      await loadSpreadsheetSheet(spreadsheetState.selectedSheetId);
    });

    const createPanel = document.getElementById("spreadsheet-create-panel");
    const newSheetButton = document.getElementById("spreadsheet-new-sheet");
    const cancelCreateButton = document.getElementById("spreadsheet-cancel-create");
    const columnsContainer = document.getElementById("spreadsheet-columns");

    const showCreatePanel = (show) => {
      createPanel.classList.toggle("is-hidden", !show);
    };

    newSheetButton.addEventListener("click", () => {
      setSpreadsheetCreateMessage("");
      showCreatePanel(true);
    });

    cancelCreateButton.addEventListener("click", () => {
      showCreatePanel(false);
    });

    addSpreadsheetColumnRow(columnsContainer);

    document
      .getElementById("spreadsheet-add-column")
      .addEventListener("click", () => {
        addSpreadsheetColumnRow(columnsContainer);
      });

    document
      .getElementById("spreadsheet-create-form")
      .addEventListener("submit", async (event) => {
        event.preventDefault();
        setSpreadsheetCreateMessage("");
        const name = document.getElementById("spreadsheet-sheet-name").value.trim();
        if (!name) {
          setSpreadsheetCreateMessage("Sheet name is required.", true);
          return;
        }
        const columns = [];
        columnsContainer.querySelectorAll(".spreadsheet-column-row").forEach((row) => {
          const nameInput = row.querySelector("input[type=\"text\"]");
          const typeSelect = row.querySelector("select");
          const requiredInput = row.querySelector("input[type=\"checkbox\"]");
          const columnName = nameInput.value.trim();
          if (!columnName) {
            return;
          }
          columns.push({
            name: columnName,
            type: typeSelect.value,
            required: requiredInput.checked,
          });
        });
        if (!columns.length) {
          setSpreadsheetCreateMessage("Add at least one column.", true);
          return;
        }
        const response = await fetch(`/api/spreadsheets/${projectId}/sheets`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name, columns }),
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          setSpreadsheetCreateMessage(
            payload?.detail || "Unable to create sheet.",
            true,
          );
          return;
        }
        setSpreadsheetCreateMessage("Sheet created.");
        document.getElementById("spreadsheet-sheet-name").value = "";
        columnsContainer.innerHTML = "";
        addSpreadsheetColumnRow(columnsContainer);
        showCreatePanel(false);
        spreadsheetState.selectedSheetId = payload.sheet_id;
        await loadSpreadsheetSheets();
      });

    document
      .getElementById("spreadsheet-export")
      .addEventListener("click", async () => {
        if (!spreadsheetState.sheet) {
          setSpreadsheetMessage("Select a sheet to export.", true);
          return;
        }
        const response = await fetch(
          `/api/spreadsheets/${projectId}/sheets/${spreadsheetState.sheet.sheet_id}/export.csv`,
        );
        if (!response.ok) {
          setSpreadsheetMessage("Unable to export CSV.", true);
          return;
        }
        const csvText = await response.text();
        const blob = new Blob([csvText], { type: "text/csv" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `${spreadsheetState.sheet.name}.csv`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
      });

    document
      .getElementById("spreadsheet-import-form")
      .addEventListener("submit", async (event) => {
        event.preventDefault();
        setSpreadsheetImportMessage("");
        if (!spreadsheetState.sheet) {
          setSpreadsheetImportMessage("Select a sheet to import into.", true);
          return;
        }
        const textArea = document.getElementById("spreadsheet-import-text");
        const csvPayload = textArea.value.trim();
        if (!csvPayload) {
          setSpreadsheetImportMessage("Paste CSV content to import.", true);
          return;
        }
        const response = await fetch(
          `/api/spreadsheets/${projectId}/sheets/${spreadsheetState.sheet.sheet_id}/import.csv`,
          {
            method: "POST",
            headers: { "Content-Type": "text/csv" },
            body: csvPayload,
          },
        );
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          setSpreadsheetImportMessage(
            payload?.detail || "Unable to import CSV.",
            true,
          );
          return;
        }
        setSpreadsheetImportMessage(
          `Imported ${payload.imported} row(s).`,
        );
        textArea.value = "";
        await loadSpreadsheetSheet(spreadsheetState.sheet.sheet_id);
      });

    loadSpreadsheetSheets();
  };

  const renderPlaceholder = (tabName) => {
    const canvas = document.querySelector(".workspace-canvas");
    if (!canvas) {
      return;
    }
    canvas.innerHTML = `<p>${tabName} canvas is not available in this view.</p>`;
  };

  const updateDashboardErrorBanner = () => {
    const banner = document.getElementById("dashboard-error");
    if (!banner) {
      return;
    }
    const messages = Object.values(dashboardState.errors).filter(Boolean);
    if (!messages.length) {
      banner.classList.add("is-hidden");
      banner.innerHTML = "";
      return;
    }
    banner.classList.remove("is-hidden");
    banner.innerHTML = `
      <strong>Dashboard data unavailable:</strong>
      <ul>${messages.map((message) => `<li>${message}</li>`).join("")}</ul>
    `;
  };

  const formatScore = (value) => {
    if (typeof value !== "number") {
      return "--";
    }
    return value.toFixed(2);
  };

  const formatTimestamp = (value) => {
    if (!value) {
      return "--";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }
    return date.toLocaleString();
  };

  const formatPercent = (value) => {
    if (typeof value !== "number") {
      return "--";
    }
    return `${Math.round(value * 100)}%`;
  };

  const formatKpiValue = (kpi) => {
    if (!kpi || typeof kpi.value !== "number") {
      return "--";
    }
    if (kpi.unit === "M") {
      return `$${kpi.value.toFixed(1)}M`;
    }
    if (kpi.unit === "ratio") {
      return formatPercent(kpi.value);
    }
    if (kpi.unit === "%") {
      return `${Math.round(kpi.value)}%`;
    }
    return kpi.value.toFixed(1);
  };

  const loadChartJs = () => {
    if (window.Chart) {
      return Promise.resolve();
    }
    if (dashboardState.chartLoader) {
      return dashboardState.chartLoader;
    }
    dashboardState.chartLoader = new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = "https://cdn.jsdelivr.net/npm/chart.js";
      script.async = true;
      script.onload = () => resolve();
      script.onerror = () => reject(new Error("Chart.js failed to load"));
      document.head.appendChild(script);
    });
    return dashboardState.chartLoader;
  };

  const destroyDashboardCharts = () => {
    dashboardState.charts.forEach((chart) => chart.destroy());
    dashboardState.charts.clear();
  };

  const renderHealthMetrics = (metrics) => {
    const body = document.getElementById("dashboard-metrics-body");
    if (!body) {
      return;
    }
    if (!metrics || !Object.keys(metrics).length) {
      body.innerHTML = "<tr><td colspan=\"4\">No metrics available.</td></tr>";
      return;
    }
    body.innerHTML = Object.entries(metrics)
      .map(([name, metric]) => {
        const rawValue =
          typeof metric.raw === "number" ? metric.raw.toFixed(2) : metric.raw || "--";
        return `
          <tr>
            <td>${name}</td>
            <td>${formatScore(metric.score)}</td>
            <td>
              <span class="dashboard-pill ${metric.status}">
                ${metric.status}
              </span>
            </td>
            <td>${rawValue}</td>
          </tr>
        `;
      })
      .join("");
  };

  const renderTrendTable = (points) => {
    const body = document.getElementById("dashboard-trends-body");
    if (!body) {
      return;
    }
    if (!points || !points.length) {
      body.innerHTML = "<tr><td colspan=\"2\">No trend data yet.</td></tr>";
      return;
    }
    body.innerHTML = points
      .map(
        (point) => `
          <tr>
            <td>${formatTimestamp(point.timestamp)}</td>
            <td>${formatScore(point.composite_score)}</td>
          </tr>
        `,
      )
      .join("");
  };

  const renderQualitySummary = (payload) => {
    const scoreValue = document.getElementById("dashboard-quality-score-value");
    const eventsValue = document.getElementById("dashboard-quality-events-value");
    const entityList = document.getElementById("dashboard-quality-entity-list");
    if (scoreValue) {
      scoreValue.textContent = formatScore(payload?.average_score);
    }
    if (eventsValue) {
      eventsValue.textContent = payload?.total_events ?? "--";
    }
    if (entityList) {
      const entries = Object.entries(payload?.by_entity || {});
      if (!entries.length) {
        entityList.innerHTML = "<li>No entity scores yet.</li>";
      } else {
        entityList.innerHTML = entries
          .map(
            ([name, score]) =>
              `<li><strong>${name}</strong>: ${formatScore(score)}</li>`,
          )
          .join("");
      }
    }
  };

  const renderPortfolioKpis = (kpis) => {
    const container = document.getElementById("portfolio-kpi-grid");
    if (!container) {
      return;
    }
    if (!kpis || !kpis.length) {
      container.innerHTML = "<p>No KPI data available.</p>";
      return;
    }
    container.innerHTML = kpis
      .map(
        (kpi) => `
          <div class="dashboard-kpi-card">
            <p class="dashboard-label">${kpi.label}</p>
            <p class="dashboard-value">${formatKpiValue(kpi)}</p>
            <p class="dashboard-subtext">
              Target: ${formatKpiValue({ ...kpi, value: kpi.target })}
            </p>
          </div>
        `,
      )
      .join("");
  };

  const renderLifecycleStages = (stages) => {
    const container = document.getElementById("lifecycle-stage-list");
    if (!container) {
      return;
    }
    if (!stages || !stages.length) {
      container.innerHTML = "<p>No stage-gate data available.</p>";
      return;
    }
    container.innerHTML = stages
      .map(
        (stage) => `
          <div class="stage-gate-card">
            <div class="stage-gate-header">
              <button type="button" class="stage-gate-button" data-stage-id="${stage.stage_id}">
                ${stage.stage_name}
              </button>
              <span class="stage-gate-status ${stage.status}">${stage.status.replace("_", " ")}</span>
            </div>
            <div class="stage-gate-progress">
              <div class="stage-gate-bar" style="width: ${stage.percent_complete || 0}%"></div>
            </div>
            <div class="stage-gate-meta">
              <span>${stage.percent_complete || 0}% complete</span>
              <span>${stage.gate || "Gate review"}</span>
            </div>
          </div>
        `,
      )
      .join("");

    document.querySelectorAll(".stage-gate-button").forEach((button) => {
      button.addEventListener("click", async () => {
        const stageId = button.dataset.stageId;
        if (!stageId || !workspaceState) {
          return;
        }
        const stage = workspaceState.methodology_map_summary.stages.find(
          (entry) => entry.id === stageId,
        );
        const activity = stage?.activities?.[0];
        if (!activity) {
          return;
        }
        const payload = await postSelection({
          current_canvas_tab: activity.recommended_canvas_tab,
          current_stage_id: stage.id,
          current_activity_id: activity.id,
          methodology: workspaceState.methodology,
        });
        if (payload) {
          updateWorkspaceUI(payload);
        }
      });
    });
  };

  const renderPortfolioChart = async (kpis) => {
    const canvas = document.getElementById("portfolio-health-chart");
    if (!canvas) {
      return;
    }
    try {
      await loadChartJs();
    } catch (error) {
      return;
    }
    if (!window.Chart || !kpis?.length) {
      return;
    }
    const labels = kpis.map((kpi) => kpi.label);
    const values = kpis.map((kpi) =>
      typeof kpi.value === "number" ? kpi.value * (kpi.unit === "ratio" ? 100 : 1) : 0,
    );
    const chart = new window.Chart(canvas.getContext("2d"), {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: "KPI value",
            data: values,
            backgroundColor: "#2563eb",
          },
        ],
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true },
        },
      },
    });
    dashboardState.charts.set("portfolio", chart);
  };

  const renderLifecycleChart = async (stages) => {
    const canvas = document.getElementById("lifecycle-stage-chart");
    if (!canvas) {
      return;
    }
    try {
      await loadChartJs();
    } catch (error) {
      return;
    }
    if (!window.Chart || !stages?.length) {
      return;
    }
    const labels = stages.map((stage) => stage.stage_name);
    const values = stages.map((stage) => stage.percent_complete || 0);
    const chart = new window.Chart(canvas.getContext("2d"), {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: "% complete",
            data: values,
            backgroundColor: "#10b981",
          },
        ],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { x: { beginAtZero: true, max: 100 } },
      },
    });
    dashboardState.charts.set("lifecycle", chart);
  };

  const loadDashboardPortfolio = async () => {
    const status = document.getElementById("portfolio-health-load-status");
    if (status) {
      status.textContent = "Loading portfolio health...";
    }
    const response = await fetch(`/api/portfolio-health?project_id=${projectId}`);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      dashboardState.errors.portfolio =
        payload?.detail || payload?.message || "Portfolio health failed to load.";
      updateDashboardErrorBanner();
      if (status) {
        status.textContent = "Unable to load portfolio health.";
      }
      return;
    }
    dashboardState.errors.portfolio = "";
    updateDashboardErrorBanner();
    if (status) {
      status.textContent = "Updated just now.";
    }
    renderPortfolioKpis(payload.kpis);
    await renderPortfolioChart(payload.kpis);
  };

  const loadDashboardLifecycle = async () => {
    const status = document.getElementById("lifecycle-metrics-load-status");
    if (status) {
      status.textContent = "Loading lifecycle metrics...";
    }
    const response = await fetch(`/api/lifecycle-metrics?project_id=${projectId}`);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      dashboardState.errors.lifecycle =
        payload?.detail || payload?.message || "Lifecycle metrics failed to load.";
      updateDashboardErrorBanner();
      if (status) {
        status.textContent = "Unable to load lifecycle metrics.";
      }
      return;
    }
    dashboardState.errors.lifecycle = "";
    updateDashboardErrorBanner();
    if (status) {
      status.textContent = "Updated just now.";
    }
    renderLifecycleStages(payload.stage_gates);
    await renderLifecycleChart(payload.stage_gates);
  };

  const loadDashboardHealth = async () => {
    const status = document.getElementById("dashboard-health-load-status");
    if (status) {
      status.textContent = "Loading health summary...";
    }
    const response = await fetch(`/api/dashboard/${projectId}/health`);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      dashboardState.errors.health =
        payload?.detail || payload?.message || "Health summary failed to load.";
      updateDashboardErrorBanner();
      if (status) {
        status.textContent = "Unable to load health summary.";
      }
      return;
    }
    dashboardState.errors.health = "";
    updateDashboardErrorBanner();
    if (status) {
      status.textContent = "Updated just now.";
    }
    document.getElementById("dashboard-health-status-value").textContent =
      payload.health_status || "--";
    document.getElementById("dashboard-health-score-value").textContent = formatScore(
      payload.composite_score,
    );
    document.getElementById("dashboard-health-monitored-value").textContent =
      formatTimestamp(payload.monitored_at);
    renderHealthMetrics(payload.metrics);
  };

  const loadDashboardTrends = async () => {
    const status = document.getElementById("dashboard-trends-load-status");
    if (status) {
      status.textContent = "Loading trend history...";
    }
    const response = await fetch(`/api/dashboard/${projectId}/trends`);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      dashboardState.errors.trends =
        payload?.detail || payload?.message || "Trend history failed to load.";
      updateDashboardErrorBanner();
      if (status) {
        status.textContent = "Unable to load trends.";
      }
      return;
    }
    dashboardState.errors.trends = "";
    updateDashboardErrorBanner();
    if (status) {
      status.textContent = `Showing ${payload.points?.length || 0} points.`;
    }
    renderTrendTable(payload.points || []);
  };

  const loadDashboardQuality = async () => {
    const status = document.getElementById("dashboard-quality-load-status");
    if (status) {
      status.textContent = "Loading quality summary...";
    }
    const response = await fetch(`/api/dashboard/${projectId}/quality`);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      dashboardState.errors.quality =
        payload?.detail || payload?.message || "Quality summary failed to load.";
      updateDashboardErrorBanner();
      if (status) {
        status.textContent = "Unable to load quality summary.";
      }
      return;
    }
    dashboardState.errors.quality = "";
    updateDashboardErrorBanner();
    if (status) {
      status.textContent = "Updated just now.";
    }
    renderQualitySummary(payload);
  };

  const renderDashboardCanvas = () => {
    const canvas = document.querySelector(".workspace-canvas");
    if (!canvas) {
      return;
    }
    destroyDashboardCharts();
    canvas.innerHTML = `
      <div class="dashboard-canvas">
        <div class="dashboard-error is-hidden" id="dashboard-error" role="alert"></div>
        <section class="dashboard-portfolio-card">
          <div class="dashboard-card-header">
            <h3>Portfolio health</h3>
            <span class="dashboard-subtext" id="portfolio-health-load-status">Loading...</span>
          </div>
          <div class="dashboard-kpi-grid" id="portfolio-kpi-grid">
            <p>Loading KPIs...</p>
          </div>
          <div class="dashboard-chart">
            <canvas id="portfolio-health-chart" height="160"></canvas>
          </div>
        </section>
        <section class="dashboard-lifecycle-card">
          <div class="dashboard-card-header">
            <h3>Lifecycle stage-gates</h3>
            <span class="dashboard-subtext" id="lifecycle-metrics-load-status">Loading...</span>
          </div>
          <div class="dashboard-stage-list" id="lifecycle-stage-list">
            <p>Loading stage-gate progress...</p>
          </div>
          <div class="dashboard-chart">
            <canvas id="lifecycle-stage-chart" height="200"></canvas>
          </div>
        </section>
        <section class="dashboard-summary-card">
          <div class="dashboard-card-header">
            <h3>Project health summary</h3>
            <span class="dashboard-subtext" id="dashboard-health-load-status">Loading...</span>
          </div>
          <div class="dashboard-summary-grid">
            <div class="dashboard-summary-item">
              <p class="dashboard-label">Health status</p>
              <p class="dashboard-value" id="dashboard-health-status-value">--</p>
            </div>
            <div class="dashboard-summary-item">
              <p class="dashboard-label">Composite score</p>
              <p class="dashboard-value" id="dashboard-health-score-value">--</p>
            </div>
            <div class="dashboard-summary-item">
              <p class="dashboard-label">Monitored at</p>
              <p class="dashboard-value" id="dashboard-health-monitored-value">--</p>
            </div>
          </div>
        </section>
        <section class="dashboard-metrics-card">
          <div class="dashboard-card-header">
            <h3>Metric breakdown</h3>
          </div>
          <table class="dashboard-table">
            <thead>
              <tr>
                <th>Metric</th>
                <th>Score</th>
                <th>Status</th>
                <th>Raw</th>
              </tr>
            </thead>
            <tbody id="dashboard-metrics-body">
              <tr><td colspan="4">Loading metrics...</td></tr>
            </tbody>
          </table>
        </section>
        <section class="dashboard-trends-card">
          <div class="dashboard-card-header">
            <h3>Health trends</h3>
            <span class="dashboard-subtext" id="dashboard-trends-load-status">Loading...</span>
          </div>
          <table class="dashboard-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Composite score</th>
              </tr>
            </thead>
            <tbody id="dashboard-trends-body">
              <tr><td colspan="2">Loading trends...</td></tr>
            </tbody>
          </table>
        </section>
        <section class="dashboard-quality-card">
          <div class="dashboard-card-header">
            <h3>Data quality summary</h3>
            <span class="dashboard-subtext" id="dashboard-quality-load-status">Loading...</span>
          </div>
          <div class="dashboard-summary-grid">
            <div class="dashboard-summary-item">
              <p class="dashboard-label">Average score</p>
              <p class="dashboard-value" id="dashboard-quality-score-value">--</p>
            </div>
            <div class="dashboard-summary-item">
              <p class="dashboard-label">Events tracked</p>
              <p class="dashboard-value" id="dashboard-quality-events-value">--</p>
            </div>
          </div>
          <div>
            <p class="dashboard-label">Scores by entity</p>
            <ul class="dashboard-quality-list" id="dashboard-quality-entity-list">
              <li>Loading quality metrics...</li>
            </ul>
          </div>
        </section>
        <section class="dashboard-whatif-card">
          <div class="dashboard-card-header">
            <h3>What-if request</h3>
          </div>
          <form id="dashboard-whatif-form">
            <label>
              Scenario
              <input type="text" id="dashboard-whatif-scenario" required />
            </label>
            <label>
              Adjustments (JSON)
              <textarea id="dashboard-whatif-adjustments" rows="4" placeholder='{"risk_score": 0.15}'></textarea>
            </label>
            <p class="dashboard-message is-error is-hidden" id="dashboard-adjustments-error"></p>
            <button type="submit">Submit what-if</button>
            <p class="dashboard-message" id="dashboard-whatif-status" role="status" aria-live="polite"></p>
            <div class="dashboard-whatif-result" id="dashboard-whatif-result"></div>
          </form>
        </section>
      </div>
    `;

    const adjustmentsInput = document.getElementById("dashboard-whatif-adjustments");
    const adjustmentsError = document.getElementById("dashboard-adjustments-error");
    const form = document.getElementById("dashboard-whatif-form");
    const status = document.getElementById("dashboard-whatif-status");
    const result = document.getElementById("dashboard-whatif-result");

    const setWhatIfStatus = (message, isError = false) => {
      if (!status) {
        return;
      }
      status.textContent = message;
      status.classList.toggle("is-error", isError);
    };

    const setAdjustmentsError = (message) => {
      if (!adjustmentsError) {
        return;
      }
      adjustmentsError.textContent = message;
      adjustmentsError.classList.toggle("is-hidden", !message);
    };

    const parseAdjustments = () => {
      if (!adjustmentsInput) {
        return { value: {}, error: "" };
      }
      const raw = adjustmentsInput.value.trim();
      if (!raw) {
        return { value: {}, error: "" };
      }
      try {
        const parsed = JSON.parse(raw);
        if (parsed === null || Array.isArray(parsed) || typeof parsed !== "object") {
          return { value: {}, error: "Adjustments must be a JSON object." };
        }
        return { value: parsed, error: "" };
      } catch (error) {
        return { value: {}, error: "Adjustments must be valid JSON." };
      }
    };

    if (adjustmentsInput) {
      adjustmentsInput.addEventListener("input", () => {
        const { error } = parseAdjustments();
        setAdjustmentsError(error);
      });
    }

    if (form) {
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        setWhatIfStatus("");
        setAdjustmentsError("");
        if (result) {
          result.innerHTML = "";
        }

        const scenario = document
          .getElementById("dashboard-whatif-scenario")
          .value.trim();
        if (!scenario) {
          setWhatIfStatus("Scenario is required.", true);
          return;
        }

        const { value, error } = parseAdjustments();
        if (error) {
          setAdjustmentsError(error);
          return;
        }

        const response = await fetch(`/api/dashboard/${projectId}/what-if`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ scenario, adjustments: value }),
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          setWhatIfStatus(
            payload?.detail || payload?.message || "Unable to submit what-if request.",
            true,
          );
          return;
        }
        setWhatIfStatus("Scenario submitted for analysis.");
        if (result) {
          result.innerHTML = `
            <div><strong>Scenario ID:</strong> ${payload.scenario_id || "--"}</div>
            <div><strong>Status:</strong> ${payload.status || "--"}</div>
            <div><strong>Message:</strong> ${payload.message || "--"}</div>
          `;
        }
      });
    }

    loadDashboardPortfolio();
    loadDashboardLifecycle();
    loadDashboardHealth();
    loadDashboardTrends();
    loadDashboardQuality();
  };

  const renderCanvas = (tabName) => {
    if (tabName === "document") {
      renderDocumentCanvas();
      renderDocumentDetail(documentState.selected);
    } else if (tabName === "tree") {
      renderTreeCanvas();
    } else if (tabName === "timeline") {
      renderTimelineCanvas();
    } else if (tabName === "spreadsheet") {
      renderSpreadsheetCanvas();
    } else if (tabName === "dashboard") {
      renderDashboardCanvas();
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
    const sendButton = document.getElementById("assistant-send");
    const setAssistantStatus = (message, isError = false) => {
      if (!status) {
        return;
      }
      status.textContent = message;
      status.classList.toggle("is-error", isError);
    };

    const updateSendState = () => {
      if (!sendButton || !promptBox) {
        return;
      }
      sendButton.disabled = !promptBox.value.trim();
    };

    document.querySelectorAll(".assistant-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        if (!promptBox) {
          return;
        }
        promptBox.value = chip.dataset.prompt || chip.textContent.trim();
        setAssistantStatus("");
        updateSendState();
      });
    });

    if (promptBox) {
      promptBox.addEventListener("input", () => {
        updateSendState();
        setAssistantStatus("");
      });
    }

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
        updateSendState();
      });
    }

    if (sendButton) {
      sendButton.addEventListener("click", async () => {
        if (!promptBox) {
          return;
        }
        const message = promptBox.value.trim();
        if (!message) {
          setAssistantStatus("Add a prompt before sending.", true);
          updateSendState();
          return;
        }
        const timestamp = new Date().toISOString();
        pushTranscriptEntry({ role: "user", text: message, timestamp });
        setAssistantStatus("Sending request...");
        sendButton.disabled = true;
        try {
          const response = await fetch("/api/assistant/send", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ project_id: projectId, message }),
          });
          const payload = await response.json().catch(() => ({}));
          if (!response.ok) {
            const errorDetail =
              payload.detail ||
              payload.error ||
              payload.message ||
              "Assistant request failed.";
            pushTranscriptEntry({
              role: "assistant",
              text: typeof errorDetail === "string" ? errorDetail : JSON.stringify(errorDetail),
              timestamp: new Date().toISOString(),
              correlation_id: payload.correlation_id,
              isError: true,
            });
            setAssistantStatus("Assistant request failed.", true);
            updateSendState();
            return;
          }
          const assistantResponse = payload.response;
          const assistantText = extractAssistantText(assistantResponse);
          pushTranscriptEntry({
            role: "assistant",
            text: assistantText,
            rawResponse: assistantText ? undefined : assistantResponse,
            timestamp: new Date().toISOString(),
            correlation_id: payload.correlation_id,
          });
          setAssistantStatus("Response received.");
          promptBox.value = "";
          updateSendState();
        } catch (error) {
          pushTranscriptEntry({
            role: "assistant",
            text: "Network error while sending assistant request.",
            timestamp: new Date().toISOString(),
            isError: true,
          });
          setAssistantStatus("Network error while sending assistant request.", true);
          updateSendState();
        }
      });
    }

    const pushResearchEntry = (title, html, correlationId) => {
      pushTranscriptEntry({
        role: "assistant",
        html: `<h5>${escapeHtml(title)}</h5>${html}`,
        timestamp: new Date().toISOString(),
        correlation_id: correlationId || null,
      });
    };

    const researchRisksButton = document.getElementById("research-risks");
    if (researchRisksButton) {
      researchRisksButton.addEventListener("click", async () => {
        const context =
          promptBox?.value.trim() ||
          activityIndex.get(workspaceState?.current_activity_id || "")?.description ||
          "Project domain";
        setAssistantStatus("Researching external risks...");
        researchRisksButton.disabled = true;
        try {
          const response = await fetch(`/v1/projects/${projectId}/risks/research`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ context, categories: [] }),
          });
          const payload = await response.json().catch(() => ({}));
          if (!response.ok) {
            setAssistantStatus(payload.detail || "Risk research failed.", true);
            return;
          }
          pushResearchEntry(
            "Risk research results",
            buildRiskResearchHtml(payload),
            payload.correlation_id,
          );
          setAssistantStatus("Risk research complete.");
        } catch (error) {
          setAssistantStatus("Unable to reach risk research endpoint.", true);
        } finally {
          researchRisksButton.disabled = false;
        }
      });
    }

    const researchVendorButton = document.getElementById("research-vendor");
    if (researchVendorButton) {
      researchVendorButton.addEventListener("click", async () => {
        const vendorId = window.prompt("Enter vendor ID");
        if (!vendorId) {
          setAssistantStatus("Vendor ID is required to run research.", true);
          return;
        }
        const domain = window.prompt("Enter vendor domain or category", "general") || "general";
        setAssistantStatus("Researching vendor signals...");
        researchVendorButton.disabled = true;
        try {
          const response = await fetch(`/v1/vendors/${vendorId}/research`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ domain }),
          });
          const payload = await response.json().catch(() => ({}));
          if (!response.ok) {
            setAssistantStatus(payload.detail || "Vendor research failed.", true);
            return;
          }
          pushResearchEntry(
            "Vendor research results",
            buildVendorResearchHtml(payload),
            payload.correlation_id,
          );
          setAssistantStatus("Vendor research complete.");
        } catch (error) {
          setAssistantStatus("Unable to reach vendor research endpoint.", true);
        } finally {
          researchVendorButton.disabled = false;
        }
      });
    }

    const researchComplianceButton = document.getElementById("research-compliance");
    if (researchComplianceButton) {
      researchComplianceButton.addEventListener("click", async () => {
        const domain = window.prompt("Enter project domain for monitoring", "general") || "general";
        const region = window.prompt("Enter region (optional)", "") || null;
        setAssistantStatus("Monitoring regulatory updates...");
        researchComplianceButton.disabled = true;
        try {
          const response = await fetch(
            `/v1/projects/${projectId}/compliance/research`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ domain, region }),
            },
          );
          const payload = await response.json().catch(() => ({}));
          if (!response.ok) {
            setAssistantStatus(payload.detail || "Compliance monitoring failed.", true);
            return;
          }
          pushResearchEntry(
            "Regulatory monitoring results",
            buildComplianceResearchHtml(payload),
            payload.correlation_id,
          );
          setAssistantStatus("Regulatory monitoring complete.");
        } catch (error) {
          setAssistantStatus("Unable to reach compliance research endpoint.", true);
        } finally {
          researchComplianceButton.disabled = false;
        }
      });
    }

    updateSendState();
    renderAssistantTranscript();
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

  const escapeHtml = (value) =>
    String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\"/g, "&quot;")
      .replace(/'/g, "&#39;");

  const attachTemplateHandlers = () => {
    document.querySelectorAll(".template-tab").forEach((button) => {
      button.addEventListener("click", () => {
        const filter = button.dataset.templateFilter || "all";
        templatesState.filter = filter;
        document.querySelectorAll(".template-tab").forEach((item) => {
          const isActive = item === button;
          item.classList.toggle("is-active", isActive);
          item.setAttribute("aria-selected", isActive ? "true" : "false");
        });
        loadTemplates();
      });
    });

    const searchInput = document.getElementById("template-search");
    if (searchInput) {
      searchInput.addEventListener("input", () => {
        templatesState.query = searchInput.value.trim();
        loadTemplates();
      });
    }
  };

  const extractAssistantText = (payload) => {
    if (!payload || typeof payload !== "object") {
      return null;
    }
    const direct = ["message", "answer", "text", "content"];
    for (const key of direct) {
      if (typeof payload[key] === "string" && payload[key].trim()) {
        return payload[key];
      }
    }
    if (payload.data && typeof payload.data === "object") {
      for (const key of direct) {
        if (typeof payload.data[key] === "string" && payload.data[key].trim()) {
          return payload.data[key];
        }
      }
    }
    return null;
  };

  const renderSourceLinks = (sources) => {
    if (!Array.isArray(sources) || !sources.length) {
      return "";
    }
    const items = sources
      .map((source) => {
        const url = source.url || source.source_url || "";
        const label = source.citation || url || "Source";
        if (!url) {
          return `<li>${escapeHtml(label)}</li>`;
        }
        return `<li><a href="${escapeHtml(url)}" target="_blank" rel="noreferrer">${escapeHtml(
          label,
        )}</a></li>`;
      })
      .join("");
    return `<ul class="assistant-source-list">${items}</ul>`;
  };

  const buildRiskResearchHtml = (payload) => {
    const risks = payload?.external_risks || [];
    if (!risks.length) {
      return "<p>No external risks were identified.</p>";
    }
    const items = risks
      .map((risk) => {
        const sources = renderSourceLinks(risk.sources || []);
        return `<li>
            <strong>${escapeHtml(risk.title || "Risk")}</strong>
            <span class="assistant-tag">${escapeHtml(risk.category || "technical")}</span>
            <div class="assistant-meta">Probability: ${escapeHtml(
              String(risk.probability ?? ""),
            )} | Impact: ${escapeHtml(String(risk.impact ?? ""))}</div>
            <p>${escapeHtml(risk.description || "")}</p>
            ${sources}
          </li>`;
      })
      .join("");
    return `<ul class="assistant-research-list">${items}</ul>`;
  };

  const buildVendorResearchHtml = (payload) => {
    const summary = payload?.summary ? `<p>${escapeHtml(payload.summary)}</p>` : "";
    const insights = payload?.insights || [];
    const insightItems = insights.length
      ? `<ul class="assistant-research-list">${insights
          .map(
            (insight) => `<li>
              <strong>${escapeHtml(insight.category || "signal")}</strong>
              <span class="assistant-tag">${escapeHtml(insight.sentiment || "neutral")}</span>
              <p>${escapeHtml(insight.detail || "")}</p>
            </li>`,
          )
          .join("")}</ul>`
      : "<p>No vendor insights were extracted.</p>";
    const sources = renderSourceLinks(payload?.sources || []);
    return `${summary}${insightItems}${sources}`;
  };

  const buildComplianceResearchHtml = (payload) => {
    const monitoring = payload?.external_monitoring || {};
    const summary = monitoring?.summary ? `<p>${escapeHtml(monitoring.summary)}</p>` : "";
    const updates = monitoring?.updates || [];
    const updateItems = updates.length
      ? `<ul class="assistant-research-list">${updates
          .map(
            (update) => `<li>
              <strong>${escapeHtml(update.regulation || "Regulation")}</strong>
              <p>${escapeHtml(update.description || "")}</p>
              ${update.effective_date ? `<div class="assistant-meta">Effective: ${escapeHtml(update.effective_date)}</div>` : ""}
            </li>`,
          )
          .join("")}</ul>`
      : "<p>No regulatory updates were detected.</p>";
    const gaps = monitoring?.gaps || [];
    const gapItems = gaps.length
      ? `<div class="assistant-gap"><h5>Control gaps</h5><ul class="assistant-research-list">${gaps
          .map(
            (gap) => `<li>${escapeHtml(gap.regulation || "")}: ${escapeHtml(
              gap.recommended_action || "",
            )}</li>`,
          )
          .join("")}</ul></div>`
      : "";
    const sources = renderSourceLinks(monitoring?.sources || []);
    return `${summary}${updateItems}${gapItems}${sources}`;
  };

  const renderAssistantTranscript = () => {
    const transcript = document.getElementById("assistant-transcript");
    if (!transcript) {
      return;
    }
    if (!assistantTranscript.length) {
      transcript.innerHTML =
        "<p class=\"assistant-transcript-empty\" id=\"assistant-transcript-empty\">No assistant messages yet.</p>";
      return;
    }
    transcript.innerHTML = assistantTranscript
      .map((entry) => {
        const timestamp = entry.timestamp
          ? `<span class=\"assistant-message-time\">${escapeHtml(entry.timestamp)}</span>`
          : "";
        const correlationId = entry.correlation_id
          ? `<div class=\"assistant-correlation\">
              <span>correlation_id: <code>${escapeHtml(entry.correlation_id)}</code></span>
              <button type=\"button\" class=\"assistant-copy-correlation\" data-correlation-id=\"${escapeHtml(
                entry.correlation_id,
              )}\">Copy correlation_id</button>
            </div>`
          : "";
        let body = "";
        if (entry.html) {
          body = `<div class=\"assistant-message-text\">${entry.html}</div>`;
        } else if (entry.text) {
          body = `<p class=\"assistant-message-text\">${escapeHtml(entry.text)}</p>`;
        } else if (entry.rawResponse !== undefined) {
          const formatted = escapeHtml(
            typeof entry.rawResponse === "string"
              ? entry.rawResponse
              : JSON.stringify(entry.rawResponse, null, 2),
          );
          body = `
            <details class=\"assistant-message-details\">
              <summary>View response JSON</summary>
              <pre>${formatted}</pre>
            </details>
          `;
        }
        return `
          <div class=\"assistant-message assistant-${entry.role}${
            entry.isError ? " is-error" : ""
          }\">
            <div class=\"assistant-message-header\">
              <span class=\"assistant-message-role\">${escapeHtml(
                entry.role === "user" ? "You" : "Assistant",
              )}</span>
              ${timestamp}
            </div>
            ${body}
            ${correlationId}
          </div>
        `;
      })
      .join("");

    transcript.querySelectorAll(".assistant-copy-correlation").forEach((button) => {
      button.addEventListener("click", async () => {
        const correlationId = button.dataset.correlationId;
        if (!correlationId) {
          return;
        }
        if (!navigator.clipboard) {
          const status = document.getElementById("assistant-status");
          if (status) {
            status.textContent = "Clipboard access is unavailable in this browser.";
            status.classList.add("is-error");
          }
          return;
        }
        try {
          await navigator.clipboard.writeText(correlationId);
          const status = document.getElementById("assistant-status");
          if (status) {
            status.textContent = "Correlation ID copied.";
            status.classList.remove("is-error");
          }
        } catch (error) {
          const status = document.getElementById("assistant-status");
          if (status) {
            status.textContent = "Unable to copy correlation ID.";
            status.classList.add("is-error");
          }
        }
      });
    });
  };

  const pushTranscriptEntry = (entry) => {
    assistantTranscript.push(entry);
    if (assistantTranscript.length > 50) {
      assistantTranscript.shift();
    }
    renderAssistantTranscript();
  };

  tabs.forEach((tab) => {
    const activateTab = () => {
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
    };
    tab.addEventListener("click", activateTab);
    tab.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        activateTab();
      }
      if (event.key === "ArrowRight" || event.key === "ArrowLeft") {
        event.preventDefault();
        const direction = event.key === "ArrowRight" ? 1 : -1;
        const currentIndex = tabs.indexOf(tab);
        const nextIndex = (currentIndex + direction + tabs.length) % tabs.length;
        tabs[nextIndex].focus();
      }
    });
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeWorkspaceNav();
      closeAgentModal();
      closeConnectorModal();
    }
  });

  attachTemplateHandlers();
  attachAgentHandlers();
  attachConnectorHandlers();
  loadTemplates();
  loadConnectorTypes();
  loadConnectorInstances();
  loadWorkspaceState();
};

  if (window.location.pathname === "/workspace") {
    initWorkspace();
  }
