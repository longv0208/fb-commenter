// Electron main: spawn Python backend, manage window, graceful quit.
const { app, BrowserWindow } = require("electron");
const { spawn } = require("child_process");
const http = require("http");
const path = require("path");
const fs = require("fs");

const REPO_ROOT = path.resolve(__dirname, "..");
const BASE_PORT = 8787;

let backendProc = null;
let backendPort = BASE_PORT;
let mainWindow = null;
let quitting = false;

function backendLogStream() {
  const dir = path.join(app.getPath("userData"), "logs");
  fs.mkdirSync(dir, { recursive: true });
  const file = path.join(dir, `backend-${new Date().toISOString().slice(0, 10)}.log`);
  return fs.createWriteStream(file, { flags: "a" });
}

function spawnBackend(port) {
  const isDev = !app.isPackaged || process.env.EXTERNAL_BACKEND === "1";
  if (process.env.EXTERNAL_BACKEND === "1") return null; // dev: backend chạy tay

  const exe = app.isPackaged
    ? path.join(process.resourcesPath, "backend", "server.exe")
    : resolvePython();

  const args = app.isPackaged
    ? ["--port", String(port)]
    : ["-m", "backend.server", "--port", String(port)];

  const proc = spawn(exe, args, {
    cwd: REPO_ROOT,
    env: { ...process.env, PYTHONUNBUFFERED: "1" },
    stdio: ["ignore", "pipe", "pipe"],
  });
  const log = backendLogStream();
  proc.stdout.pipe(log);
  proc.stderr.pipe(log);
  proc.on("exit", (code) => {
    log.write(`\n[backend exited code=${code}]\n`);
    if (!quitting) setTimeout(() => spawnBackend(backendPort), 1500);
  });
  return proc;
}

function resolvePython() {
  // dev: ưu tiên venv của project, rồi PATH
  const candidates = [
    path.join(REPO_ROOT, ".venv", "Scripts", "python.exe"),
    path.join(REPO_ROOT, "venv", "Scripts", "python.exe"),
    "python",
    "py",
  ];
  for (const c of candidates) {
    try {
      if (c === "python" || c === "py") return c;
      if (fs.existsSync(c)) return c;
    } catch {}
  }
  return "python";
}

function waitHealthy(port, timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;
  return new Promise((resolve, reject) => {
    const tick = () => {
      const req = http.get(`http://127.0.0.1:${port}/api/health`, (res) => {
        res.resume();
        if (res.statusCode === 200) return resolve(true);
        retry();
      });
      req.on("error", retry);
      req.setTimeout(1000, () => req.destroy());
    };
    const retry = () => {
      if (Date.now() > deadline) return reject(new Error("backend timeout"));
      setTimeout(tick, 300);
    };
    tick();
  });
}

async function ensureBackend() {
  for (let i = 0; i < 4; i++) {
    const port = BASE_PORT + i;
    try {
      // thử health trước — backend có thể đã chạy sẵn
      await waitHealthy(port, 1500);
      backendPort = port;
      return;
    } catch {}
    backendProc = spawnBackend(port);
    try {
      await waitHealthy(port, 25000);
      backendPort = port;
      return;
    } catch (e) {
      try { backendProc && backendProc.kill(); } catch {}
    }
  }
  throw new Error("Không khởi động được backend Python");
}

async function stopBackend() {
  quitting = true;
  try {
    await new Promise((r) => {
      const req = http.request(
        `http://127.0.0.1:${backendPort}/api/runs/stop-all`,
        { method: "POST", timeout: 2000 },
        () => r()
      );
      req.on("error", r);
      req.on("timeout", () => { req.destroy(); r(); });
      req.end();
    });
  } catch {}
  try { backendProc && backendProc.kill(); } catch {}
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 960,
    minHeight: 600,
    backgroundColor: "#0f1115",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  mainWindow.loadFile(path.join(__dirname, "renderer", "index.html"), {
    query: { port: String(backendPort) },
  });
}

app.whenReady().then(async () => {
  try {
    await ensureBackend();
  } catch (e) {
    console.error(e);
  }
  createWindow();
});

app.on("window-all-closed", async () => {
  await stopBackend();
  app.quit();
});

app.on("before-quit", () => { quitting = true; });
