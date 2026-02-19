const setStatus = (element, message, ok = true) => {
  element.textContent = message;
  element.classList.remove("ok", "error");
  element.classList.add(ok ? "ok" : "error");
};

const DEMO_QUERY_PARAM = "demo";
const DEMO_SCENARIO_BASE = "/examples/demo-scenarios";
const DEMO_PROJECT_ID = "demo-1";
const DEMO_PROGRAM_ID = "launch";
const DEMO_SCENARIO_CACHE = new Map();

const isProductionMode = () => {
  const envFlag = document.documentElement?.dataset?.environment;
  if (envFlag) {
    return envFlag === "production";
  }
  const hostname = window.location.hostname;
  return hostname && hostname !== "localhost" && hostname !== "127.0.0.1";
};

const isDemoMode = (searchParams) =>
  searchParams.get(DEMO_QUERY_PARAM) === "true" && !isProductionMode();

const loadDemoScenario = async (filename) => {
  if (DEMO_SCENARIO_CACHE.has(filename)) {
    return DEMO_SCENARIO_CACHE.get(filename);
  }
  const response = await fetch(`${DEMO_SCENARIO_BASE}/${filename}`);
  if (!response.ok) {
    throw new Error(`Unable to load demo scenario: ${filename}`);
  }
  const payload = await response.json();
  DEMO_SCENARIO_CACHE.set(filename, payload);
  return payload;
};

const governancePages = [
  {
    path: "/approvals",
    title: "Approvals",
    description: "Review pending stage-gate and financial approvals with context.",
  },
  {
    path: "/workflow-monitoring",
    title: "Workflow Monitoring",
    description: "Track workflow run health, bottlenecks, and SLA alerts.",
  },
  {
    path: "/document-search",
    title: "Document Search",
    description: "Find artefacts across repositories with filters and previews.",
  },
  {
    path: "/lessons-learned",
    title: "Lessons Learned",
    description: "Capture retrospectives and recommended insights.",
  },
  {
    path: "/audit-log",
    title: "Audit Log",
    description: "Inspect tamper-evident audit entries and evidence packs.",
  },
];

