(function () {
  const area = document.getElementById("log-area");
  const accountSel = document.getElementById("log-account");
  const levels = new Set(["INFO", "WARNING", "ERROR"]);
  const MAX_LINES = 5000, RENDER_TAIL = 500;
  let buffer = [];

  const esc = (s) => String(s || "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  function passFilters(e) {
    if (accountSel.value !== "*" && e.account !== accountSel.value) return false;
    if (!levels.has(e.level)) return false;
    const q = document.getElementById("log-search").value.trim().toLowerCase();
    if (q && !(e.msg || "").toLowerCase().includes(q)) return false;
    return true;
  }

  function lineHtml(e) {
    const t = new Date(e.ts * 1000).toLocaleTimeString("vi-VN");
    return `<div class="log-line"><span class="ts">${t}</span>` +
      `<span class="lv-${e.level}">${e.level}</span> ` +
      `<span class="acct">[${esc(e.account)}]</span> ${esc(e.msg)}</div>`;
  }

  function render() {
    const filtered = buffer.filter(passFilters).slice(-RENDER_TAIL);
    area.innerHTML = filtered.map(lineHtml).join("");
    if (document.getElementById("log-autoscroll").checked)
      area.scrollTop = area.scrollHeight;
  }

  const off = window.onBackendEvent((data) => {
    if (data.type !== "log") return;
    buffer.push(data);
    if (buffer.length > MAX_LINES) buffer = buffer.slice(-MAX_LINES);
    if (passFilters(data)) {
      area.insertAdjacentHTML("beforeend", lineHtml(data));
      if (area.children.length > RENDER_TAIL)
        area.innerHTML = [...area.children].slice(-RENDER_TAIL).map((c) => c.outerHTML).join("");
      if (document.getElementById("log-autoscroll").checked)
        area.scrollTop = area.scrollHeight;
    }
  });

  // populate account dropdown
  api.get("/api/accounts").then((accounts) => {
    accountSel.innerHTML = '<option value="*">Tất cả account</option>' +
      accounts.map((a) => `<option value="${esc(a.name)}">${esc(a.name)}</option>`).join("");
  });

  accountSel.onchange = render;
  document.getElementById("log-search").oninput = render;
  document.querySelectorAll("[data-level]").forEach((chip) => {
    chip.onclick = () => {
      const lv = chip.dataset.level;
      if (levels.has(lv)) { levels.delete(lv); chip.classList.remove("on"); }
      else { levels.add(lv); chip.classList.add("on"); }
      render();
    };
  });

  document.getElementById("log-clear").onclick = () => { buffer = []; area.innerHTML = ""; };
  document.getElementById("log-export").onclick = () => {
    const text = buffer.filter(passFilters)
      .map((e) => `${new Date(e.ts * 1000).toISOString()} ${e.level} [${e.account}] ${e.msg}`)
      .join("\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([text], { type: "text/plain" }));
    a.download = `logs-${accountSel.value}-${Date.now()}.log`;
    a.click();
    URL.revokeObjectURL(a.href);
  };
})();
