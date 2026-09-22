const numberFormat = new Intl.NumberFormat("uk-UA");
const percentFormat = new Intl.NumberFormat("uk-UA", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function el(id) {
  return document.getElementById(id);
}

function formatNumber(value) {
  return value === null || value === undefined ? "—" : numberFormat.format(value);
}

function setStatus(text, type = "") {
  const node = el("api-status");
  node.textContent = text;
  node.className = "status-pill";
  if (type) node.classList.add(type);
}

async function fetchJson(path) {
  const response = await fetch(path);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `${response.status} ${response.statusText}`);
  }
  return response.json();
}

function renderKpis(overview, attribution) {
  el("kpi-events").textContent = formatNumber(overview.events);
  el("kpi-period").textContent = `${overview.first_date || "—"} → ${overview.last_date || "—"}`;
  el("kpi-launched").textContent = formatNumber(overview.launched_known_total);
  el("kpi-destroyed").textContent = formatNumber(overview.destroyed_known_total);
  el("kpi-coverage").textContent = `${percentFormat.format(attribution.coverage_pct)}%`;
  el("kpi-coverage-note").textContent =
    `${formatNumber(attribution.events_with_region_link)} із ${formatNumber(attribution.events)} canonical events`;
}

function renderDailyChart(rows) {
  const ctx = el("daily-chart");
  new Chart(ctx, {
    type: "line",
    data: {
      labels: rows.map((row) => row.date),
      datasets: [{
        label: "Canonical events",
        data: rows.map((row) => row.events),
        borderWidth: 1.5,
        pointRadius: 0,
        tension: 0.12,
        fill: true,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { intersect: false, mode: "index" },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (context) => `Записи: ${formatNumber(context.raw)}`,
          },
        },
      },
      scales: {
        x: {
          ticks: { maxTicksLimit: 12 },
          grid: { display: false },
        },
        y: {
          beginAtZero: true,
          ticks: { precision: 0 },
        },
      },
    },
  });
}

function renderCategoryChart(rows) {
  const ctx = el("category-chart");
  new Chart(ctx, {
    type: "bar",
    data: {
      labels: rows.map((row) => row.category),
      datasets: [{
        label: "Canonical events",
        data: rows.map((row) => row.events),
        borderWidth: 0,
      }],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: {
          beginAtZero: true,
          ticks: { precision: 0 },
        },
        y: { grid: { display: false } },
      },
    },
  });
}

function renderCoverage(data) {
  el("coverage-number").textContent = `${percentFormat.format(data.coverage_pct)}%`;
  el("coverage-text").textContent =
    `${formatNumber(data.events_with_region_link)} з ${formatNumber(data.events)} canonical events мають хоча б один region link.`;
  el("coverage-high").textContent = formatNumber(data.events_with_high_confidence_region);
  el("coverage-medium").textContent = formatNumber(data.events_with_medium_confidence_region);
  el("coverage-low").textContent = formatNumber(data.events_with_low_confidence_region);
}

function renderModels(rows) {
  el("models-body").innerHTML = rows.map((row) => `
    <tr>
      <td>${row.model}</td>
      <td>${row.category}</td>
      <td class="numeric">${formatNumber(row.events)}</td>
    </tr>
  `).join("");
}

function renderRegions(rows) {
  el("regions-body").innerHTML = rows.slice(0, 12).map((row) => {
    const confidence = row.high_confidence_events > 0
      ? `high: ${row.high_confidence_events}`
      : `medium: ${row.medium_confidence_events}`;
    return `
      <tr>
        <td>${row.name_uk || row.name_en}</td>
        <td class="numeric">${formatNumber(row.events)}</td>
        <td><span class="confidence-tag">${confidence}</span></td>
      </tr>
    `;
  }).join("");
}

function renderProvenance(build) {
  const items = [
    ["Build ID", build.build_id],
    ["Transformation", build.transformation_version],
    ["Built at", build.built_at],
    ["Rows loaded", formatNumber(build.rows_loaded)],
    ["Source", build.source_name],
    ["Snapshot", build.source_snapshot],
    ["Source SHA-256", build.source_sha256],
    ["Code commit", build.code_commit_sha || "—"],
  ];
  el("provenance").innerHTML = items.map(([term, value]) => `
    <div><dt>${term}</dt><dd>${value || "—"}</dd></div>
  `).join("");
  el("build-meta").textContent =
    `build ${build.build_id} · ${build.transformation_version}`;
}

async function initializeDashboard() {
  try {
    const health = await fetchJson("/api/health");
    if (health.database !== "ready") {
      setStatus("БД не ініціалізована", "error");
      el("setup-message").classList.remove("hidden");
      return;
    }

    setStatus("SQLite ready", "ready");

    const [
      overview,
      attribution,
      daily,
      categories,
      models,
      regions,
      build,
    ] = await Promise.all([
      fetchJson("/api/stats/overview"),
      fetchJson("/api/stats/attribution"),
      fetchJson("/api/stats/daily"),
      fetchJson("/api/stats/categories"),
      fetchJson("/api/stats/models?limit=12"),
      fetchJson("/api/stats/regions"),
      fetchJson("/api/build/latest"),
    ]);

    renderKpis(overview, attribution);
    renderCoverage(attribution);
    renderModels(models);
    renderRegions(regions);
    renderProvenance(build);

    if (typeof Chart !== "undefined") {
      renderDailyChart(daily);
      renderCategoryChart(categories);
    }

    el("dashboard").classList.remove("hidden");
  } catch (error) {
    console.error(error);
    setStatus("Помилка API", "error");
    const setup = el("setup-message");
    setup.classList.remove("hidden");
    setup.querySelector("p").textContent =
      `Не вдалося завантажити аналітику: ${error.message}`;
  }
}

window.addEventListener("DOMContentLoaded", initializeDashboard);
