(async function () {
  const esc = (s) => String(s || "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const msg = document.getElementById("camp-msg");
  let current = "";

  const $ = (id) => document.getElementById(id);
  // id → campaign JSON key for numeric fields
  const NUM_MAP = {
    "camp-cooldown": "cooldown_seconds", "camp-max-scrolls": "max_scrolls",
    "camp-empty-scroll": "empty_scroll_limit", "camp-scroll-px": "scroll_pixels",
    "camp-scroll-pause": "scroll_pause_ms", "camp-scroll-ratio": "scroll_ratio",
    "camp-max-group": "max_comments_per_group", "camp-max-run": "max_comments_per_run",
    "camp-phobert-th": "phobert_threshold",
  };

  const DEFAULTS = {
    groups: "", subjects: "", help_phrases: "",
    use_phobert: true, phobert_threshold: 0.8, phobert_review_all: false,
    sort_newest: false, max_scrolls: 30, empty_scroll_limit: 4,
    scroll_pixels: 700, scroll_pause_ms: 4000, scroll_ratio: 0.4,
    max_comments_per_group: 5, max_comments_per_run: 15, cooldown_seconds: 120,
  };

  async function loadList() {
    const list = await api.get("/api/campaigns");
    document.getElementById("camp-list").innerHTML = list.length
      ? list.map((c) => `<label><input type="radio" name="camp" value="${esc(c.name)}" ${c.name === current ? "checked" : ""}> ${esc(c.name)}</label>`).join("")
      : '<span class="muted">Chưa có campaign</span>';
    document.querySelectorAll("#camp-list input").forEach((r) => {
      r.onchange = () => loadCampaign(r.value);
    });
  }

  function fillForm(d) {
    $("camp-name").value = current;
    $("camp-name").disabled = !!current;
    $("camp-groups").value = (d.groups || []).join("\n");
    $("camp-subjects").value = (d.subjects || []).join(", ");
    $("camp-help").value = (d.help_phrases || []).join(", ");
    // Legacy jev_* keys are read by backend defaults — translate once here,
    // then write only the phobert_* keys on save so files migrate cleanly.
    $("camp-use-phobert").checked = d.use_phobert ?? d.use_jev ?? DEFAULTS.use_phobert;
    $("camp-phobert-th").value = d.phobert_threshold ?? d.jev_confidence ?? DEFAULTS.phobert_threshold;
    $("camp-phobert-all").checked = d.phobert_review_all ?? d.jev_review_all ?? false;
    $("camp-sort-newest").checked = !!d.sort_newest;
    for (const [id, key] of Object.entries(NUM_MAP)) {
      if (id === "camp-phobert-th") continue; // handled above (legacy jev_confidence)
      $(id).value = d[key] ?? DEFAULTS[key];
    }
  }

  async function loadCampaign(name) {
    current = name;
    const d = await api.get("/api/campaigns/" + encodeURIComponent(name));
    fillForm(d);
    document.querySelectorAll("#camp-list input").forEach((r) => (r.checked = r.value === name));
  }

  function newCampaign() {
    current = "";
    fillForm({ ...DEFAULTS, groups: [], subjects: [], help_phrases: [] });
    document.querySelectorAll("#camp-list input").forEach((r) => (r.checked = false));
    $("camp-name").focus();
  }

  function buildBody() {
    const csv = (id) => $(id).value.split(",").map((s) => s.trim()).filter(Boolean);
    const body = {
      groups: $("camp-groups").value.split("\n").map((s) => s.trim()).filter(Boolean),
      subjects: csv("camp-subjects"),
      help_phrases: csv("camp-help"),
      use_phobert: $("camp-use-phobert").checked,
      phobert_threshold: +$("camp-phobert-th").value || 0.8,
      phobert_review_all: $("camp-phobert-all").checked,
      sort_newest: $("camp-sort-newest").checked,
      max_scrolls: +$("camp-max-scrolls").value || DEFAULTS.max_scrolls,
      empty_scroll_limit: +$("camp-empty-scroll").value || DEFAULTS.empty_scroll_limit,
      scroll_pixels: +$("camp-scroll-px").value || DEFAULTS.scroll_pixels,
      scroll_pause_ms: +$("camp-scroll-pause").value || DEFAULTS.scroll_pause_ms,
      scroll_ratio: +$("camp-scroll-ratio").value || DEFAULTS.scroll_ratio,
      max_comments_per_group: +$("camp-max-group").value || DEFAULTS.max_comments_per_group,
      max_comments_per_run: +$("camp-max-run").value || DEFAULTS.max_comments_per_run,
      cooldown_seconds: +$("camp-cooldown").value || DEFAULTS.cooldown_seconds,
    };
    return body;
  }

  document.getElementById("btn-camp-save").onclick = async () => {
    const name = (current || $("camp-name").value).trim();
    if (!name) { msg.textContent = "Điền tên campaign."; return; }
    if (!/^[\w-]+$/.test(name)) { msg.textContent = "Tên chỉ gồm chữ, số, -, _."; return; }
    const body = buildBody();
    if (!body.groups.length) { msg.textContent = "Cần ít nhất 1 group URL."; return; }
    msg.textContent = "";
    const res = await api.put("/api/campaigns/" + encodeURIComponent(name), body);
    msg.textContent = res.error ? `Lỗi: ${res.error}` : "Đã lưu.";
    if (!res.error) { current = name; $("camp-name").disabled = true; loadList(); }
    setTimeout(() => { if (msg.textContent === "Đã lưu.") msg.textContent = ""; }, 2500);
  };

  document.getElementById("btn-camp-new").onclick = newCampaign;

  newCampaign();
  loadList();
})();
