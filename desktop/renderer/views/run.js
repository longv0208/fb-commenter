(async function () {
  const esc = (s) => String(s || "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const msg = document.getElementById("run-msg");
  let runs = {};

  async function loadAccounts() {
    const accounts = await api.get("/api/accounts");
    document.getElementById("run-accounts").innerHTML = accounts.length
      ? accounts.map((a) => `<label><input type="checkbox" value="${esc(a.name)}"> ${esc(a.name)} <span class="muted">(${esc(a.page_id || "no page")})</span></label>`).join("")
      : '<span class="muted">Chưa có account</span>';
  }

  async function loadCampaigns() {
    const c = await api.get("/api/campaigns");
    document.getElementById("campaign-select").innerHTML =
      c.map((x) => `<option value="${esc(x.name)}">${esc(x.name)}</option>`).join("") ||
      '<option value="">— chưa có campaign —</option>';
  }

  function mode() { return document.querySelector("input[name=mode]:checked").value; }

  function toggleMode() {
    const isCampaign = mode() === "campaign";
    document.getElementById("campaign-picker").hidden = !isCampaign;
    document.getElementById("urls-row").hidden = isCampaign;
    document.getElementById("cooldown-row").hidden = !isCampaign;
    document.getElementById("opt-cooldown").hidden = !isCampaign;
  }
  document.querySelectorAll("input[name=mode]").forEach((r) => (r.onchange = toggleMode));

  function buildOpts() {
    const o = {
      mode: mode(),
      campaign: document.getElementById("campaign-select").value,
      urls: document.getElementById("opt-urls").value,
      delay_min: +document.getElementById("opt-delay-min").value || 1,
      delay_max: +document.getElementById("opt-delay-max").value || 60,
      headless: document.getElementById("opt-headless").checked,
      dry_run: document.getElementById("opt-dry-run").checked,
      no_proxy: document.getElementById("opt-no-proxy").checked,
    };
    const cd = document.getElementById("opt-cooldown").value;
    if (cd !== "") o.cooldown = +cd;
    return o;
  }

  function selected() {
    return [...document.querySelectorAll("#run-accounts input:checked")].map((c) => c.value);
  }

  function renderStatus() {
    const rows = Object.values(runs);
    document.getElementById("run-status").innerHTML = rows.length
      ? rows.map((r) => `<tr><td><b>${esc(r.name)}</b></td><td>${esc(r.mode)}</td>
          <td><span class="badge badge-${r.status}">${r.status}</span></td>
          <td class="muted">${esc((r.error || "").slice(0, 80))}</td></tr>`).join("")
      : '<tr><td colspan="4" class="muted">Chưa có run nào</td></tr>';
  }

  document.getElementById("btn-run-start").onclick = async () => {
    const names = selected(), opts = buildOpts();
    if (!names.length) { msg.textContent = "Chọn ít nhất 1 account."; return; }
    msg.textContent = "";
    for (const name of names) {
      const res = await api.post(`/api/runs/${encodeURIComponent(name)}/start`, opts);
      if (res.error) msg.textContent += `${name}: ${res.error} `;
    }
    refreshRuns();
  };

  document.getElementById("btn-run-stop").onclick = async () => {
    for (const name of selected()) {
      await api.post(`/api/runs/${encodeURIComponent(name)}/stop`);
    }
    refreshRuns();
  };

  async function refreshRuns() { runs = await api.get("/api/runs"); renderStatus(); }
  window.addEventListener("runs-status", (e) => { runs = e.detail; renderStatus(); });

  toggleMode();
  loadAccounts();
  loadCampaigns();
  refreshRuns();
})();
