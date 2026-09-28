(async function () {
  let accounts = [];
  let runs = {};

  const statusBadge = (s) => `<span class="badge badge-${s}">${s}</span>`;
  const shortProxy = (p) => {
    if (!p) return '<span class="muted">—</span>';
    try { return new URL(p).host; } catch { return p.slice(0, 24); }
  };

  async function refresh() {
    accounts = await api.get("/api/accounts");
    runs = await api.get("/api/runs");
    renderRows();
  }

  function renderRows() {
    const tbody = document.getElementById("account-rows");
    if (!accounts.length) {
      tbody.innerHTML = '<tr><td colspan="7" class="muted">Chưa có account. Vào mục "Tài khoản" để thêm.</td></tr>';
      return;
    }
    tbody.innerHTML = accounts.map((a) => {
      const run = runs[a.name] || {};
      const status = run.status || "idle";
      return `<tr>
        <td><input type="checkbox" class="acc-check" value="${esc(a.name)}"></td>
        <td><b>${esc(a.name)}</b></td>
        <td>${esc(a.page_id || "—")}</td>
        <td>${shortProxy(a.proxy)}</td>
        <td>${statusBadge(status)}</td>
        <td class="muted">${esc((run.error || "").slice(0, 60))}</td>
        <td>${status === "running" || status === "starting"
          ? `<button class="btn btn-sm btn-danger" data-stop="${esc(a.name)}">Dừng</button>`
          : `<button class="btn btn-sm" data-start="${esc(a.name)}">Chạy</button>`}
        </td>
      </tr>`;
    }).join("");
    document.getElementById("dashboard-summary").textContent =
      `${accounts.length} account · ${Object.values(runs).filter(r => r.status === "running").length} đang chạy`;
  }

  const esc = (s) => String(s || "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  document.getElementById("check-all").onchange = (e) =>
    document.querySelectorAll(".acc-check").forEach((c) => (c.checked = e.target.checked));

  document.getElementById("btn-stop-all").onclick = async () => {
    await api.post("/api/runs/stop-all");
    refresh();
  };

  document.getElementById("btn-start-selected").onclick = async () => {
    const names = [...document.querySelectorAll(".acc-check:checked")].map((c) => c.value);
    for (const name of names) {
      await api.post(`/api/runs/${encodeURIComponent(name)}/start`, { mode: "uid" });
    }
    refresh();
  };

  document.getElementById("account-rows").addEventListener("click", async (e) => {
    const start = e.target.dataset.start, stop = e.target.dataset.stop;
    if (start) await api.post(`/api/runs/${encodeURIComponent(start)}/start`, { mode: "uid" });
    if (stop) await api.post(`/api/runs/${encodeURIComponent(stop)}/stop`);
    if (start || stop) refresh();
  });

  window.addEventListener("runs-status", (e) => { runs = e.detail; renderRows(); });
  refresh();
})();
