const numberFormat = new Intl.NumberFormat("uk-UA");
const percentFormat = new Intl.NumberFormat("uk-UA", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const metricFormat = new Intl.NumberFormat("uk-UA", {
  minimumFractionDigits: 3,
  maximumFractionDigits: 3,
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

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function evidenceColor(events, maxEvents, hasEvidence) {
  if (!hasEvidence) return "#d5dce1";
  const ratio = maxEvents > 0 ? events / maxEvents : 0;
  if (ratio >= 0.75) return "#4f1d1d";
  if (ratio >= 0.50) return "#7c2d2d";
  if (ratio >= 0.25) return "#a94738";
  if (ratio >= 0.10) return "#d57952";
  return "#e9aa77";
}

function renderRegionMap(geojson) {
  const status = el("map-status");

  if (typeof L === "undefined") {
    status.textContent = "Leaflet не завантажився; карта недоступна.";
    return;
  }

  const evidenceValues = geojson.features
    .filter((feature) => feature.properties?.has_region_evidence)
    .map((feature) => Number(feature.properties.events || 0));
  const maxEvents = Math.max(...evidenceValues, 0);

  const map = L.map("region-map", {
    zoomControl: true,
    attributionControl: true,
    minZoom: 4,
    maxZoom: 9,
  });

  let layer = null;
  layer = L.geoJSON(geojson, {
    style: (feature) => {
      const properties = feature.properties || {};
      return {
        color: "#ffffff",
        weight: 1,
        fillOpacity: properties.has_region_evidence ? 0.82 : 0.55,
        fillColor: evidenceColor(
          Number(properties.events || 0),
          maxEvents,
          Boolean(properties.has_region_evidence),
        ),
      };
    },
    onEachFeature: (feature, featureLayer) => {
      const p = feature.properties || {};
      const title = escapeHtml(
        p.name_uk || p.name_en || p.shapeName || "Регіон"
      );
      const evidence = Boolean(p.has_region_evidence);

      let evidenceText = "";
      if (evidence) {
        evidenceText =
          "<strong>" + formatNumber(p.events) + " canonical events</strong><br>" +
          "High confidence: " + formatNumber(p.high_confidence_events) + "<br>" +
          "Medium confidence: " + formatNumber(p.medium_confidence_events) + "<br>" +
          "Low confidence: " + formatNumber(p.low_confidence_events);
      } else {
        evidenceText =
          "<strong>Немає canonical region evidence.</strong><br>" +
          "Це не означає відсутність атак у регіоні.";
      }

      featureLayer.bindPopup(
        '<div class="map-popup"><strong>' + title + "</strong><br>" +
        evidenceText + "</div>"
      );

      featureLayer.on({
        mouseover: (event) => {
          event.target.setStyle({ weight: 2, color: "#253743" });
        },
        mouseout: (event) => {
          layer.resetStyle(event.target);
        },
      });
    },
  }).addTo(map);

  if (layer.getBounds().isValid()) {
    map.fitBounds(layer.getBounds(), { padding: [12, 12] });
  }

  const metadata = geojson.metadata || {};
  const coverage = Number(metadata.region_attribution_coverage_pct || 0);
  const boundaryParts = [];
  if (metadata.boundary_id) boundaryParts.push(metadata.boundary_id);
  if (metadata.boundary_year_represented) {
    boundaryParts.push("year " + metadata.boundary_year_represented);
  }

  el("map-meta").textContent =
    (boundaryParts.join(" · ") || "ADM1") +
    " · coverage " + percentFormat.format(coverage) + "%";

  const statusParts = [];
  if (metadata.boundary_source) {
    statusParts.push("Geometry: " + metadata.boundary_source);
  }
  if (metadata.boundary_license) {
    statusParts.push("License: " + metadata.boundary_license);
  }
  statusParts.push(
    "Mapped: " + formatNumber(metadata.mapped_count) +
    "/" + formatNumber(metadata.feature_count) + " ADM1"
  );
  status.textContent = statusParts.join(" · ");

  setTimeout(() => map.invalidateSize(), 0);
}

function renderMlEvaluation(data) {
  const validationModels = data.validation?.models || {};
  const testModels = data.test?.models || {};
  const modelNames = Array.from(
    new Set([...Object.keys(validationModels), ...Object.keys(testModels)])
  );

  el("ml-evaluation-empty").classList.add("hidden");
  el("ml-evaluation-content").classList.remove("hidden");

  const status = el("ml-status");
  status.textContent = data.deployment_status || "unknown";
  status.className = "status-pill";
  if (data.deployment_status === "blocked_research_only") {
    status.classList.add("blocked");
  }

  el("ml-target").textContent = data.target_name || "—";
  el("ml-source-build").textContent = data.source_build_id || "—";
  el("ml-lowest-mae").textContent =
    data.comparison?.lowest_test_mae_model || "—";
  el("ml-highest-r2").textContent =
    data.comparison?.highest_test_r2 === undefined
      ? "—"
      : metricFormat.format(data.comparison.highest_test_r2);

  el("ml-metrics-body").innerHTML = modelNames.map((name) => {
    const val = validationModels[name] || {};
    const test = testModels[name] || {};
    const fmt = (value) =>
      value === undefined || value === null ? "—" : metricFormat.format(value);

    return "<tr>" +
      "<td>" + escapeHtml(name) + "</td>" +
      "<td class=\"numeric\">" + fmt(val.mae) + "</td>" +
      "<td class=\"numeric\">" + fmt(val.rmse) + "</td>" +
      "<td class=\"numeric\">" + fmt(val.r2) + "</td>" +
      "<td class=\"numeric\">" + fmt(test.mae) + "</td>" +
      "<td class=\"numeric\">" + fmt(test.rmse) + "</td>" +
      "<td class=\"numeric\">" + fmt(test.r2) + "</td>" +
      "</tr>";
  }).join("");

  const reason = data.notes?.deployment_gate?.reason;
  el("ml-note").textContent = reason ||
    "Retrospective metrics only; no deployable model is exposed.";
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

    try {
      const regionMap = await fetchJson("/api/map/regions");
      renderRegionMap(regionMap);
    } catch (mapError) {
      console.error(mapError);
      el("map-status").textContent =
        "Карта недоступна: " + mapError.message +
        ". Виконайте python -m src.ingestion.acquire_boundaries";
      el("map-meta").textContent = "GeoJSON unavailable";
    }

    try {
      const mlEvaluation = await fetchJson("/api/ml/evaluation/latest");
      renderMlEvaluation(mlEvaluation);
    } catch (mlError) {
      console.error(mlError);
      el("ml-status").textContent = "Evaluation unavailable";
      el("ml-status").className = "status-pill";
    }
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