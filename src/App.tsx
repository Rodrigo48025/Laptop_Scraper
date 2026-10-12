import React, { useState, useEffect } from "react"
import { LaptopScraperView } from "./components/LaptopScraperView"
import { SettingsView } from "./components/SettingsView"
import { ScraperLogsModal } from "./components/ScraperLogsModal"
import { Dialog } from "./components/ui/dialog"
import { Laptop, Settings, Terminal, Globe } from "lucide-react"
import { useLanguage } from "./i18n/LanguageContext"

export function App() {
  const { t, language, setLanguage } = useLanguage()
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [settingsVersion, setSettingsVersion] = useState(0)

  // Daemon State & Uptime
  const [daemonRunning, setDaemonRunning] = useState<boolean>(false)
  const [daemonUptime, setDaemonUptime] = useState<number>(0)
  const [daemonLoading, setDaemonLoading] = useState<boolean>(false)

  // Logs Modal State
  const [logsOpen, setLogsOpen] = useState<boolean>(false)

  const checkBackend = async () => {
    try {
      const res = await fetch("/api/health")
      setBackendOnline(res.ok)
    } catch {
      setBackendOnline(false)
    }
  }

  const checkDaemon = async () => {
    try {
      const res = await fetch("/api/daemon/status")
      if (res.ok) {
        const data = await res.json()
        setDaemonRunning(Boolean(data.running))
        if (data.running) {
          setDaemonUptime(data.uptime_seconds || 0)
        } else {
          setDaemonUptime(0)
        }
      }
    } catch (e) {
      console.error("Failed to check daemon status:", e)
    }
  }

  useEffect(() => {
    checkBackend()
    checkDaemon()
    const backendInterval = setInterval(checkBackend, 15000)
    const daemonPollInterval = setInterval(checkDaemon, 5000)

    return () => {
      clearInterval(backendInterval)
      clearInterval(daemonPollInterval)
    }
  }, [])

  // Local second-by-second ticker for smooth live uptime display
  useEffect(() => {
    if (!daemonRunning) return
    const ticker = setInterval(() => {
      setDaemonUptime((prev) => prev + 1)
    }, 1000)
    return () => clearInterval(ticker)
  }, [daemonRunning])

  const handleToggleDaemon = async () => {
    setDaemonLoading(true)
    try {
      const willStart = !daemonRunning
      const endpoint = daemonRunning ? "/api/daemon/stop" : "/api/daemon/start"
      const res = await fetch(endpoint, { method: "POST" })
      if (res.ok) {
        const data = await res.json()
        const isRunning = Boolean(data.running)
        setDaemonRunning(isRunning)
        setDaemonUptime(data.uptime_seconds || 0)


      }
    } catch (err) {
      console.error("Failed to toggle daemon:", err)
    } finally {
      setDaemonLoading(false)
    }
  }

  const formatUptime = (totalSeconds: number): string => {
    if (totalSeconds < 60) {
      return `${totalSeconds}s`
    }
    const minutes = Math.floor(totalSeconds / 60)
    const seconds = totalSeconds % 60
    if (minutes < 60) {
      return `${minutes}m ${seconds}s`
    }
    const hours = Math.floor(minutes / 60)
    const remMinutes = minutes % 60
    return `${hours}h ${remMinutes}m`
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans selection:bg-indigo-500 selection:text-white">
      {/* App Header */}
      <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b border-slate-200 px-4 sm:px-6 py-3 flex items-center justify-between shadow-xs">
        <div className="flex items-center space-x-3">
          <div className="h-9 w-9 rounded-xl bg-indigo-600 flex items-center justify-center shadow-xs">
            <Laptop className="h-5 w-5 text-white" />
          </div>
          <div>
            <div className="flex items-center">
              <h1 className="text-base font-bold text-slate-900 tracking-tight">{t("app.title")}</h1>
            </div>
            <p className="text-xs text-slate-500 hidden sm:block">
              {t("app.subtitle")}
            </p>
          </div>
        </div>

        {/* Top-Right Header Actions: Logs, Language, Settings, Status */}
        <div className="flex items-center space-x-2 sm:space-x-2.5">

          {/* Logs Terminal Trigger */}
          <button
            type="button"
            onClick={() => setLogsOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-xs transition-all hover:border-slate-300"
            title={t("logs.title")}
          >
            <Terminal className="w-4 h-4 text-slate-600" />
            <span className="hidden sm:inline">{t("app.logs")}</span>
          </button>

          {/* Language Toggle Button */}
          <button
            type="button"
            onClick={() => setLanguage(language === "pt" ? "en" : "pt")}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-xs transition-all hover:border-slate-300"
            title={language === "pt" ? "Switch to English" : "Mudar para Português"}
          >
            <Globe className="w-3.5 h-3.5 text-indigo-600" />
            <span className="uppercase font-mono text-[11px] font-bold">{language}</span>
          </button>

          {/* Backend Status Dot */}
          <div className="hidden lg:flex items-center space-x-1.5 px-2.5 py-1.5 rounded-full bg-slate-100 border border-slate-200 text-xs">
            <span
              className={`h-2 w-2 rounded-full ${
                backendOnline === true
                  ? "bg-emerald-500"
                  : backendOnline === false
                  ? "bg-red-500"
                  : "bg-amber-400 animate-pulse"
              }`}
            />
            <span className="text-slate-700 font-medium text-[10px]">
              {backendOnline === true ? t("app.online") : t("app.connecting")}
            </span>
          </div>

          {/* Daemon Status Header Badge */}
          {daemonRunning && (
            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 shadow-2xs">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse shrink-0" />
              <span className="font-medium hidden md:inline text-[11px]">Demon</span>
              <span className="font-mono text-[11px] font-semibold text-emerald-900 bg-emerald-100/90 px-1.5 py-0.5 rounded border border-emerald-200/60">
                {formatUptime(daemonUptime)}
              </span>
            </div>
          )}

          {/* Settings Trigger */}
          <button
            type="button"
            onClick={() => setSettingsOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-xs transition-all hover:border-slate-300"
            title={t("app.settings")}
          >
            <Settings className="w-4 h-4 text-slate-600" />
            <span className="hidden sm:inline">{t("app.settings")}</span>
          </button>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 w-full max-w-7xl mx-auto p-4 sm:p-6">
        <LaptopScraperView
          settingsVersion={settingsVersion}
          daemonRunning={daemonRunning}
          daemonUptime={daemonUptime}
          onToggleDaemon={handleToggleDaemon}
          daemonLoading={daemonLoading}
        />
      </main>

      {/* Settings Pop-up Modal */}
      <Dialog
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        title={t("settings.title")}
        description={t("settings.desc")}
        maxWidth="max-w-5xl lg:max-w-6xl"
      >
        <SettingsView
          onClose={() => setSettingsOpen(false)}
          onSettingsSaved={() => setSettingsVersion((v) => v + 1)}
        />
      </Dialog>

      {/* Scraper & Daemon Logs Modal */}
      <ScraperLogsModal
        open={logsOpen}
        onClose={() => setLogsOpen(false)}
      />
    </div>
  )
}

export default App
