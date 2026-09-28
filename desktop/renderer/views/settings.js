(async function () {
  document.getElementById("set-backend").textContent = api.base;
  const msg = document.getElementById("set-msg");

  const settings = await api.get("/api/settings");
  document.getElementById("set-jev").value = settings.jev_api_key || "";
  document.getElementById("set-data-root").value = settings.data_root || "";
  document.getElementById("set-delay-min").value = settings.delay_min || 1;
  document.getElementById("set-delay-max").value = settings.delay_max || 60;

  document.getElementById("set-save").onclick = async () => {
    await api.put("/api/settings", {
      jev_api_key: document.getElementById("set-jev").value,
      data_root: document.getElementById("set-data-root").value,
      delay_min: document.getElementById("set-delay-min").value,
      delay_max: document.getElementById("set-delay-max").value,
    });
    msg.textContent = "Đã lưu.";
    setTimeout(() => (msg.textContent = ""), 2000);
  };
})();
