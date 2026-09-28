(async function () {
  const esc = (s) => String(s || "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const form = document.getElementById("acc-form");
  const msg = document.getElementById("form-msg");
  let editing = null;

  async function loadCommentLists() {
    const files = await api.get("/api/comments");
    const sel = form.elements.comment_list;
    sel.innerHTML = '<option value="">— mặc định —</option>' +
      files.map((f) => `<option value="${esc(f.path)}">${esc(f.name)}</option>`).join("");
  }

  async function refresh() {
    const accounts = await api.get("/api/accounts");
    document.getElementById("acc-list").innerHTML = accounts.length
      ? accounts.map((a) => `<tr>
          <td><b>${esc(a.name)}</b></td>
          <td>${esc(a.page_id || "—")}</td>
          <td class="muted">${esc((a.proxy || "").slice(0, 30))}</td>
          <td><span class="muted">${a.use_profile ? "profile" : ""}</span></td>
          <td><button class="btn btn-sm" data-edit="${esc(a.name)}">Sửa</button></td>
          <td><button class="btn btn-sm btn-danger" data-del="${esc(a.name)}">Xóa</button></td>
        </tr>`).join("")
      : '<tr><td colspan="6" class="muted">Chưa có account</td></tr>';
  }

  function fillForm(a) {
    editing = a ? a.name : null;
    document.getElementById("form-title").textContent = a ? `Sửa: ${a.name}` : "Thêm tài khoản";
    document.getElementById("btn-delete").hidden = !a;
    document.getElementById("btn-cancel").hidden = !a;
    for (const k of ["name", "cookie", "page_id", "proxy", "profile_dir", "comment_list"]) {
      form.elements[k].value = a ? a[k] || "" : "";
    }
    form.elements.name.disabled = !!a;
    form.elements.use_profile.checked = !!(a && a.use_profile);
    msg.textContent = "";
  }

  document.getElementById("acc-list").addEventListener("click", async (e) => {
    const delName = e.target.dataset.del;
    if (delName) {
      e.preventDefault();
      if (!confirm(`Xóa tài khoản "${delName}"?`)) return;
      await api.del(`/api/accounts/${encodeURIComponent(delName)}`);
      if (editing === delName) fillForm(null);
      await refresh();
      // nếu form đang Sửa một account đã bị xóa → reset về Thêm
      if (editing) {
        const left = await api.get("/api/accounts");
        if (!left.find((x) => x.name === editing)) fillForm(null);
      }
      return;
    }
    const name = e.target.dataset.edit;
    if (!name) return;
    e.preventDefault();
    const accounts = await api.get("/api/accounts");
    fillForm(accounts.find((x) => x.name === name));
  });

  document.getElementById("btn-new").onclick = () => fillForm(null);
  document.getElementById("btn-cancel").onclick = () => fillForm(null);

  document.getElementById("cookie-file").onchange = async (e) => {
    const f = e.target.files[0];
    if (f) form.elements.cookie.value = await f.text();
  };

  form.onsubmit = async (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(form).entries());
    data.use_profile = form.elements.use_profile.checked;
    const res = editing
      ? await api.put(`/api/accounts/${encodeURIComponent(editing)}`, data)
      : await api.post("/api/accounts", data);
    if (res.error) { msg.textContent = res.error; return; }
    msg.textContent = "Đã lưu.";
    fillForm(null);
    refresh();
  };

  document.getElementById("btn-delete").onclick = async () => {
    if (!editing) return;
    await api.del(`/api/accounts/${encodeURIComponent(editing)}`);
    fillForm(null);
    refresh();
  };

  loadCommentLists();
  fillForm(null);
  refresh();
})();
