(() => {
  const form = document.getElementById("analyzeForm");
  const question = document.getElementById("question");
  const mode = document.getElementById("mode");
  const fileInput = document.getElementById("files");
  const dropzone = document.getElementById("dropzone");
  const fileList = document.getElementById("fileList");
  const submitBtn = document.getElementById("submitBtn");
  const resultPanel = document.getElementById("resultPanel");
  const emptyPanel = document.getElementById("emptyPanel");
  const resultBody = document.getElementById("resultBody");
  const modeBadge = document.getElementById("modeBadge");
  const confBadge = document.getElementById("confBadge");
  const healthPill = document.getElementById("healthPill");

  /** @type {File[]} */
  let selectedFiles = [];

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
      healthPill.textContent = "online";
      healthPill.classList.add("ok");
    })
    .catch(() => {
      healthPill.textContent = "offline";
      healthPill.classList.add("bad");
    });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const q = question.value.trim();
    if (!q) return;

    submitBtn.disabled = true;
    submitBtn.textContent = "Running swarm…";

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
    } catch (err) {
      emptyPanel.hidden = true;
      resultPanel.hidden = false;
      modeBadge.textContent = "error";
      confBadge.textContent = "";
      resultBody.innerHTML = `<div class="card error"><h3>Error</h3><p>${escapeHtml(
        String(err.message || err)
      )}</p></div>`;
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Run swarm analysis";
    }
  });

  function renderReport(r) {
    emptyPanel.hidden = true;
    resultPanel.hidden = false;
    modeBadge.textContent = `mode: ${r.mode || "?"}`;
    const conf = Math.round((r.confidence || 0) * 100);
    confBadge.textContent = `confidence ${conf}%`;
    confBadge.classList.add("accent");

    const drivers = (r.key_drivers || []).map((d) => `<li>${escapeHtml(d)}</li>`).join("");
    const risks = (r.risks || []).map((d) => `<li>${escapeHtml(d)}</li>`).join("");
    const actions = (r.recommended_actions || []).map((d) => `<li>${escapeHtml(d)}</li>`).join("");
    const insights = (r.data_insights || []).map((d) => `<li>${escapeHtml(d)}</li>`).join("");
    const scenarios = (r.scenarios || [])
      .map(
        (s) => `<li><strong>${escapeHtml(s.name || "")}</strong>
        <span class="mono">${escapeHtml(s.probability || "")}</span>
        — ${escapeHtml(s.narrative || "")}</li>`
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

    const files = (r.attachments_used || []).join(", ") || "none";

    resultBody.innerHTML = `
      <div class="card">
        <h3>Executive summary</h3>
        <p>${escapeHtml(r.executive_summary || "")}</p>
        <div class="conf-bar" title="confidence"><span style="width:${conf}%"></span></div>
      </div>
      <div class="card">
        <h3>Prediction</h3>
        <p>${formatMdLite(r.prediction || "")}</p>
        <p class="mono" style="margin-top:0.5rem">Horizon: ${escapeHtml(
          r.time_horizon || ""
        )} · run ${escapeHtml(r.run_id || "")}</p>
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
        <h3>Data insights</h3>
        <ul>${insights || "<li>None</li>"}</ul>
        <p class="mono" style="margin-top:0.5rem">Files: ${escapeHtml(files)}</p>
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

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function formatMdLite(s) {
    // very small **bold** support
    return escapeHtml(s).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  }

  function formatBytes(n) {
    if (n < 1024) return `${n} B`;
    if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
    return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  }
})();
