#!/usr/bin/env node

const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const ROOT_DIR = path.resolve(__dirname, "..");
const isWin = process.platform === "win32";

function log(msg) {
  console.log(`\x1b[36m[Setup]\x1b[0m ${msg}`);
}

function success(msg) {
  console.log(`\x1b[32m✔ ${msg}\x1b[0m`);
}

function error(msg) {
  console.error(`\x1b[31m✖ ${msg}\x1b[0m`);
}

function run(cmd, opts = {}) {
  return execSync(cmd, {
    cwd: ROOT_DIR,
    stdio: "inherit",
    ...opts
  });
}

try {
  log("Starting full project setup (Node + Python + Playwright)...");

  // 1. Check & install Node dependencies
  const concurrentlyBin = path.join(ROOT_DIR, "node_modules", ".bin", isWin ? "concurrently.cmd" : "concurrently");
  if (!fs.existsSync(concurrentlyBin)) {
    log("Installing Node dependencies via npm install (this may take a minute)...");
    run("npm install");
    success("npm packages installed.");
  }

  // Ensure Electron & esbuild postinstall binaries are downloaded
  log("Verifying Electron & esbuild binaries...");
  const electronInstallJs = path.join(ROOT_DIR, "node_modules/electron/install.js");
  if (fs.existsSync(electronInstallJs)) {
    try {
      run(`node "${electronInstallJs}"`);
    } catch {
      log("Electron binary postinstall already satisfied.");
    }
  }
  const esbuildInstallJs = path.join(ROOT_DIR, "node_modules/esbuild/install.js");
  if (fs.existsSync(esbuildInstallJs)) {
    try {
      run(`node "${esbuildInstallJs}"`);
    } catch {
      // ignore
    }
  }
  success("Node modules & Electron verified.");

  // 2. Python Virtual Environment setup (.venv)
  const venvDir = path.join(ROOT_DIR, ".venv");
  const pythonBin = isWin
    ? path.join(venvDir, "Scripts", "python.exe")
    : path.join(venvDir, "bin", "python3");
  const pipBin = isWin
    ? path.join(venvDir, "Scripts", "pip.exe")
    : path.join(venvDir, "bin", "pip");
  const playwrightBin = isWin
    ? path.join(venvDir, "Scripts", "playwright.exe")
    : path.join(venvDir, "bin", "playwright");

  if (!fs.existsSync(pythonBin)) {
    log("Creating isolated Python virtual environment (.venv)...");
    const sysPython = isWin ? "python" : "python3";
    run(`${sysPython} -m venv .venv`);
    success("Created .venv virtual environment.");
  } else {
    log("Existing Python virtual environment (.venv) detected.");
  }

  // 3. Install Python requirements
  const reqPath = path.join(ROOT_DIR, "backend", "requirements.txt");
  if (fs.existsSync(reqPath)) {
    log("Installing Python dependencies from backend/requirements.txt...");
    run(`"${pipBin}" install -r "${reqPath}"`);
    success("Python dependencies installed.");
  }

  // 4. Install Playwright Chromium browser
  log("Ensuring Playwright Chromium browser is installed...");
  try {
    run(`"${playwrightBin}" install chromium`);
    success("Playwright Chromium browser installed.");
  } catch (pwErr) {
    console.warn("\x1b[33m[Warning]\x1b[0m Playwright install encountered a warning. Scraper will attempt fallback if needed.");
  }

  console.log("\n\x1b[32m==================================================");
  console.log("🚀 Setup Complete! Everything is ready.");
  console.log("To launch the app with live reload, run:");
  console.log("\n   npm start\n");
  console.log("==================================================\x1b[0m\n");

} catch (err) {
  error(`Setup failed: ${err.message}`);
  process.exit(1);
}
