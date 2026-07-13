(() => {
  const form = document.getElementById("analyzeForm");
  const question = document.getElementById("question");
  const mode = document.getElementById("mode");
  const fileInput = document.getElementById("files");
  const dropzone = document.getElementById("dropzone");
  const fileList = document.getElementById("fileList");
  const submitBtn = document.getElementById("submitBtn");
  const loadingBar = document.getElementById("loadingBar");
  const resultPanel = document.getElementById("resultPanel");
  const emptyPanel = document.getElementById("emptyPanel");
  const resultBody = document.getElementById("resultBody");
  const modeBadge = document.getElementById("modeBadge");
  const confBadge = document.getElementById("confBadge");
  const healthPill = document.getElementById("healthPill");
  const runMeta = document.getElementById("runMeta");
  const historyList = document.getElementById("historyList");
  const refreshHistory = document.getElementById("refreshHistory");

  /** @type {File[]} */
  let selectedFiles = [];
  /** @type {any} */
  let lastReport = null;
  let authRequired = false;

  function apiHeaders(extra = {}) {
    const h = { ...extra };
    const tok = sessionStorage.getItem("smf_swarm_api_token") || "";
    if (tok) h["X-API-Key"] = tok;
    return h;
  }

  function ensureTokenIfNeeded() {
    if (!authRequired) return true;
    let tok = sessionStorage.getItem("smf_swarm_api_token") || "";
    if (!tok) {
      tok = window.prompt("This server requires SMF_SWARM_API_TOKEN. Enter API token:") || "";
      if (tok) sessionStorage.setItem("smf_swarm_api_token", tok.trim());
    }
    return Boolean(sessionStorage.getItem("smf_swarm_api_token"));
  }

  function toast(msg) {
    let el = document.querySelector(".toast");
    if (!el) {
      el = document.createElement("div");
      el.className = "toast";
      document.body.appendChild(el);
    }
    el.textContent = msg;
    el.classList.add("show");
    setTimeout(() => el.classList.remove("show"), 1800);
  }

  function renderFiles() {
    fileList.innerHTML = "";
    selectedFiles.forEach((f, idx) => {
      const li = document.createElement("li");
      li.innerHTML = `<span>${escapeHtml(f.name)} <span class="mono">(${formatBytes(f.size)})</span></span>`;
      const rm = document.createElement("button");
      rm.type = "button";
      rm.className = "rm";
      rm.textContent = "remove";
      rm.addEventListener("click", () => {
        selectedFiles.splice(idx, 1);
        renderFiles();
      });
      li.appendChild(rm);
      fileList.appendChild(li);
    });
  }

  function addFiles(fileListLike) {
    const incoming = Array.from(fileListLike || []);
    for (const f of incoming) {
      if (selectedFiles.length >= 8) break;
      if (!selectedFiles.some((x) => x.name === f.name && x.size === f.size)) {
        selectedFiles.push(f);
      }
    }
    renderFiles();
  }

  fileInput.addEventListener("change", () => {
    addFiles(fileInput.files);
    fileInput.value = "";
  });

  ["dragenter", "dragover"].forEach((evt) => {
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    });
  });
  ["dragleave", "drop"].forEach((evt) => {
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
    });
  });
  dropzone.addEventListener("drop", (e) => {
    addFiles(e.dataTransfer.files);
  });

  fetch("/api/health")
    .then((r) => r.json())
    .then((j) => {
      authRequired = Boolean(j.auth_required);
      healthPill.textContent = `online · ${j.version || ""}`.trim() + (authRequired ? " · auth" : "");
      healthPill.classList.add("ok");
    })
    .catch(() => {
      healthPill.textContent = "offline";
      healthPill.classList.add("bad");
    });

  async function loadHistory() {
    try {
      if (authRequired && !ensureTokenIfNeeded()) {
        historyList.innerHTML = `<li class="muted">Auth required for history</li>`;
        return;
      }
      const r = await fetch("/api/history?limit=12", { headers: apiHeaders() });
      if (r.status === 401) {
        sessionStorage.removeItem("smf_swarm_api_token");
        historyList.innerHTML = `<li class="muted">Unauthorized — set API token</li>`;
        return;
      }
      const data = await r.json();
      const items = data.items || [];
      if (!items.length) {
        historyList.innerHTML = `<li class="muted">No runs yet</li>`;
        return;
      }
      historyList.innerHTML = "";
      items.forEach((it) => {
        const li = document.createElement("li");
        const conf = Math.round((it.confidence || 0) * 100);
        li.innerHTML = `
          <div class="q">${escapeHtml((it.prediction_headline || "Run") + " — " + (it.question || "").slice(0, 80))}</div>
          <div class="meta">${escapeHtml(it.run_id || "")} · ${escapeHtml(it.mode || "")} · ${conf}% · ${escapeHtml((it.created_at || "").slice(0, 19))}</div>
        `;
        li.addEventListener("click", async () => {
          const res = await fetch(`/api/history/${encodeURIComponent(it.run_id)}`, {
            headers: apiHeaders(),
          });
          if (!res.ok) {
            toast("Could not load run");
            return;
          }
          const report = await res.json();
          renderReport(report);
        });
        historyList.appendChild(li);
      });
    } catch {
      historyList.innerHTML = `<li class="muted">History unavailable</li>`;
    }
  }

  refreshHistory.addEventListener("click", loadHistory);
  loadHistory();

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const q = question.value.trim();
    if (!q) return;
    if (authRequired && !ensureTokenIfNeeded()) {
      toast("API token required");
      return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = "Running swarm…";
    loadingBar.hidden = false;

    const fd = new FormData();
    fd.append("question", q);
    fd.append("mode", mode.value);
    selectedFiles.forEach((f) => fd.append("files", f, f.name));

    try {
      const res = await fetch("/api/analyze", {
        method: "POST",
        body: fd,
        headers: apiHeaders(),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || res.statusText || "Request failed");
      }
      renderReport(data);
      loadHistory();
    } catch (err) {
      emptyPanel.hidden = true;
      resultPanel.hidden = false;
      modeBadge.textContent = "error";
      confBadge.textContent = "";
      runMeta.textContent = "";
      resultBody.innerHTML = `<div class="card error"><h3>Error</h3><p>${escapeHtml(
        String(err.message || err)
      )}</p></div>`;
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Run swarm analysis";
      loadingBar.hidden = true;
    }
  });

  document.getElementById("copyJson").addEventListener("click", async () => {
    if (!lastReport) return;
    const { markdown, ...rest } = lastReport;
    await navigator.clipboard.writeText(JSON.stringify(rest, null, 2));
    toast("JSON copied");
  });

  document.getElementById("copyMd").addEventListener("click", async () => {
    if (!lastReport) return;
    const md = lastReport.markdown || buildMdClient(lastReport);
    await navigator.clipboard.writeText(md);
    toast("Markdown copied");
  });

  document.getElementById("downloadMd").addEventListener("click", () => {
    if (!lastReport) return;
    const md = lastReport.markdown || buildMdClient(lastReport);
    const blob = new Blob([md], { type: "text/markdown" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `smf-swarm-${lastReport.run_id || "report"}.md`;
    a.click();
    URL.revokeObjectURL(a.href);
  });

  document.getElementById("copyShare").addEventListener("click", async () => {
    if (!lastReport) return;
    const path = lastReport.share_url_path || lastReport.share_path || lastReport.signed_url_path;
    if (!path) {
      toast("No share link on this report");
      return;
    }
    const url = new URL(path, window.location.origin).toString();
    await navigator.clipboard.writeText(url);
    toast("Share link copied");
  });

  function renderReport(r) {
    lastReport = r;
    emptyPanel.hidden = true;
    resultPanel.hidden = false;

    let modeLabel = `mode: ${r.mode || "?"}`;
    if (r.fallback_used) modeLabel += " (fallback)";
    modeBadge.textContent = modeLabel;
    modeBadge.className = "pill" + (r.fallback_used ? " warn" : "");

    const conf = Math.round((r.confidence || 0) * 100);
    confBadge.textContent = `confidence ${conf}%`;
    confBadge.classList.add("accent");

    runMeta.textContent = `run ${r.run_id || "?"} · ${r.created_at || ""} · horizon: ${r.time_horizon || "n/a"}`;

    const headline = r.prediction_headline || r.prediction || "Prediction";
    const detail = r.prediction_detail || r.prediction || "";

    const drivers = (r.key_drivers || []).map((d) => `<li>${escapeHtml(d)}</li>`).join("");
    const risks = (r.risks || []).map((d) => `<li>${escapeHtml(d)}</li>`).join("");
    const actions = (r.recommended_actions || []).map((d) => `<li>${escapeHtml(d)}</li>`).join("");
    const insights = (r.data_insights || []).map((d) => `<li>${escapeHtml(d)}</li>`).join("");
    const scenarios = (r.scenarios || [])
      .map(
        (s) => `<li><strong>${escapeHtml(s.name || "")}</strong>
        <span class="mono">${escapeHtml(formatProb(s.probability))}</span>
        — ${escapeHtml(s.narrative || "")}</li>`
      )
      .join("");

    const evidence = (r.evidence || [])
      .map(
        (e) => `<li><strong>[${escapeHtml(e.source || "")}]</strong> ${escapeHtml(
          e.claim || ""
        )} <span class="mono">— ${escapeHtml((e.excerpt || "").slice(0, 160))}</span></li>`
      )
      .join("");

    const charts = (r.charts || [])
      .map((c) => {
        const stats = c.stats || {};
        return `<div class="chart-card">
          <div class="chart-title">${escapeHtml(c.filename || "")} · <strong>${escapeHtml(
          c.name || "series"
        )}</strong>
          <span class="mono">n=${escapeHtml(String(stats.n ?? ""))} last=${escapeHtml(
          String(stats.last ?? "")
        )} Δ=${escapeHtml(String(stats.delta ?? ""))} (${escapeHtml(
          Number(stats.delta_pct || 0).toFixed(1)
        )}%)</span></div>
          <div class="sparkline">${c.sparkline_svg || ""}</div>
        </div>`;
      })
      .join("");

    const personas = (r.persona_views || [])
      .map((p) => {
        const findings = (p.findings || []).map((f) => `<li>${escapeHtml(f)}</li>`).join("");
        return `<div class="persona">
          <div class="name">${escapeHtml(p.persona || "Analyst")}</div>
          <div class="role">${escapeHtml(p.role || "")}</div>
          <ul>${findings}</ul>
        </div>`;
      })
      .join("");

    const m = r.methodology || {};
    const files = (r.attachments_used || []).join(", ") || "none";
    const sharePath = r.share_url_path || r.share_path || "";

    resultBody.innerHTML = `
      <div class="card">
        <h3>Prediction</h3>
        <div class="prediction-headline">${escapeHtml(headline)}</div>
        <p>${formatMdLite(detail)}</p>
        <div class="conf-bar" title="confidence"><span style="width:${conf}%"></span></div>
      </div>
      <div class="card">
        <h3>Executive summary</h3>
        <p>${escapeHtml(r.executive_summary || "")}</p>
      </div>
      ${
        charts
          ? `<div class="card"><h3>Charts</h3>${charts}</div>`
          : ""
      }
      <div class="card">
        <h3>Key drivers</h3>
        <ul>${drivers || "<li>None listed</li>"}</ul>
      </div>
      <div class="card">
        <h3>Scenarios</h3>
        <ul>${scenarios || "<li>None listed</li>"}</ul>
      </div>
      <div class="card">
        <h3>Evidence</h3>
        <ul>${evidence || "<li>No evidence items</li>"}</ul>
        <p class="mono" style="margin-top:0.5rem">Files used: ${escapeHtml(files)}</p>
      </div>
      <div class="card">
        <h3>Data insights</h3>
        <ul>${insights || "<li>None</li>"}</ul>
      </div>
      <div class="card">
        <h3>Risks</h3>
        <ul>${risks || "<li>None listed</li>"}</ul>
      </div>
      <div class="card">
        <h3>Recommended actions</h3>
        <ul>${actions || "<li>None listed</li>"}</ul>
      </div>
      <div class="card">
        <h3>Swarm personas</h3>
        <div class="personas">${personas || "<p class='mono'>No persona detail</p>"}</div>
      </div>
      <div class="card">
        <h3>Methodology</h3>
        <ul>
          <li>Personas: ${escapeHtml((m.personas || []).join(", ") || "Scout, Strategist, Skeptic, Forecaster")}</li>
          <li>Pipeline: ${escapeHtml(m.pipeline || "")}</li>
          <li>Model: ${escapeHtml(r.model_used || m.model || "n/a")}</li>
          <li>Mode: ${escapeHtml(r.mode || "")}${r.fallback_used ? " (LLM failed → mock fallback)" : ""}</li>
          <li>Limitations: ${escapeHtml(m.limitations || "")}</li>
        </ul>
      </div>
      <div class="card">
        <h3>Share & governance</h3>
        <p class="mono">agent=${escapeHtml(r.agent_id || "")} · audit_events=${
      r.audit_events ?? "?"
    } · chain_valid=${r.chain_valid}</p>
        ${
          sharePath
            ? `<p style="margin-top:0.45rem">Share path: <span class="mono">${escapeHtml(
                sharePath
              )}</span></p>`
            : ""
        }
        <p style="margin-top:0.5rem;color:var(--muted);font-size:0.88rem">${escapeHtml(
          r.disclaimer || ""
        )}</p>
      </div>
    `;
  }

  function formatProb(p) {
    if (p == null) return "";
    if (typeof p === "number") {
      if (p <= 1) return `${Math.round(p * 100)}%`;
      return `${Math.round(p)}%`;
    }
    const s = String(p);
    if (/^0?\.\d+$/.test(s)) return `${Math.round(parseFloat(s) * 100)}%`;
    return s;
  }

  function buildMdClient(r) {
    return `# SMF Swarm Report ${r.run_id || ""}\n\n## Question\n${r.question || ""}\n\n## Prediction\n**${r.prediction_headline || ""}**\n\n${r.prediction_detail || r.prediction || ""}\n`;
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function formatMdLite(s) {
    return escapeHtml(s).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  }

  function formatBytes(n) {
    if (n < 1024) return `${n} B`;
    if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
    return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  }
})();
