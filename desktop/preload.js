const { contextBridge } = require("electron");

const params = new URLSearchParams(location.search);
const port = params.get("port") || "8787";

contextBridge.exposeInMainWorld("appEnv", {
  backendBase: `http://127.0.0.1:${port}`,
  wsBase: `ws://127.0.0.1:${port}`,
});
