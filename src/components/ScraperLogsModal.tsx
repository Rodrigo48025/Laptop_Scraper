import React, { useState, useEffect, useRef } from "react"
import { Dialog } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import {
  Terminal,
  RefreshCw,
  Copy,
  Trash2,
  Check,
  ArrowDown,
  Search,
  Filter
} from "lucide-react"

interface ScraperLogsModalProps {
  open: boolean
  onClose: () => void
}

export function ScraperLogsModal({ open, onClose }: ScraperLogsModalProps) {
  const [logs, setLogs] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [autoScroll, setAutoScroll] = useState(true)
  const [filterText, setFilterText] = useState("")
  const [copied, setCopied] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  const fetchLogs = async () => {
    try {
      setLoading(true)
      const res = await fetch("/api/logs?limit=300")
      if (res.ok) {
        const data = await res.json()
        setLogs(data.logs || [])
      }
    } catch (err) {
      console.error("Failed to load logs:", err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (open) {
      fetchLogs()
      const interval = setInterval(fetchLogs, 3000)
      return () => clearInterval(interval)
    }
  }, [open])

  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [logs, autoScroll])

  const handleCopyLogs = () => {
    navigator.clipboard.writeText(logs.join("\n"))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleClearLogs = async () => {
    try {
      await fetch("/api/logs/clear", { method: "POST" })
      setLogs([])
    } catch (err) {
      console.error("Failed to clear logs:", err)
    }
  }

  const filteredLogs = logs.filter((l) =>
    filterText ? l.toLowerCase().includes(filterText.toLowerCase()) : true
  )

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Terminal de Logs do Scraper & Daemon"
      description="Registo de eventos em tempo real, pedidos de extração, sincronização OLX e ciclos de negociação."
      maxWidth="max-w-4xl"
    >
      <div className="space-y-3 py-1">
        {/* Controls Toolbar */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5 pb-2 border-b border-slate-100">
          <div className="relative flex-1 max-w-sm">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Filtrar eventos (ex: OLX, Daemon, ERRO)..."
              value={filterText}
              onChange={(e) => setFilterText(e.target.value)}
              className="w-full pl-8 pr-3 py-1 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-900 focus:bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          <div className="flex items-center gap-1.5 flex-wrap">
            <label className="flex items-center gap-1.5 px-2.5 py-1 text-xs text-slate-600 rounded-lg border border-slate-200 bg-slate-50 cursor-pointer hover:bg-slate-100 select-none">
              <input
                type="checkbox"
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
                className="rounded text-indigo-600 focus:ring-indigo-500 w-3 h-3 cursor-pointer"
              />
              <span className="text-[11px] font-medium">Auto-Scroll</span>
            </label>

            <Button
              size="sm"
              variant="outline"
              onClick={fetchLogs}
              disabled={loading}
              className="h-7 px-2.5 text-xs text-slate-700 border-slate-200 hover:bg-slate-50 flex items-center gap-1"
            >
              <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin" : ""}`} />
              <span className="text-[11px]">Atualizar</span>
            </Button>

            <Button
              size="sm"
              variant="outline"
              onClick={handleCopyLogs}
              className="h-7 px-2.5 text-xs text-slate-700 border-slate-200 hover:bg-slate-50 flex items-center gap-1"
            >
              {copied ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
              <span className="text-[11px]">{copied ? "Copiado!" : "Copiar"}</span>
            </Button>

            <Button
              size="sm"
              variant="outline"
              onClick={handleClearLogs}
              className="h-7 px-2.5 text-xs text-red-600 border-slate-200 hover:bg-red-50 hover:border-red-200 flex items-center gap-1"
            >
              <Trash2 className="w-3 h-3 text-red-500" />
              <span className="text-[11px]">Limpar</span>
            </Button>
          </div>
        </div>

        {/* Log Viewer Container */}
        <div
          ref={scrollRef}
          className="h-96 w-full rounded-xl bg-slate-900 border border-slate-800 p-4 font-mono text-[11px] leading-relaxed text-slate-200 overflow-y-auto space-y-1 shadow-inner"
        >
          {filteredLogs.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-slate-500 py-12">
              <Terminal className="w-8 h-8 mb-2 stroke-1 text-slate-600" />
              <span className="text-xs">Nenhum evento registado de momento.</span>
            </div>
          ) : (
            filteredLogs.map((line, idx) => {
              const isError = line.toLowerCase().includes("error") || line.toLowerCase().includes("erro")
              const isWarning = line.toLowerCase().includes("warning") || line.toLowerCase().includes("aviso")
              const isSuccess = line.toLowerCase().includes("acordo") || line.toLowerCase().includes("sucesso") || line.toLowerCase().includes("complete")
              
              let textColor = "text-slate-300"
              if (isError) textColor = "text-red-400 font-semibold"
              else if (isWarning) textColor = "text-amber-300"
              else if (isSuccess) textColor = "text-emerald-400"

              return (
                <div key={idx} className={`whitespace-pre-wrap break-all ${textColor}`}>
                  {line}
                </div>
              )
            })
          )}
        </div>

        <div className="flex items-center justify-between text-[11px] text-slate-500 pt-2 border-t border-slate-100">
          <span>Total de linhas: {filteredLogs.length}</span>
          <Button
            size="sm"
            variant="outline"
            onClick={onClose}
            className="text-xs border-slate-200"
          >
            Fechar
          </Button>
        </div>
      </div>
    </Dialog>
  )
}
