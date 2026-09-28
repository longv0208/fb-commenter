// Hash router + API client + WS client. No framework.
(function () {
  const BASE = window.appEnv ? window.appEnv.backendBase : "http://127.0.0.1:8787";
  const WS = window.appEnv ? window.appEnv.wsBase : "ws://127.0.0.1:8787";

  window.api = {
    base: BASE,
    async get(p) { return (await fetch(BASE + p)).json(); },
    async post(p, body) {
      return (await fetch(BASE + p, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body || {}),
      })).json();
    },
    async put(p, body) {
      return (await fetch(BASE + p, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body || {}),
      })).json();
    },
    async del(p) { return (await fetch(BASE + p, { method: "DELETE" })).json(); },
  };

  // ---- WS log stream ----
  const listeners = new Set();
  let ws = null;
  function connectWs() {
    try { ws = new WebSocket(WS + "/ws"); } catch { return scheduleReconnect(); }
    ws.onmessage = (ev) => {
      let data;
      try { data = JSON.parse(ev.data); } catch { return; }
      listeners.forEach((fn) => fn(data));
      if (data.type === "status") window.dispatchEvent(new CustomEvent("runs-status", { detail: data.runs }));
    };
    ws.onclose = scheduleReconnect;
    ws.onerror = () => ws.close();
  }
  function scheduleReconnect() { setTimeout(connectWs, 2000); }
  window.onBackendEvent = (fn) => { listeners.add(fn); return () => listeners.delete(fn); };
  connectWs();

  // ---- health badge ----
  async function pollHealth() {
    const el = document.getElementById("backend-status");
    try {
      const r = await api.get("/api/health");
      el.textContent = "backend: ok";
      el.className = "badge badge-ok";
    } catch {
      el.textContent = "backend: down";
      el.className = "badge badge-err";
    }
    setTimeout(pollHealth, 5000);
  }
  pollHealth();

  // ---- router ----
  const routes = {
    dashboard: "views/dashboard.html",
    accounts: "views/accounts.html",
    run: "views/run.html",
    logs: "views/logs.html",
    settings: "views/settings.html",
  };

  async function render() {
    const name = (location.hash.replace("#/", "") || "dashboard").split("?")[0];
    const file = routes[name] || routes.dashboard;
    document.querySelectorAll("[data-route]").forEach((a) =>
      a.classList.toggle("active", a.dataset.route === name)
    );
    const view = document.getElementById("view");
    try {
      const html = await (await fetch(file)).text();
      view.innerHTML = html;
      const jsFile = file.replace(".html", ".js");
      const script = document.createElement("script");
      script.src = jsFile + "?t=" + Date.now();
      view.appendChild(script);
    } catch (e) {
      view.innerHTML = `<div class="error">Không tải được view: ${e.message}</div>`;
    }
  }
  window.addEventListener("hashchange", render);
  render();
})();
