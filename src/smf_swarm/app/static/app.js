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
      healthPill.textContent = `online · ${j.version || ""}`.trim();
      healthPill.classList.add("ok");
    })
    .catch(() => {
      healthPill.textContent = "offline";
      healthPill.classList.add("bad");
    });

  async function loadHistory() {
    try {
      const r = await fetch("/api/history?limit=12");
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
          const res = await fetch(`/api/history/${encodeURIComponent(it.run_id)}`);
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

    submitBtn.disabled = true;
    submitBtn.textContent = "Running swarm…";
    loadingBar.hidden = false;

    const fd = new FormData();
    fd.append("question", q);
    fd.append("mode", mode.value);
    selectedFiles.forEach((f) => fd.append("files", f, f.name));

    try {
      const res = await fetch("/api/analyze", { method: "POST", body: fd });
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
        <h3>Governance</h3>
        <p class="mono">agent=${escapeHtml(r.agent_id || "")} · audit_events=${
      r.audit_events ?? "?"
    } · chain_valid=${r.chain_valid}</p>
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
