const { app, BrowserWindow, shell, ipcMain } = require("electron");
const path = require("path");
const fs = require("fs");
const { spawn } = require("child_process");

let mainWindow = null;
let pythonProcess = null;

const BACKEND_PORT = process.env.PORT || 8001;
const isDev = process.env.NODE_ENV === "development" || !app.isPackaged;

function getPythonPath() {
  const isWin = process.platform === "win32";
  const candidates = [
    path.join(__dirname, "../.venv", isWin ? "Scripts/python.exe" : "bin/python3"),
    path.join(__dirname, "../.venv", isWin ? "Scripts/python.exe" : "bin/python"),
    path.join(__dirname, "../backend/venv", isWin ? "Scripts/python.exe" : "bin/python3"),
    path.join(__dirname, "../venv", isWin ? "Scripts/python.exe" : "bin/python3")
  ];

  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }

  return isWin ? "python" : "python3";
}

function startBackend() {
  const backendScript = path.join(__dirname, "../backend/main.py");
  const pythonCmd = getPythonPath();
  console.log(`[Electron] Spawning Python backend (${pythonCmd}): ${backendScript} on port ${BACKEND_PORT}...`);
  
  pythonProcess = spawn(pythonCmd, [backendScript], {
    env: { ...process.env, PORT: String(BACKEND_PORT), PYTHONUNBUFFERED: "1" },
    stdio: "inherit"
  });

  pythonProcess.on("error", (err) => {
    console.error("[Electron] Failed to start Python backend:", err);
  });

  pythonProcess.on("exit", (code) => {
    console.log(`[Electron] Python backend exited with code ${code}`);
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 1024,
    minHeight: 700,
    title: "Laptop Hunter",
    backgroundColor: "#0B0F17",
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  // Open external links in default OS browser (OLX links)
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith("http://") || url.startsWith("https://")) {
      shell.openExternal(url);
      return { action: "deny" };
    }
    return { action: "allow" };
  });

  if (isDev && process.env.VITE_DEV_SERVER_URL) {
    mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL);
    // Auto-open Developer Tools in dev mode
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, "../dist/index.html"));
  }

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  startBackend();
  // Small delay to allow uvicorn to bind
  setTimeout(createWindow, 800);

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (pythonProcess) {
    console.log("[Electron] Stopping Python backend...");
    pythonProcess.kill("SIGTERM");
    pythonProcess = null;
  }
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("will-quit", () => {
  if (pythonProcess) {
    pythonProcess.kill("SIGKILL");
    pythonProcess = null;
  }
});