const renderGovernanceLinks = (demoQueryString) => {
  const container = document.getElementById("governance-links-list");
  if (!container) {
    return;
  }
  const querySuffix = demoQueryString ? `?${demoQueryString}` : "";
  const linksMarkup = governancePages
    .map(
      (page) => `
        <li class="list-item">
          <article>
            <a href="${page.path}${querySuffix}">${page.title}</a>
            <p class="meta">${page.description}</p>
          </article>
        </li>
      `,
    )
    .join("");
  container.innerHTML = linksMarkup;
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
  const response = await fetch("/v1/api/workflows/start", {
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

const renderWorkspaceShell = ({ demoQueryString, showDemoControls } = {}) => {
  document.body.classList.add("workspace-body");
  const querySuffix = demoQueryString ? `?${demoQueryString}` : "";
  const demoControlMarkup = showDemoControls
    ? `
        <div class="workspace-demo-actions">
          <button type="button" class="secondary" id="demo-tour-start">
            Start guided tour
          </button>
        </div>
      `
    : "";
  const topNavItems = [
    { path: "/approvals", label: "Approvals" },
    { path: "/workflow-monitoring", label: "Monitoring" },
    { path: "/document-search", label: "Search" },
    { path: "/lessons-learned", label: "Lessons Learned" },
    { path: "/audit-log", label: "Audit Log" },
    { path: "/settings", label: "Settings" },
  ];
  const currentPath = window.location.pathname;
  const topNavLinks = topNavItems
    .map((item) => {
      const isActive =
        currentPath === item.path || currentPath.startsWith(`${item.path}/`);
      return `
        <a
          class="workspace-top-link${isActive ? " is-active" : ""}"
          href="${item.path}${querySuffix}"
          ${isActive ? 'aria-current="page"' : ""}
        >
          ${item.label}
        </a>
      `;
    })
    .join("");
  document.body.innerHTML = `
    <a class="skip-link" href="#workspace-main">Skip to main content</a>
    <div class="workspace-shell">
      <header class="workspace-topbar" role="banner">
        <div class="workspace-topbar-brand">PPM Workspace</div>
        <nav class="workspace-topbar-links" aria-label="Workspace sections">
          ${topNavLinks}
        </nav>
        ${demoControlMarkup}
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
            data-canvas-tab="dependency-map"
            id="canvas-tab-dependency-map"
            tabindex="-1"
          >
            Dependency Map
          </button>
          <button
            class="workspace-tab"
            role="tab"
            aria-selected="false"
            aria-controls="workspace-canvas"
            data-canvas-tab="program-roadmap"
            id="canvas-tab-program-roadmap"
            tabindex="-1"
          >
            Program Roadmap
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
          <p>Select a canvas tab to view its workspace.</p>
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
  const searchParams = new URLSearchParams(window.location.search);
  const demoMode = isDemoMode(searchParams);
  const demoQueryString = demoMode ? `${DEMO_QUERY_PARAM}=true` : "";
  const projectId = demoMode
    ? searchParams.get("project_id") || DEMO_PROJECT_ID
    : searchParams.get("project_id") || "default";
  const programId = demoMode
    ? searchParams.get("program_id") || DEMO_PROGRAM_ID
    : searchParams.get("program_id") || projectId;
  const urlMethodology = searchParams.get("methodology");

  document.body.dataset.demo = demoMode ? "true" : "false";

  renderWorkspaceShell({ demoQueryString, showDemoControls: demoMode });
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
  loadSession(sessionInfo);
  const tabs = Array.from(document.querySelectorAll(".workspace-tab"));
  let workspaceState = null;
  let activityIndex = new Map();
  const dashboardState = {
    charts: new Map(),
    chartLoader: null,
    errors: {
      portfolio: "",
      lifecycle: "",
    },
  };
  const wbsState = {
    items: [],
    draggingId: null,
    lastUpdated: "",
  };
  const scheduleState = {
    tasks: [],
    gantt: null,
    viewMode: "Week",
    loading: null,
  };
  const dependencyMapState = {
    nodes: [],
    links: [],
    simulation: null,
    loading: null,
  };
  const roadmapState = {
    phases: [],
    milestones: [],
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
    try {
      let payload = null;
      if (demoMode) {
        payload = await loadDemoScenario("portfolio-health.json");
      } else {
        const response = await fetch(`/api/portfolio-health?project_id=${projectId}`);
        payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(
            payload?.detail ||
              payload?.message ||
              "Portfolio health failed to load.",
          );
        }
      }
      if (!payload) {
        throw new Error("Missing portfolio health data.");
      }
      dashboardState.errors.portfolio = "";
      if (status) {
        status.textContent = demoMode ? "Demo data loaded." : "Updated just now.";
      }
      renderPortfolioKpis(payload.kpis);
      await renderPortfolioChart(payload.kpis);
    } catch (error) {
      dashboardState.errors.portfolio =
        error?.message || "Portfolio health failed to load.";
      if (status) {
        status.textContent = "Unable to load portfolio health.";
      }
    }
  };

  const loadDashboardLifecycle = async () => {
    const status = document.getElementById("lifecycle-metrics-load-status");
    if (status) {
      status.textContent = "Loading lifecycle metrics...";
    }
    try {
      let payload = null;
      if (demoMode) {
        payload = await loadDemoScenario("lifecycle-metrics.json");
      } else {
        const response = await fetch(`/api/lifecycle-metrics?project_id=${projectId}`);
        payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(
            payload?.detail ||
              payload?.message ||
              "Lifecycle metrics failed to load.",
          );
        }
      }
      if (!payload) {
        throw new Error("Missing lifecycle metrics.");
      }
      dashboardState.errors.lifecycle = "";
      if (status) {
        status.textContent = demoMode ? "Demo data loaded." : "Updated just now.";
      }
      renderLifecycleStages(payload.stage_gates);
      await renderLifecycleChart(payload.stage_gates);
    } catch (error) {
      dashboardState.errors.lifecycle =
        error?.message || "Lifecycle metrics failed to load.";
      if (status) {
        status.textContent = "Unable to load lifecycle metrics.";
      }
    }
  };

  const renderDashboardCanvas = () => {
    const canvas = document.querySelector(".workspace-canvas");
    if (!canvas) {
      return;
    }
    destroyDashboardCharts();
    canvas.innerHTML = `
      <div class="dashboard-canvas">
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
      </div>
    `;

    loadDashboardPortfolio();
    loadDashboardLifecycle();
  };

  const setWbsStatus = (message, isError = false) => {
    const status = document.getElementById("wbs-status");
    if (!status) {
      return;
    }
    status.textContent = message;
    status.classList.toggle("is-error", isError);
  };

  const loadWbs = async () => {
    setWbsStatus("Loading WBS...");
    try {
      let payload = null;
      if (demoMode) {
        payload = await loadDemoScenario("wbs.json");
      } else {
        const response = await fetch(`/api/wbs/${projectId}`);
        if (!response.ok) {
          throw new Error("Unable to load WBS data.");
        }
        payload = await response.json();
      }
      wbsState.items = payload.items || [];
      wbsState.lastUpdated = payload.updated_at || "";
      renderWbsList();
      setWbsStatus(
        demoMode
          ? `${wbsState.items.length} demo WBS items loaded.`
          : `${wbsState.items.length} WBS items loaded.`,
      );
    } catch (error) {
      setWbsStatus("Unable to load WBS data.", true);
    }
  };

  const updateWbsItem = async (itemId, parentId, order) => {
    setWbsStatus("Saving order...");
    const response = await fetch(`/api/wbs/${projectId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ item_id: itemId, parent_id: parentId, order }),
    });
    if (!response.ok) {
      setWbsStatus("Unable to update WBS order.", true);
      return;
    }
    const updated = await response.json();
    wbsState.items = wbsState.items.map((item) =>
      item.id === updated.id ? updated : item,
    );
    renderWbsList();
    setWbsStatus("WBS updated.");
  };

  const renderWbsList = () => {
    const list = document.getElementById("wbs-list");
    if (!list) {
      return;
    }
    const buildItems = (parentId, depth) => {
      return wbsState.items
        .filter((item) => item.parent_id === parentId)
        .sort((a, b) => a.order - b.order)
        .map((item) => {
          const children = buildItems(item.id, depth + 1);
          return `
            <li class="wbs-item" data-item-id="${item.id}" data-parent-id="${item.parent_id || ""}" data-order="${item.order}" style="--wbs-depth: ${depth};">
              <div class="wbs-row" draggable="true">
                <span class="wbs-title">${item.title}</span>
                <span class="wbs-meta">${item.owner || "Unassigned"}</span>
              </div>
              ${children ? `<ul class="wbs-children">${children}</ul>` : ""}
            </li>
          `;
        })
        .join("");
    };
    const markup = buildItems(null, 0);
    list.innerHTML = markup || "<li class=\"wbs-empty\">No WBS items yet.</li>";

    list.querySelectorAll(".wbs-row").forEach((row) => {
      row.addEventListener("dragstart", (event) => {
        const item = row.closest(".wbs-item");
        if (!item || !event.dataTransfer) {
          return;
        }
        wbsState.draggingId = item.dataset.itemId;
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", wbsState.draggingId);
        item.classList.add("is-dragging");
      });
      row.addEventListener("dragend", () => {
        list.querySelectorAll(".wbs-item").forEach((item) => {
          item.classList.remove("is-dragging", "is-drop-target");
        });
        wbsState.draggingId = null;
      });
    });

    list.querySelectorAll(".wbs-item").forEach((item) => {
      item.addEventListener("dragover", (event) => {
        event.preventDefault();
        item.classList.add("is-drop-target");
      });
      item.addEventListener("dragleave", () => {
        item.classList.remove("is-drop-target");
      });
      item.addEventListener("drop", (event) => {
        event.preventDefault();
        item.classList.remove("is-drop-target");
        const targetId = item.dataset.itemId;
        const draggedId =
          event.dataTransfer?.getData("text/plain") || wbsState.draggingId;
        if (!draggedId || draggedId === targetId) {
          return;
        }
        const targetItem = wbsState.items.find((entry) => entry.id === targetId);
        if (!targetItem) {
          return;
        }
        updateWbsItem(draggedId, targetItem.parent_id, targetItem.order + 1);
      });
    });

    list.ondragover = (event) => {
      event.preventDefault();
    };
    list.ondrop = (event) => {
      if (event.target.closest(".wbs-item")) {
        return;
      }
      const draggedId =
        event.dataTransfer?.getData("text/plain") || wbsState.draggingId;
      if (!draggedId) {
        return;
      }
      const maxOrder = Math.max(
        0,
        ...wbsState.items
          .filter((item) => item.parent_id === null)
          .map((item) => item.order),
      );
      updateWbsItem(draggedId, null, maxOrder + 1);
    };
  };

  const loadGanttLibrary = () => {
    if (window.Gantt) {
      return Promise.resolve();
    }
    if (scheduleState.loading) {
      return scheduleState.loading;
    }
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "https://unpkg.com/frappe-gantt@0.6.1/dist/frappe-gantt.css";
    document.head.appendChild(link);
    scheduleState.loading = new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = "https://unpkg.com/frappe-gantt@0.6.1/dist/frappe-gantt.min.js";
      script.onload = () => resolve();
      script.onerror = () => reject(new Error("Unable to load Frappe Gantt."));
      document.body.appendChild(script);
    });
    return scheduleState.loading;
  };

  const loadD3Library = () => {
    if (window.d3) {
      return Promise.resolve();
    }
    if (dependencyMapState.loading) {
      return dependencyMapState.loading;
    }
    dependencyMapState.loading = new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = "https://d3js.org/d3.v7.min.js";
      script.async = true;
      script.onload = () => resolve();
      script.onerror = () => reject(new Error("Unable to load D3.js."));
      document.body.appendChild(script);
    });
    return dependencyMapState.loading;
  };

  const loadSchedule = async () => {
    const status = document.getElementById("gantt-status");
    if (status) {
      status.textContent = "Loading schedule...";
    }
    try {
      let payload = null;
      if (demoMode) {
        payload = await loadDemoScenario("schedule.json");
      } else {
        const response = await fetch(`/api/schedule/${projectId}`);
        if (!response.ok) {
          throw new Error("Unable to load schedule.");
        }
        payload = await response.json();
      }
      scheduleState.tasks = payload.tasks || [];
      if (status) {
        status.textContent = demoMode
          ? `${scheduleState.tasks.length} demo tasks loaded.`
          : `${scheduleState.tasks.length} tasks loaded.`;
        status.classList.remove("is-error");
      }
    } catch (error) {
      if (status) {
        status.textContent = "Unable to load schedule.";
        status.classList.add("is-error");
      }
    }
  };

  const renderGantt = () => {
    const container = document.getElementById("gantt-container");
    if (!container || !window.Gantt) {
      return;
    }
    const tasks = scheduleState.tasks.map((task) => ({
      id: task.id,
      name: task.name,
      start: task.start,
      end: task.end,
      progress: task.progress,
      dependencies: (task.dependencies || []).join(","),
    }));
    scheduleState.gantt = new window.Gantt(container, tasks, {
      view_mode: scheduleState.viewMode,
      bar_height: 26,
      padding: 18,
    });
  };

  const renderWbsCanvas = () => {
    const canvas = document.querySelector(".workspace-canvas");
    if (!canvas) {
      return;
    }
    canvas.innerHTML = `
      <div class="wbs-canvas">
        <header class="wbs-header">
          <div>
            <h3>Work Breakdown Structure</h3>
            <p class="wbs-subtitle">Drag rows to reorder and adjust priorities.</p>
          </div>
          <button type="button" class="secondary" id="wbs-refresh">Refresh</button>
        </header>
        <ul class="wbs-list" id="wbs-list"></ul>
        <p class="wbs-status" id="wbs-status" role="status" aria-live="polite"></p>
      </div>
    `;
    const refreshButton = document.getElementById("wbs-refresh");
    if (refreshButton) {
      refreshButton.addEventListener("click", () => loadWbs());
    }
    loadWbs();
  };

  const updateDependencyDetails = (node) => {
    const details = document.getElementById("dependency-map-details");
    if (!details) {
      return;
    }
    if (!node) {
      details.innerHTML = `
        <p class="dependency-map-empty">Hover a node to see dependency details.</p>
      `;
      return;
    }
    details.innerHTML = `
      <div class="dependency-map-detail-card">
        <h4>${node.label}</h4>
        <p class="dependency-map-detail-type">${node.type}</p>
        <div class="dependency-map-detail-grid">
          <div>
            <span>Status</span>
            <strong>${node.status || "Pending"}</strong>
          </div>
          <div>
            <span>Owner</span>
            <strong>${node.owner || "Unassigned"}</strong>
          </div>
        </div>
        <p class="dependency-map-detail-summary">${node.summary || "No summary provided."}</p>
        ${
          node.url
            ? `<button type="button" class="secondary" data-open-url="${node.url}">
                Open item
              </button>`
            : ""
        }
      </div>
    `;
    const openButton = details.querySelector("[data-open-url]");
    if (openButton) {
      openButton.addEventListener("click", () => {
        const url = openButton.dataset.openUrl;
        if (url) {
          window.location.href = url;
        }
      });
    }
  };

  const renderDependencyMap = () => {
    const container = document.getElementById("dependency-map");
    if (!container || !window.d3) {
      return;
    }
    if (dependencyMapState.simulation) {
      dependencyMapState.simulation.stop();
    }
    container.innerHTML = "";
    const width = container.clientWidth || 640;
    const height = container.clientHeight || 420;
    const svg = window.d3
      .create("svg")
      .attr("viewBox", `0 0 ${width} ${height}`)
      .attr("role", "img")
      .attr("aria-label", "Dependency map visualization");

    const linkGroup = svg.append("g").attr("stroke", "#94a3b8").attr("stroke-opacity", 0.7);
    const nodeGroup = svg.append("g").attr("stroke", "#ffffff").attr("stroke-width", 1.2);

    const tooltip = document.getElementById("dependency-map-tooltip");
    const color = window.d3
      .scaleOrdinal()
      .domain(["program", "project", "task", "milestone"])
      .range(["#2563eb", "#0f766e", "#7c3aed", "#f97316"]);

    const nodes = dependencyMapState.nodes.map((node) => ({ ...node }));
    const links = dependencyMapState.links.map((link) => ({ ...link }));

    const simulation = window.d3
      .forceSimulation(nodes)
      .force(
        "link",
        window.d3
          .forceLink(links)
          .id((d) => d.id)
          .distance(140)
          .strength(0.6),
      )
      .force("charge", window.d3.forceManyBody().strength(-320))
      .force("center", window.d3.forceCenter(width / 2, height / 2))
      .force("collision", window.d3.forceCollide().radius(42));

    const link = linkGroup
      .selectAll("line")
      .data(links)
      .enter()
      .append("line")
      .attr("stroke-width", (d) => (d.critical ? 2.6 : 1.2))
      .attr("stroke-dasharray", (d) => (d.kind === "soft" ? "4 4" : "0"));

    const node = nodeGroup
      .selectAll("circle")
      .data(nodes)
      .enter()
      .append("circle")
      .attr("r", 18)
      .attr("fill", (d) => color(d.type))
      .attr("tabindex", 0)
      .attr("role", "button")
      .attr("aria-label", (d) => `${d.label} dependency node`)
      .on("mouseover", (event, d) => {
        updateDependencyDetails(d);
        if (tooltip) {
          tooltip.classList.add("is-visible");
          tooltip.innerHTML = `
            <strong>${d.label}</strong>
            <span>${d.type} · ${d.status || "pending"}</span>
          `;
        }
      })
      .on("mousemove", (event) => {
        if (!tooltip) {
          return;
        }
        tooltip.style.left = `${event.offsetX + 16}px`;
        tooltip.style.top = `${event.offsetY + 16}px`;
      })
      .on("mouseout", () => {
        updateDependencyDetails(null);
        if (tooltip) {
          tooltip.classList.remove("is-visible");
        }
      })
      .on("keydown", (event, d) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          if (d.url) {
            window.location.href = d.url;
          }
        }
        if (event.key === "Escape" && tooltip) {
          updateDependencyDetails(null);
          tooltip.classList.remove("is-visible");
        }
      })
      .on("click", (event, d) => {
        if (d.url) {
          window.location.href = d.url;
        }
      });

    const label = svg
      .append("g")
      .selectAll("text")
      .data(nodes)
      .enter()
      .append("text")
      .text((d) => d.label)
      .attr("font-size", 11)
      .attr("fill", "#1f2937")
      .attr("text-anchor", "middle")
      .attr("dy", 32);

    simulation.on("tick", () => {
      link
        .attr("x1", (d) => d.source.x)
        .attr("y1", (d) => d.source.y)
        .attr("x2", (d) => d.target.x)
        .attr("y2", (d) => d.target.y);
      node.attr("cx", (d) => d.x).attr("cy", (d) => d.y);
      label.attr("x", (d) => d.x).attr("y", (d) => d.y);
    });

    dependencyMapState.simulation = simulation;
    container.appendChild(svg.node());
  };

  const loadDependencyMap = async () => {
    const status = document.getElementById("dependency-map-status");
    if (status) {
      status.textContent = "Loading dependency map...";
    }
    const response = await fetch(`/api/dependency-map/${programId}`);
    if (!response.ok) {
      if (status) {
        status.textContent = "Unable to load dependency map.";
        status.classList.add("is-error");
      }
      return;
    }
    const payload = await response.json();
    dependencyMapState.nodes = payload.nodes || [];
    dependencyMapState.links = payload.links || [];
    if (status) {
      status.textContent = `${dependencyMapState.nodes.length} nodes loaded.`;
      status.classList.remove("is-error");
    }
  };

  const renderDependencyMapCanvas = () => {
    const canvas = document.querySelector(".workspace-canvas");
    if (!canvas) {
      return;
    }
    canvas.innerHTML = `
      <div class="dependency-map-canvas">
        <header class="dependency-map-header">
          <div>
            <h3>Dependency map</h3>
            <p class="dependency-map-subtitle">Visualize cross-project risks and upstream blockers.</p>
          </div>
          <button type="button" class="secondary" id="dependency-map-refresh">Refresh</button>
        </header>
        <div class="dependency-map-body">
          <div class="dependency-map-chart" id="dependency-map">
            <div class="dependency-map-tooltip" id="dependency-map-tooltip"></div>
          </div>
          <aside class="dependency-map-details" id="dependency-map-details">
            <p class="dependency-map-empty">Hover a node to see dependency details.</p>
          </aside>
        </div>
        <p class="dependency-map-status" id="dependency-map-status" role="status" aria-live="polite"></p>
      </div>
    `;
    const refreshButton = document.getElementById("dependency-map-refresh");
    if (refreshButton) {
      refreshButton.addEventListener("click", () => {
        loadDependencyMap()
          .then(() => renderDependencyMap())
          .catch(() => {
            const status = document.getElementById("dependency-map-status");
            if (status) {
              status.textContent = "Dependency map failed to refresh.";
              status.classList.add("is-error");
            }
          });
      });
    }
    loadD3Library()
      .then(loadDependencyMap)
      .then(() => renderDependencyMap())
      .catch(() => {
        const status = document.getElementById("dependency-map-status");
        if (status) {
          status.textContent = "Dependency map visualization failed to load.";
          status.classList.add("is-error");
        }
      });
  };

  const formatRoadmapDate = (value) => {
    if (!value) {
      return "--";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }
    return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  };

  const renderProgramRoadmapCanvas = () => {
    const canvas = document.querySelector(".workspace-canvas");
    if (!canvas) {
      return;
    }
    canvas.innerHTML = `
      <div class="roadmap-canvas">
        <header class="roadmap-header">
          <div>
            <h3>Program roadmap</h3>
            <p class="roadmap-subtitle">Track phases, milestones, and key delivery checkpoints.</p>
          </div>
          <button type="button" class="secondary" id="roadmap-refresh">Refresh</button>
        </header>
        <div class="roadmap-body" id="roadmap-body">
          <p>Loading roadmap...</p>
        </div>
        <p class="roadmap-status" id="roadmap-status" role="status" aria-live="polite"></p>
      </div>
    `;
    const refreshButton = document.getElementById("roadmap-refresh");
    if (refreshButton) {
      refreshButton.addEventListener("click", () => {
        loadProgramRoadmap();
      });
    }
    loadProgramRoadmap();
  };

  const renderRoadmap = () => {
    const container = document.getElementById("roadmap-body");
    if (!container) {
      return;
    }
    const milestoneLookup = roadmapState.milestones.reduce((acc, milestone) => {
      if (!acc[milestone.phase_id]) {
        acc[milestone.phase_id] = [];
      }
      acc[milestone.phase_id].push(milestone);
      return acc;
    }, {});
    container.innerHTML = roadmapState.phases
      .map((phase) => {
        const milestones = milestoneLookup[phase.id] || [];
        const milestoneMarkup = milestones.length
          ? milestones
              .map(
                (milestone) => `
                  <li>
                    <span class="roadmap-milestone-name">${milestone.name}</span>
                    <span class="roadmap-milestone-date">${formatRoadmapDate(
                      milestone.date,
                    )}</span>
                    <span class="roadmap-milestone-status">${milestone.status}</span>
                  </li>
                `,
              )
              .join("")
          : "<li class=\"roadmap-milestone-empty\">No milestones scheduled.</li>";
        return `
          <section class="roadmap-phase">
            <div class="roadmap-phase-header">
              <div>
                <h4>${phase.name}</h4>
                <p>${phase.summary || "High-level phase delivery summary."}</p>
              </div>
              <div class="roadmap-phase-meta">
                <span>${formatRoadmapDate(phase.start)} → ${formatRoadmapDate(phase.end)}</span>
                <span>${phase.owner || "Unassigned"}</span>
                <span class="roadmap-phase-status">${phase.status}</span>
              </div>
            </div>
            <div class="roadmap-phase-bar">
              <div class="roadmap-phase-progress" style="width: ${phase.progress}%;"></div>
            </div>
            <ul class="roadmap-milestones">${milestoneMarkup}</ul>
          </section>
        `;
      })
      .join("");
  };

  const loadProgramRoadmap = async () => {
    const status = document.getElementById("roadmap-status");
    if (status) {
      status.textContent = "Loading program roadmap...";
    }
    const response = await fetch(`/api/program-roadmap/${programId}`);
    if (!response.ok) {
      if (status) {
        status.textContent = "Unable to load program roadmap.";
        status.classList.add("is-error");
      }
      return;
    }
    const payload = await response.json();
    roadmapState.phases = payload.phases || [];
    roadmapState.milestones = payload.milestones || [];
    renderRoadmap();
    if (status) {
      status.textContent = `${roadmapState.phases.length} phases loaded.`;
      status.classList.remove("is-error");
    }
  };

  const renderTimelineCanvas = () => {
    const canvas = document.querySelector(".workspace-canvas");
    if (!canvas) {
      return;
    }
    canvas.innerHTML = `
      <div class="gantt-canvas">
        <header class="gantt-header">
          <div>
            <h3>Schedule timeline</h3>
            <p class="gantt-subtitle">Review dependencies and adjust delivery windows.</p>
          </div>
          <div class="gantt-controls" role="toolbar" aria-label="Timeline zoom">
            <button type="button" data-gantt-view="Day">Day</button>
            <button type="button" data-gantt-view="Week" class="is-active">Week</button>
            <button type="button" data-gantt-view="Month">Month</button>
          </div>
        </header>
        <div id="gantt-container" class="gantt-container" aria-live="polite"></div>
        <p class="gantt-status" id="gantt-status" role="status" aria-live="polite"></p>
      </div>
    `;

    document.querySelectorAll("[data-gantt-view]").forEach((button) => {
      button.addEventListener("click", () => {
        scheduleState.viewMode = button.dataset.ganttView;
        document.querySelectorAll("[data-gantt-view]").forEach((item) => {
          item.classList.toggle("is-active", item === button);
        });
        if (scheduleState.gantt) {
          scheduleState.gantt.change_view_mode(scheduleState.viewMode);
        }
      });
    });

    loadGanttLibrary()
      .then(loadSchedule)
      .then(() => {
        renderGantt();
      })
      .catch(() => {
        const status = document.getElementById("gantt-status");
        if (status) {
          status.textContent = "Gantt library failed to load.";
          status.classList.add("is-error");
        }
      });
  };

  const renderCanvas = (tabName) => {
    const canvas = document.querySelector(".workspace-canvas");
    if (!canvas) {
      return;
    }
    if (tabName === "dashboard") {
      renderDashboardCanvas();
      return;
    }
    if (tabName === "tree") {
      renderWbsCanvas();
      return;
    }
    if (tabName === "timeline") {
      renderTimelineCanvas();
      return;
    }
    if (tabName === "dependency-map") {
      renderDependencyMapCanvas();
      return;
    }
    if (tabName === "program-roadmap") {
      renderProgramRoadmapCanvas();
      return;
    }
    canvas.innerHTML = `<p>${tabName} canvas is not available in this view.</p>`;
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
    const nextSteps = [];
    if (payload.current_canvas_tab === "tree") {
      nextSteps.push("Drag WBS rows to reprioritize and adjust the hierarchy.");
      nextSteps.push("Drop items on the root area to promote them to the top level.");
      nextSteps.push("Use refresh after collaborating to reload the latest structure.");
    }
    if (payload.current_canvas_tab === "timeline") {
      nextSteps.push("Review dependency links and validate critical path overlaps.");
      nextSteps.push("Use zoom controls to switch between week and month views.");
      nextSteps.push("Confirm schedule dates with delivery owners before exporting.");
    }
    if (payload.current_canvas_tab === "dependency-map") {
      nextSteps.push("Hover nodes to review upstream/downstream dependency context.");
      nextSteps.push("Click an item to open the related project or task.");
      nextSteps.push("Identify critical links and flag blockers early.");
    }
    if (payload.current_canvas_tab === "program-roadmap") {
      nextSteps.push("Review phase owners and confirm milestone dates.");
      nextSteps.push("Use progress bars to spot delivery slippage.");
      nextSteps.push("Align upcoming milestones with governance checkpoints.");
    }
    const nextStepsMarkup = nextSteps.length
      ? `
        <div class="assistant-next-steps">
          <p class="assistant-label">Next steps</p>
          <ul>${nextSteps.map((step) => `<li>${step}</li>`).join("")}</ul>
        </div>
      `
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
        </div>
        <p class="assistant-status" id="assistant-status" role="status" aria-live="polite"></p>
        ${nextStepsMarkup}
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

  const activateTabByName = (tabName) => {
    const targetTab = tabs.find((tab) => tab.dataset.canvasTab === tabName);
    if (targetTab) {
      targetTab.click();
    }
  };

  const loadShepherdAssets = () => {
    if (window.Shepherd) {
      return Promise.resolve();
    }
    return new Promise((resolve, reject) => {
      const stylesheet = document.createElement("link");
      stylesheet.rel = "stylesheet";
      stylesheet.href =
        "https://cdn.jsdelivr.net/npm/shepherd.js@11.2.0/dist/css/shepherd.css";
      document.head.appendChild(stylesheet);

      const script = document.createElement("script");
      script.src =
        "https://cdn.jsdelivr.net/npm/shepherd.js@11.2.0/dist/js/shepherd.min.js";
      script.async = true;
      script.onload = () => resolve();
      script.onerror = () => reject(new Error("Shepherd.js failed to load."));
      document.head.appendChild(script);
    });
  };

  let demoTour = null;

  const buildDemoTour = () => {
    if (!window.Shepherd) {
      return null;
    }
    const tour = new window.Shepherd.Tour({
      useModalOverlay: true,
      defaultStepOptions: {
        cancelIcon: { enabled: true },
        scrollTo: { behavior: "smooth", block: "center" },
      },
    });

    const addStepIfPresent = (step) => {
      if (!step.attachTo?.element) {
        tour.addStep(step);
        return;
      }
      if (document.querySelector(step.attachTo.element)) {
        tour.addStep(step);
      }
    };

    addStepIfPresent({
      id: "login-status",
      title: "Login status",
      text: "Confirm authentication state and tenant context here.",
      attachTo: { element: "#workspace-session", on: "right" },
    });

    addStepIfPresent({
      id: "navigation",
      title: "Navigation hub",
      text: "Jump between governance areas from the top navigation.",
      attachTo: { element: ".workspace-topbar-links", on: "bottom" },
    });

    addStepIfPresent({
      id: "dashboard",
      title: "Dashboard insights",
      text: "Demo KPIs and stage-gate metrics live in the dashboard tab.",
      attachTo: { element: "#canvas-tab-dashboard", on: "bottom" },
      beforeShowPromise: () =>
        new Promise((resolve) => {
          activateTabByName("dashboard");
          setTimeout(resolve, 300);
        }),
    });

    addStepIfPresent({
      id: "wbs",
      title: "WBS editing",
      text: "Drag and reorder work packages to tune scope and ownership.",
      attachTo: { element: "#wbs-list", on: "right" },
      beforeShowPromise: () =>
        new Promise((resolve) => {
          activateTabByName("tree");
          setTimeout(resolve, 300);
        }),
    });

    addStepIfPresent({
      id: "dependency-map",
      title: "Dependency map",
      text: "Visualize upstream blockers and cross-project risks here.",
      attachTo: { element: "#dependency-map", on: "left" },
      beforeShowPromise: () =>
        new Promise((resolve) => {
          activateTabByName("dependency-map");
          setTimeout(resolve, 300);
        }),
    });

    addStepIfPresent({
      id: "approvals",
      title: "Approvals workspace",
      text: "Open approvals to review stage-gate, budget, and vendor decisions.",
      attachTo: { element: 'a[href^="/approvals"]', on: "bottom" },
    });

    addStepIfPresent({
      id: "document-search",
      title: "Document search",
      text: "Search the knowledge base for evidence, risks, and deliverables.",
      attachTo: { element: 'a[href^="/document-search"]', on: "bottom" },
    });

    return tour;
  };

  const startGuidedTour = async () => {
    if (!demoMode || isProductionMode()) {
      return;
    }
    await loadShepherdAssets();
    if (!demoTour) {
      demoTour = buildDemoTour();
    }
    if (demoTour) {
      demoTour.start();
    }
  };

  const skipGuidedTour = () => {
    demoTour?.cancel();
  };

  if (demoMode) {
    window.startGuidedTour = startGuidedTour;
    window.skipGuidedTour = skipGuidedTour;
  }

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
      const tooltip = document.getElementById("dependency-map-tooltip");
      if (tooltip) {
        tooltip.classList.remove("is-visible");
      }
      updateDependencyDetails(null);
    }
  });

  loadWorkspaceState().then(() => {
    if (demoMode) {
      startGuidedTour();
    }
  });

  const startTourButton = document.getElementById("demo-tour-start");
  if (startTourButton) {
    startTourButton.addEventListener("click", () => startGuidedTour());
  }
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

  const searchParams = new URLSearchParams(window.location.search);
  const demoMode = isDemoMode(searchParams);
  const demoQueryString = demoMode ? `${DEMO_QUERY_PARAM}=true` : "";
  renderGovernanceLinks(demoQueryString);
  loadSession(sessionInfo);
};

