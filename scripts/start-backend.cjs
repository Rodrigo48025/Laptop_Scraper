#!/usr/bin/env node

const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");

const ROOT_DIR = path.resolve(__dirname, "..");
const isWin = process.platform === "win32";

const candidates = [
  path.join(ROOT_DIR, ".venv", isWin ? "Scripts/python.exe" : "bin/python3"),
  path.join(ROOT_DIR, ".venv", isWin ? "Scripts/python.exe" : "bin/python"),
  path.join(ROOT_DIR, "backend/venv", isWin ? "Scripts/python.exe" : "bin/python3"),
  path.join(ROOT_DIR, "venv", isWin ? "Scripts/python.exe" : "bin/python3")
];

const pythonCmd = candidates.find(p => fs.existsSync(p)) || (isWin ? "python" : "python3");
const backendScript = path.join(ROOT_DIR, "backend/main.py");
const port = process.env.PORT || "8001";

console.log(`[Backend Runner] Starting Python backend (${pythonCmd}) on port ${port}...`);

const child = spawn(pythonCmd, [backendScript], {
  cwd: ROOT_DIR,
  env: { ...process.env, PORT: String(port), PYTHONUNBUFFERED: "1" },
  stdio: "inherit"
});

child.on("exit", (code) => {
  console.log(`[Backend Runner] Python backend exited with code ${code}`);
  process.exit(code || 0);
});