const renderDemoApprovalData = async () => {
  try {
    const payload = await loadDemoScenario("approvals.json");
    const title = document.getElementById("approval-title");
    if (title && payload?.pending_count !== undefined) {
      title.textContent = `Approvals ▸ Pending (${payload.pending_count})`;
    }
    const queueList = document.getElementById("approval-queue-list");
    if (queueList && Array.isArray(payload?.queues)) {
      queueList.innerHTML = payload.queues
        .map((queue) => `<li class="list-item" role="listitem">${queue}</li>`)
        .join("");
    }
    const approvalsList = document.getElementById("approval-items-list");
    if (approvalsList && Array.isArray(payload?.approvals)) {
      approvalsList.innerHTML = payload.approvals
        .map(
          (item) => `
            <li class="list-item" role="listitem">
              <strong>${item.title}</strong>
              ${item.meta?.map((meta) => `<p class="meta">${meta}</p>`).join("") || ""}
              ${
                item.approvers
                  ? `<p class="meta">Approvers: ${item.approvers}</p>`
                  : ""
              }
            </li>
          `,
        )
        .join("");
    }
    const historyList = document.getElementById("approval-history-list");
    if (historyList && Array.isArray(payload?.history)) {
      historyList.innerHTML = payload.history
        .map(
          (entry) => `
            <li class="list-item" role="listitem">
              <strong>${entry.title}</strong>
              ${entry.meta?.map((meta) => `<p class="meta">${meta}</p>`).join("") || ""}
            </li>
          `,
        )
        .join("");
    }
    const contextArtefact = document.getElementById("approval-context-artefact");
    if (contextArtefact && payload?.context?.artefact) {
      contextArtefact.innerHTML = `<span class="tag">Artefact Preview</span> ${payload.context.artefact}`;
    }
    const contextImpact = document.getElementById("approval-context-impact");
    if (contextImpact && payload?.context?.impact) {
      contextImpact.innerHTML = `<span class="tag">Impact Summary</span> ${payload.context.impact}`;
    }
    const contextFooter = document.getElementById("approval-context-footer");
    if (contextFooter && payload?.context?.footer) {
      contextFooter.textContent = payload.context.footer;
    }
  } catch (error) {
    // Keep default static copy if demo assets are missing.
  }
};

const renderDemoWorkflowMonitoring = async () => {
  try {
    const payload = await loadDemoScenario("workflow-monitoring.json");
    const statusList = document.getElementById("workflow-status-list");
    if (statusList && payload?.status_board) {
      statusList.innerHTML = `
        <li class="list-item" role="listitem">Healthy ${payload.status_board.healthy}</li>
        <li class="list-item" role="listitem">Warning ${payload.status_board.warning}</li>
        <li class="list-item" role="listitem">Failed ${payload.status_board.failed}</li>
      `;
    }
    const runList = document.getElementById("workflow-runs-list");
    if (runList && Array.isArray(payload?.runs)) {
      runList.innerHTML = payload.runs
        .map(
          (run) => `
            <li class="list-item" role="listitem">
              <strong>${run.title} ▸ ${run.status}</strong>
              <p class="meta">Run ${run.run_id} · ${run.duration} · ${run.owner}</p>
            </li>
          `,
        )
        .join("");
    }
    const detailPanel = document.getElementById("workflow-detail-panel");
    if (detailPanel && payload?.detail) {
      detailPanel.innerHTML = `
        <h2>Detail Panel</h2>
        <p><span class="tag">Run</span> ${payload.detail.run_id}</p>
        <p class="meta">${payload.detail.summary}</p>
        <p class="meta">SLA Status: ${payload.detail.sla}</p>
        <div class="actions" aria-label="Run actions">
          <button type="button">Pause</button>
          <button type="button" class="secondary">Rerun</button>
        </div>
      `;
    }
    const alertList = document.getElementById("workflow-alerts-list");
    if (alertList && Array.isArray(payload?.alerts)) {
      alertList.innerHTML = payload.alerts
        .map(
          (alert) => `
            <li class="list-item" role="listitem">
              <strong>${alert.title}</strong>
              <p class="meta">Recommendation: ${alert.recommendation}</p>
            </li>
          `,
        )
        .join("");
    }
  } catch (error) {
    // Keep default static copy if demo assets are missing.
  }
};

const handleRoute = () => {
  const path = window.location.pathname;
  const searchParams = new URLSearchParams(window.location.search);
  const demoMode = isDemoMode(searchParams);
  if (path === "/app") {
    initWorkspace();
    return;
  }
  if (path === "/" || path === "/index.html") {
    initConsole();
    return;
  }
  if (path === "/approvals" && demoMode) {
    renderDemoApprovalData();
    return;
  }
  if (path === "/workflow-monitoring" && demoMode) {
    renderDemoWorkflowMonitoring();
    return;
  }
  if (governancePages.some((page) => page.path === path)) {
    return;
  }
  if (document.getElementById("session-info")) {
    initConsole();
  }
};

window.addEventListener("popstate", handleRoute);
handleRoute();
