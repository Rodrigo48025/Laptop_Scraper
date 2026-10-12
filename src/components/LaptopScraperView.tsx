import React, { useState, useEffect } from "react"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Dialog } from "@/components/ui/dialog"
import {
  Laptop,
  Cpu,
  HardDrive,
  Layers,
  Search,
  RefreshCw,
  ExternalLink,
  Trash2,
  Filter,
  SlidersHorizontal,
  MapPin,
  TrendingDown,
  Monitor,
  MessageSquare,
  Copy,
  Check,
  CheckCircle2,
  Play,
  Square,
  Settings,
  DollarSign,
  Tag,
  X,
  Sparkles,
  ArrowUpDown,
  Mail,
  Timer,
  ChevronDown,
  Send,
  ShieldCheck
} from "lucide-react"
import { UserSettings, PITCH_STRATEGIES } from "./SettingsView"
import { NegotiationsView } from "./NegotiationsView"
import { BatchPitchModal } from "./BatchPitchModal"
import { useLanguage } from "@/i18n/LanguageContext"

interface LaptopScraperViewProps {
  settingsVersion?: number
  daemonRunning?: boolean
  daemonUptime?: number
  onToggleDaemon?: () => void
  daemonLoading?: boolean
}

export interface LaptopDeal {
  id: number
  url: string
  title: string
  price: number
  original_price?: number
  location?: string
  travel_distance_km?: number
  is_near_lisbon?: number
  supports_shipping?: number
  brand?: string
  cpu?: string
  ram_gb?: number
  ram_type?: string
  ram_display?: string
  storage_gb?: number
  storage_type?: string
  storage_display?: string
  gpu?: string
  screen_size?: string
  condition_grade?: string
  condition?: string
  has_warranty?: number | boolean
  warranty_details?: string
  description?: string
  spec_score?: number
  value_score?: number
  deal_score?: number
  deal_verdict?: string
  source?: string
  contact_status?: string
  image_url?: string
  image_urls?: string
  updated_at?: string
}

export function LaptopScraperView({
  settingsVersion = 0,
  daemonRunning = false,
  daemonUptime = 0,
  onToggleDaemon,
  daemonLoading = false
}: LaptopScraperViewProps) {
  const { t, language } = useLanguage()

  const formatUptime = (totalSeconds: number): string => {
    if (totalSeconds < 60) {
      return `${totalSeconds}s`
    }
    const minutes = Math.floor(totalSeconds / 60)
    const seconds = totalSeconds % 60
    if (minutes < 60) {
      return `${minutes}m ${seconds < 10 ? `0${seconds}` : seconds}s`
    }
    const hours = Math.floor(minutes / 60)
    const remMinutes = minutes % 60
    return `${hours}h ${remMinutes < 10 ? `0${remMinutes}` : remMinutes}m`
  }
  const [activeTab, setActiveTab] = useState<"deals" | "negotiations">("deals")
  const [laptops, setLaptops] = useState<LaptopDeal[]>([])
  const [loading, setLoading] = useState(false)
  const [stats, setStats] = useState<any>({ total: 0, total_laptops: 0, avg_price: 0, near_lisbon: 0, negotiated: 0 })
  const [limit, setLimit] = useState<number>(250)
  const [totalCount, setTotalCount] = useState<number>(0)

  // Filters
  const [search, setSearch] = useState("")
  const [minPrice, setMinPrice] = useState<string>("200")
  const [maxPrice, setMaxPrice] = useState<string>("800")
  const [selectedSource, setSelectedSource] = useState<string>("all")
  const [selectedCondition, setSelectedCondition] = useState<string>("all")
  const [warrantyOnly, setWarrantyOnly] = useState<boolean>(false)
  const [sortBy, setSortBy] = useState<string>("value")

  // Negotiation Modal
  const [negotiateModalOpen, setNegotiateModalOpen] = useState(false)
  const [batchPitchModalOpen, setBatchPitchModalOpen] = useState(false)
  const [selectedLaptop, setSelectedLaptop] = useState<LaptopDeal | null>(null)
  const [customDiscount, setCustomDiscount] = useState<number>(20)
  const [activeStrategy, setActiveStrategy] = useState<string>("dinheiro_imediato")
  const [composedPitch, setComposedPitch] = useState<string>("")
  const [copiedPitch, setCopiedPitch] = useState(false)
  const [pitchSentSuccess, setPitchSentSuccess] = useState(false)

  // Settings Cache
  const [userSettings, setUserSettings] = useState<UserSettings | null>(null)
  const [scraping, setScraping] = useState(false)
  const [daemonNotice, setDaemonNotice] = useState<string | null>(null)

  // Live Link Verification & Non-Blocking Progress Bar
  const [verifyingLinks, setVerifyingLinks] = useState(false)
  const [verifyProgress, setVerifyProgress] = useState<{
    checked: number
    total: number
    removedCount: number
    activeCount: number
    currentTitle?: string
    done: boolean
  } | null>(null)
  const [confirmedActiveIds, setConfirmedActiveIds] = useState<Set<number>>(new Set())
  const eventSourceRef = React.useRef<EventSource | null>(null)
  const dismissTimerRef = React.useRef<NodeJS.Timeout | null>(null)

  const stopLinkVerification = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
    setVerifyingLinks(false)
    fetchStats()
  }

  const startLinkVerification = () => {
    if (verifyingLinks) {
      stopLinkVerification()
      return
    }

    if (dismissTimerRef.current) {
      clearTimeout(dismissTimerRef.current)
      dismissTimerRef.current = null
    }

    setVerifyingLinks(true)
    setVerifyProgress({
      checked: 0,
      total: filteredLaptops.length || laptops.length || 250,
      removedCount: 0,
      activeCount: 0,
      done: false
    })

    const params = new URLSearchParams()
    params.set("limit", String(limit || 250))
    if (selectedSource && selectedSource !== "all") params.set("source", selectedSource)
    if (search.trim()) params.set("query", search.trim())
    if (minPrice) params.set("min_price", minPrice)
    if (maxPrice) params.set("max_price", maxPrice)

    const url = `/api/laptops/verify-stream?${params.toString()}`
    const es = new EventSource(url)
    eventSourceRef.current = es

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === "start") {
          setVerifyProgress({
            checked: 0,
            total: data.total,
            removedCount: 0,
            activeCount: 0,
            done: false
          })
        } else if (data.type === "item") {
          setVerifyProgress((prev) => ({
            checked: data.checked,
            total: data.total,
            removedCount: data.removed_count,
            activeCount: data.active_count,
            currentTitle: data.title,
            done: false
          }))

          if (data.status === "removed") {
            // Instantly remove dead/expired laptop from the UI grid without full reload
            setLaptops((prev) => prev.filter((item) => item.id !== data.id))
            setTotalCount((prev) => (prev !== null ? Math.max(0, prev - 1) : null))
            setStats((prev) => ({
              ...prev,
              total: Math.max(0, (prev.total || 1) - 1),
              total_laptops: Math.max(0, (prev.total_laptops || 1) - 1)
            }))
          } else if (data.status === "active") {
            // Record active verified ID
            setConfirmedActiveIds((prev) => new Set(prev).add(data.id))
          }
        } else if (data.type === "complete") {
          setVerifyProgress((prev) =>
            prev
              ? {
                  ...prev,
                  done: true,
                  checked: data.checked,
                  total: data.total,
                  removedCount: data.removed_count,
                  activeCount: data.active_count
                }
              : null
          )
          setVerifyingLinks(false)
          es.close()
          eventSourceRef.current = null
          fetchStats()

          // Auto-dismiss after 6 seconds
          dismissTimerRef.current = setTimeout(() => {
            setVerifyProgress(null)
          }, 6000)
        }
      } catch (err) {
        console.error("Error parsing verify stream SSE:", err)
      }
    }

    es.onerror = () => {
      es.close()
      eventSourceRef.current = null
      setVerifyingLinks(false)
      fetchLaptops(true)
      fetchStats()
    }
  }

  // Cleanup EventSource on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
      if (dismissTimerRef.current) {
        clearTimeout(dismissTimerRef.current)
      }
    }
  }, [])

  const fetchSettings = async () => {
    try {
      const res = await fetch("/api/settings")
      if (res.ok) {
        const data = await res.json()
        setUserSettings(data)
        if (data.min_price) setMinPrice(String(data.min_price))
        if (data.max_price) setMaxPrice(String(data.max_price))
        if (data.target_discount_pct) setCustomDiscount(data.target_discount_pct)
      }
    } catch (e) {
      console.error(e)
    }
  }

  const fetchStats = async () => {
    try {
      const res = await fetch("/api/laptops/stats")
      if (res.ok) {
        const data = await res.json()
        setStats(data)
      }
    } catch (e) {
      console.error(e)
    }
  }

  const fetchLaptops = async (silent = false, customLimit?: number) => {
    if (!silent) setLoading(true)
    try {
      const effectiveLimit = customLimit !== undefined ? customLimit : limit
      const params = new URLSearchParams()
      if (search) params.append("search", search)
      if (minPrice) params.append("min_price", minPrice)
      if (maxPrice) params.append("max_price", maxPrice)
      if (selectedSource && selectedSource !== "all") params.append("source", selectedSource)
      if (selectedCondition && selectedCondition !== "all") params.append("condition", selectedCondition)
      if (warrantyOnly) params.append("has_warranty", "true")
      params.append("sort_by", sortBy === "price_asc" ? "price" : sortBy === "specs" ? "spec_score" : "deal_score")
      params.append("sort_order", sortBy === "price_asc" ? "asc" : "desc")
      params.append("limit", String(effectiveLimit))

      const res = await fetch(`/api/laptops?${params.toString()}`)
      if (res.ok) {
        const data = await res.json()
        setLaptops(data.laptops || [])
        if (typeof data.total === "number") {
          setTotalCount(data.total)
        }
      }
    } catch (e) {
      console.error(e)
    } finally {
      if (!silent) setLoading(false)
    }
  }

  const triggerScrapeJob = async () => {
    setScraping(true)
    setDaemonNotice("A extrair anúncios de portáteis de todas as lojas ativas (Amazon, Worten, CeX, PCDiga, OLX...)...")
    try {
      const minP = Number(minPrice) || 200
      const maxP = Number(maxPrice) || 800
      const q = search.trim() || userSettings?.search_query || "portatil"
      const sources = userSettings?.enabled_sources || ["amazon", "cex", "pcdiga", "globaldata", "pccomponentes", "olx", "worten"]

      const res = await fetch("/api/laptops/scrape", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: q,
          min_price: minP,
          max_price: maxP,
          sources: sources,
          headless: true
        })
      })
      if (res.ok) {
        setTimeout(() => {
          fetchLaptops(true)
          fetchStats()
        }, 1200)
      }
    } catch (err) {
      console.error("Failed to trigger scrape:", err)
    } finally {
      setTimeout(() => setScraping(false), 1500)
    }
  }

  // Continuous 5-second database polling: smooth live updates without UI flicker
  useEffect(() => {
    fetchLaptops(false)
    fetchStats()
    fetchSettings()

    const pollInterval = setInterval(() => {
      fetchLaptops(true)
      fetchStats()
    }, 5000)

    return () => clearInterval(pollInterval)
  }, [search, minPrice, maxPrice, sortBy, limit, settingsVersion])

  // Daemon state notice
  useEffect(() => {
    if (daemonRunning) {
      setDaemonNotice("Demon em execução: A pesquisar e extrair anúncios de portáteis em segundo plano...")
    } else {
      setDaemonNotice(null)
    }
  }, [daemonRunning])

  const handleOpenNegotiate = (laptop: LaptopDeal) => {
    setSelectedLaptop(laptop)
    const discount = userSettings?.target_discount_pct || 20
    setCustomDiscount(discount)
    const strategy = userSettings?.pitch_type || "dinheiro_imediato"
    setActiveStrategy(strategy)
    const origPrice = laptop.price || 500
    const offerPrice = Math.round(origPrice * (1 - discount / 100))

    const matchedStrat = PITCH_STRATEGIES.find((s) => s.id === strategy)
    const template =
      userSettings?.custom_pitch_template ||
      matchedStrat?.template ||
      "Olá! Tenho interesse no portátil {title}. Consegue fazer por {offer_price}€ com levantamento presencial e pagamento imediato em dinheiro ou MBWay?"

    const populated = template
      .replace(/{title}/g, laptop.title || "portátil")
      .replace(/{price}/g, `${origPrice}`)
      .replace(/{offer_price}/g, `${offerPrice}`)
      .replace(/{discount_eur}/g, `${origPrice - offerPrice}`)

    setComposedPitch(populated)
    setNegotiateModalOpen(true)
  }

  const handleStrategyChange = (stratId: string) => {
    setActiveStrategy(stratId)
    if (!selectedLaptop) return
    const origPrice = selectedLaptop.price || 500
    const offerPrice = Math.round(origPrice * (1 - customDiscount / 100))
    const matchedStrat = PITCH_STRATEGIES.find((s) => s.id === stratId)
    const template =
      matchedStrat?.template ||
      userSettings?.custom_pitch_template ||
      "Olá! Tenho interesse no portátil {title}. Consegue fazer por {offer_price}€?"

    const populated = template
      .replace(/{title}/g, selectedLaptop.title || "portátil")
      .replace(/{price}/g, `${origPrice}`)
      .replace(/{offer_price}/g, `${offerPrice}`)
      .replace(/{discount_eur}/g, `${origPrice - offerPrice}`)

    setComposedPitch(populated)
  }

  const handleDiscountChange = (newDiscount: number) => {
    setCustomDiscount(newDiscount)
    if (!selectedLaptop) return
    const origPrice = selectedLaptop.price || 500
    const offerPrice = Math.round(origPrice * (1 - newDiscount / 100))

    const matchedStrat = PITCH_STRATEGIES.find((s) => s.id === activeStrategy)
    const template =
      matchedStrat?.template ||
      userSettings?.custom_pitch_template ||
      "Olá! Tenho interesse no portátil {title}. Consegue fazer por {offer_price}€?"

    const populated = template
      .replace(/{title}/g, selectedLaptop.title || "portátil")
      .replace(/{price}/g, `${origPrice}`)
      .replace(/{offer_price}/g, `${offerPrice}`)
      .replace(/{discount_eur}/g, `${origPrice - offerPrice}`)

    setComposedPitch(populated)
  }

  const handleCopyPitch = () => {
    navigator.clipboard.writeText(composedPitch)
    setCopiedPitch(true)
    setTimeout(() => setCopiedPitch(false), 2000)
  }

  const handleSendEmail = () => {
    if (!selectedLaptop) return
    const subject = encodeURIComponent(`Interesse no portátil: ${selectedLaptop.title}`)
    const body = encodeURIComponent(composedPitch)
    window.open(`mailto:?subject=${subject}&body=${body}`, "_blank")
  }

  const handleSaveNegotiation = async () => {
    if (!selectedLaptop) return
    try {
      await fetch(`/api/laptops/${selectedLaptop.id}/negotiate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          discount_pct: customDiscount / 100,
          method: activeStrategy,
          custom_message: composedPitch
        })
      })
      await fetch(`/api/laptops/${selectedLaptop.id}/contact`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ contact_status: "offered" })
      })
      setPitchSentSuccess(true)
      setTimeout(() => {
        setPitchSentSuccess(false)
        setNegotiateModalOpen(false)
        fetchLaptops()
      }, 1500)
    } catch (e) {
      console.error(e)
    }
  }

  const filteredLaptops = laptops.filter(l => {
    if (selectedSource !== "all" && l.source?.toLowerCase() !== selectedSource.toLowerCase()) {
      return false
    }
    if (selectedCondition !== "all") {
      const cond = (l.condition_grade || l.condition || "").toLowerCase()
      if (selectedCondition === "usado" && !(cond.includes("usado") || cond.includes("segunda"))) return false
      if (selectedCondition === "recondicionado" && !(cond.includes("recondicionado") || cond.includes("renewed") || cond.includes("refurbished"))) return false
      if (selectedCondition === "novo" && !(cond.includes("novo") || cond.includes("selado"))) return false
    }
    if (warrantyOnly && !(l.has_warranty === 1 || l.has_warranty === true)) {
      return false
    }
    return true
  })

  return (
    <div className="space-y-6">
      {/* Navigation Bar */}
      <div className="bg-white rounded-xl border border-slate-200 p-1.5 shadow-xs flex items-center justify-between">
        <div className="flex items-center gap-1">
          <button
            onClick={() => setActiveTab("deals")}
            className={`px-4 py-2 rounded-lg text-xs font-semibold flex items-center gap-2 transition-all ${
              activeTab === "deals"
                ? "bg-indigo-600 text-white shadow-xs"
                : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
            }`}
          >
            <Laptop className="w-3.5 h-3.5" />
            {t("catalog.tabs.deals")}
          </button>

          <button
            onClick={() => setActiveTab("negotiations")}
            className={`px-4 py-2 rounded-lg text-xs font-semibold flex items-center gap-2 transition-all ${
              activeTab === "negotiations"
                ? "bg-indigo-600 text-white shadow-xs"
                : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5" />
            {t("catalog.tabs.negotiations")}
          </button>
        </div>

        <div className="flex items-center gap-2 pr-2">
          {onToggleDaemon && (
            daemonRunning ? (
              <div className="flex items-center gap-1.5">
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 shadow-2xs">
                  <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse shrink-0" />
                  <span className="text-[11px] font-semibold">Demon Ativo</span>
                  <span className="inline-flex items-center gap-1 font-mono text-[10px] font-bold bg-emerald-100/90 text-emerald-900 px-1.5 py-0.5 rounded border border-emerald-200/60">
                    <Timer className="w-2.5 h-2.5 text-emerald-700" />
                    {formatUptime(daemonUptime)}
                  </span>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={onToggleDaemon}
                  disabled={daemonLoading}
                  className="border-red-200 bg-red-50 hover:bg-red-100 text-red-700 text-xs h-8 px-2.5 font-semibold flex items-center gap-1.5 shadow-2xs"
                  title={t("app.stopDaemon")}
                >
                  <Square className="w-3 h-3 fill-current text-red-600" />
                  <span className="hidden sm:inline">{t("app.stopDaemon")}</span>
                </Button>
              </div>
            ) : (
              <Button
                size="sm"
                onClick={onToggleDaemon}
                disabled={daemonLoading}
                className="bg-slate-900 hover:bg-slate-800 text-white font-semibold text-xs h-8 px-3.5 shadow-xs flex items-center gap-1.5"
                title={t("app.startDaemon")}
              >
                <Play className="w-3 h-3 fill-current text-white" />
                <span className="text-white font-semibold">{t("app.startDaemon")}</span>
              </Button>
            )
          )}

          {/* Manual Scrape Trigger */}
          <Button
            variant="outline"
            size="sm"
            onClick={triggerScrapeJob}
            disabled={scraping}
            className="border-slate-200 bg-white hover:bg-slate-50 text-slate-800 text-xs h-8 px-2.5 sm:px-3 font-semibold flex items-center gap-1.5 shadow-2xs"
            title="Extrair novas oportunidades de portáteis em segundo plano"
          >
            <Search className={`w-3.5 h-3.5 text-indigo-600 ${scraping ? "animate-pulse" : ""}`} />
            <span className="hidden sm:inline">{scraping ? "A Extrair..." : "Pesquisar Ofertas"}</span>
          </Button>

          {/* Batch Pitch Launcher */}
          <Button
            size="sm"
            onClick={() => setBatchPitchModalOpen(true)}
            className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs h-8 px-3 shadow-xs flex items-center gap-1.5"
            title="Lançar propostas e fazer pitches automáticos por segmento e plataforma"
          >
            <Send className="w-3.5 h-3.5" />
            <span className="font-semibold">{t("catalog.batchPitchBtn") || "Fazer Pitches"}</span>
          </Button>

          {/* 5-second Live DB Polling Indicator */}
          <div
            className="hidden md:flex items-center gap-1.5 px-2 py-1 rounded-md bg-slate-100 border border-slate-200 text-[11px] text-slate-600 font-mono shadow-2xs"
            title="Sincronização contínua com a base de dados a cada 5 segundos"
          >
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse shrink-0" />
            <span>5s DB</span>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={startLinkVerification}
            disabled={loading && !verifyingLinks}
            className={`border-slate-200 bg-white text-slate-800 hover:bg-slate-50 text-xs h-8 px-2.5 font-medium transition-all ${
              verifyingLinks ? "border-indigo-500 bg-indigo-50 text-indigo-700 shadow-2xs" : ""
            }`}
            title={verifyingLinks ? "Parar verificação de links" : "Verificar links individuais e atualizar catálogo"}
          >
            <RefreshCw className={`w-3.5 h-3.5 text-slate-700 ${verifyingLinks || loading ? "animate-spin text-indigo-600" : ""}`} />
            <span className="hidden sm:inline text-[11px] ml-1.5 font-semibold">
              {verifyingLinks ? "A Verificar..." : "Verificar Links"}
            </span>
          </Button>
        </div>
      </div>

      {daemonRunning && daemonNotice && (
        <div className="bg-indigo-50 border border-indigo-200/80 text-indigo-950 px-4 py-3 rounded-xl text-xs flex items-center justify-between shadow-2xs">
          <div className="flex items-center gap-2.5">
            <RefreshCw className="w-4 h-4 text-indigo-600 animate-spin shrink-0" />
            <span className="font-medium">{daemonNotice}</span>
            <span className="inline-flex items-center gap-1 font-mono text-[11px] font-semibold text-indigo-900 bg-indigo-100/90 px-1.5 py-0.5 rounded border border-indigo-200/70">
              <Timer className="w-3 h-3 text-indigo-600" />
              {formatUptime(daemonUptime)}
            </span>
          </div>
          <button
            type="button"
            onClick={() => setDaemonNotice(null)}
            className="text-indigo-400 hover:text-indigo-700 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Tab: Negotiations */}
      {activeTab === "negotiations" && <NegotiationsView />}

      {/* Tab: Deals Catalog */}
      {activeTab === "deals" && (
        <div className="space-y-6">
          {/* Minimalist Metric KPIs */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <Card className="bg-white border-slate-200 shadow-xs p-4">
              <span className="text-[11px] font-medium text-slate-500 uppercase tracking-wider block">{t("catalog.stats.total")}</span>
              <span className="text-2xl font-bold text-slate-900 mt-1 block">
                {stats.total_laptops || stats.total || totalCount || laptops.length}
              </span>
              {selectedSource !== "all" && (
                <span className="text-[10px] text-slate-500 block mt-0.5">
                  {filteredLaptops.length} da plataforma {selectedSource.toUpperCase()}
                </span>
              )}
            </Card>

            <Card className="bg-white border-slate-200 shadow-xs p-4">
              <span className="text-[11px] font-medium text-slate-500 uppercase tracking-wider block">{t("catalog.stats.avgPrice")}</span>
              <span className="text-2xl font-bold text-slate-900 mt-1 block">
                {stats.avg_price ? `${Math.round(stats.avg_price)} €` : "—"}
              </span>
            </Card>

            <Card className="bg-white border-slate-200 shadow-xs p-4">
              <span className="text-[11px] font-medium text-slate-500 uppercase tracking-wider block">
                {t("catalog.stats.nationalShipping")}
              </span>
              <span className="text-2xl font-bold text-indigo-600 mt-1 block">
                {laptops.filter(l => l.supports_shipping !== 0).length}
              </span>
            </Card>

            <Card className="bg-white border-slate-200 shadow-xs p-4">
              <span className="text-[11px] font-medium text-slate-500 uppercase tracking-wider block">{t("catalog.stats.inProgress")}</span>
              <span className="text-2xl font-bold text-emerald-600 mt-1 block">
                {laptops.filter(l => l.contact_status === "offered").length}
              </span>
            </Card>
          </div>

          {/* Search & Fast Filters */}
          <Card className="bg-white border-slate-200 shadow-xs p-4">
            <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-4">
              <div className="relative flex-1">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <Input
                  type="text"
                  placeholder={t("catalog.searchPlaceholder")}
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && fetchLaptops()}
                  className="pl-9 bg-slate-50 border-slate-200 text-xs text-slate-900 focus:bg-white"
                />
              </div>

              <div className="flex flex-wrap items-center gap-3">
                {/* Source Filter Chips */}
                <div className="flex items-center bg-slate-100 p-1 rounded-lg border border-slate-200 text-xs flex-wrap gap-0.5">
                  {["all", "olx", "facebook", "amazon", "worten", "cex", "pcdiga", "pccomponentes", "globaldata"].map((src) => (
                    <button
                      key={src}
                      onClick={() => setSelectedSource(src)}
                      className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-all uppercase ${
                        selectedSource === src
                          ? "bg-white text-slate-900 shadow-xs font-semibold"
                          : "text-slate-600 hover:text-slate-900"
                      }`}
                    >
                      {src === "all" ? t("catalog.allPlatforms") : src}
                    </button>
                  ))}
                </div>

                {/* Sort selector */}
                <select
                  value={sortBy}
                  onChange={(e) => { setSortBy(e.target.value); setTimeout(fetchLaptops, 100); }}
                  className="h-9 px-3 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-700 focus:bg-white focus:outline-none"
                >
                  <option value="value">{t("catalog.sort.value")}</option>
                  <option value="price_asc">{t("catalog.sort.priceAsc")}</option>
                  <option value="specs">{t("catalog.sort.specs")}</option>
                </select>

                {/* Limit selector */}
                <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-lg px-2.5 h-9">
                  <span className="text-[11px] font-medium text-slate-500 hidden sm:inline">{t("catalog.limitSelector")}</span>
                  <select
                    value={limit}
                    onChange={(e) => {
                      const newLim = Number(e.target.value)
                      setLimit(newLim)
                      fetchLaptops(false, newLim)
                    }}
                    className="bg-transparent text-xs font-semibold text-slate-700 focus:outline-none cursor-pointer"
                  >
                    <option value={50}>50</option>
                    <option value={100}>100</option>
                    <option value={250}>250 (Todos)</option>
                    <option value={500}>500</option>
                  </select>
                </div>

                <Button
                  size="sm"
                  onClick={() => fetchLaptops(false)}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs h-9 px-4 font-semibold"
                >
                  {t("catalog.filter")}
                </Button>
              </div>
            </div>

            {/* Condition & Warranty Filter Bar */}
            <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-slate-100 mt-2">
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="text-[11px] font-semibold text-slate-500 mr-1">Condição:</span>
                {[
                  { id: "all", label: t("catalog.filter.condition.all") },
                  { id: "usado", label: t("catalog.filter.condition.used") },
                  { id: "recondicionado", label: t("catalog.filter.condition.refurbished") },
                  { id: "novo", label: t("catalog.filter.condition.new") }
                ].map((cond) => (
                  <button
                    key={cond.id}
                    onClick={() => setSelectedCondition(cond.id)}
                    className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-all ${
                      selectedCondition === cond.id
                        ? "bg-slate-900 text-white font-semibold shadow-2xs"
                        : "bg-slate-100 text-slate-600 hover:text-slate-900 hover:bg-slate-200"
                    }`}
                  >
                    {cond.label}
                  </button>
                ))}
              </div>

              <button
                type="button"
                onClick={() => setWarrantyOnly(!warrantyOnly)}
                className={`px-3 py-1 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all border ${
                  warrantyOnly
                    ? "bg-emerald-600 text-white border-emerald-700 shadow-xs"
                    : "bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100"
                }`}
                title="Mostrar apenas portáteis com garantia ativa confirmada"
              >
                <ShieldCheck className={`w-3.5 h-3.5 ${warrantyOnly ? "text-white" : "text-emerald-600"}`} />
                <span>{t("catalog.filter.warrantyOnly")}</span>
              </button>
            </div>
          </Card>

          {/* Catalog Count Banner */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 px-1 text-xs text-slate-600">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-800">
                {t("catalog.showingCount")
                  .replace("{current}", String(filteredLaptops.length))
                  .replace("{total}", String(totalCount || stats.total_laptops || stats.total || laptops.length))}
              </span>
              {selectedSource !== "all" && (
                <span className="text-[11px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-medium border border-slate-200">
                  {selectedSource.toUpperCase()}
                </span>
              )}
            </div>

            {filteredLaptops.length < (totalCount || stats.total_laptops || 0) && (
              <button
                type="button"
                onClick={() => {
                  const allLimit = totalCount || stats.total_laptops || 500
                  setLimit(allLimit)
                  fetchLaptops(false, allLimit)
                }}
                className="text-indigo-600 hover:text-indigo-800 font-semibold text-xs hover:underline flex items-center gap-1 self-start sm:self-auto"
              >
                <span>{t("catalog.showAll").replace("{total}", String(totalCount || stats.total_laptops || 0))}</span>
              </button>
            )}
          </div>

          {/* Non-Blocking Real-Time Link Verification Progress Bar */}
          {verifyProgress && (
            <div className="bg-white border border-slate-200/90 rounded-xl p-3 shadow-xs space-y-2 transition-all animate-in fade-in duration-200">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
                <div className="flex items-center gap-2 min-w-0">
                  {verifyProgress.done ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  ) : (
                    <RefreshCw className="w-4 h-4 text-indigo-600 animate-spin shrink-0" />
                  )}
                  <div className="min-w-0">
                    <span className="font-semibold text-slate-900 block sm:inline">
                      {verifyProgress.done
                        ? t("catalog.verifyDone")
                            .replace("{removed}", String(verifyProgress.removedCount))
                            .replace("{active}", String(verifyProgress.activeCount))
                        : t("catalog.verifyingLinks")}
                    </span>
                    {!verifyProgress.done && verifyProgress.currentTitle && (
                      <p className="text-[11px] text-slate-500 truncate max-w-sm md:max-w-md lg:max-w-xl">
                        {verifyProgress.currentTitle}
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0 self-end sm:self-auto">
                  <span className="text-[11px] font-mono font-medium text-slate-600 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                    {verifyProgress.checked} / {verifyProgress.total} ({Math.round((verifyProgress.checked / Math.max(verifyProgress.total, 1)) * 100)}%)
                  </span>
                  {verifyProgress.removedCount > 0 && (
                    <span className="text-[11px] font-semibold text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200">
                      -{verifyProgress.removedCount} expirados
                    </span>
                  )}
                  {verifyingLinks && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={stopLinkVerification}
                      className="h-6 px-2 text-[11px] font-medium border-slate-300 text-slate-700 hover:bg-slate-100"
                    >
                      {t("catalog.cancelVerify")}
                    </Button>
                  )}
                  {verifyProgress.done && (
                    <button
                      type="button"
                      onClick={() => setVerifyProgress(null)}
                      className="text-slate-400 hover:text-slate-700 p-0.5 rounded hover:bg-slate-100 transition-colors"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>

              {/* Smooth Progress Track */}
              <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
                <div
                  className={`h-full transition-all duration-300 ease-out rounded-full ${
                    verifyProgress.done ? "bg-emerald-500" : "bg-indigo-600"
                  }`}
                  style={{
                    width: `${Math.min(100, Math.round((verifyProgress.checked / Math.max(verifyProgress.total, 1)) * 100))}%`
                  }}
                />
              </div>
            </div>
          )}

          {/* Deals Grid */}
          {loading && laptops.length === 0 ? (
            <div className="py-16 text-center">
              <RefreshCw className="w-6 h-6 text-indigo-600 animate-spin mx-auto mb-2" />
              <p className="text-xs text-slate-500">{t("catalog.loading")}</p>
            </div>
          ) : filteredLaptops.length === 0 ? (
            <Card className="bg-white border-slate-200 p-16 text-center shadow-xs">
              <Laptop className="w-10 h-10 text-slate-300 mx-auto mb-3" />
              <h3 className="text-sm font-semibold text-slate-800">{t("catalog.noLaptops")}</h3>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                {daemonRunning
                  ? "O Demon está ativo e a pesquisar continuamente oportunidades em todas as lojas ativas. Os portáteis vão surgir automaticamente."
                  : "O catálogo está vazio. Ative o Demon para iniciar a extração contínua de oportunidades e monitorização de preços."}
              </p>
              <div className="mt-5 flex flex-wrap items-center justify-center gap-3">
                <Button
                  size="sm"
                  onClick={triggerScrapeJob}
                  disabled={scraping}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-xs flex items-center gap-2 px-4 h-9"
                  title="Extrair ofertas agora de todas as lojas online"
                >
                  <Search className={`w-3.5 h-3.5 ${scraping ? "animate-pulse" : ""}`} />
                  <span>{scraping ? "A Extrair de 8 Lojas..." : "Pesquisar Ofertas Agora"}</span>
                </Button>

                {onToggleDaemon && (
                  daemonRunning ? (
                    <>
                      <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 font-semibold shadow-2xs">
                        <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse shrink-0" />
                        <span>Demon a Pesquisar em Segundo Plano...</span>
                        <span className="inline-flex items-center gap-1 font-mono text-[11px] font-semibold bg-emerald-100/90 text-emerald-900 px-1.5 py-0.5 rounded border border-emerald-200/60">
                          <Timer className="w-3 h-3 text-emerald-700" />
                          {formatUptime(daemonUptime)}
                        </span>
                      </div>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={onToggleDaemon}
                        disabled={daemonLoading}
                        className="border-red-200 bg-red-50 hover:bg-red-100 text-red-700 text-xs font-semibold h-8 px-3 flex items-center gap-1.5 shadow-2xs"
                        title={t("app.stopDaemon")}
                      >
                        <Square className="w-3 h-3 fill-current text-red-600" />
                        <span>{t("app.stopDaemon")}</span>
                      </Button>
                    </>
                  ) : (
                    <Button
                      size="sm"
                      onClick={onToggleDaemon}
                      disabled={daemonLoading}
                      className="bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold shadow-xs flex items-center gap-2 px-4 h-9"
                    >
                      <Play className="w-3.5 h-3.5 fill-current text-white" />
                      <span>{t("app.startDaemon")}</span>
                    </Button>
                  )
                )}
              </div>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
              {filteredLaptops.map((laptop) => {
                const discountPct = userSettings?.target_discount_pct || 20
                const rawPrice = typeof laptop.price === "number" && !isNaN(laptop.price)
                  ? laptop.price
                  : parseFloat(String(laptop.price || 0)) || 0
                const targetOffer = Math.round(rawPrice * (1 - discountPct / 100))

                return (
                  <Card
                    key={laptop.id}
                    className="bg-white border-slate-200/90 shadow-xs hover:shadow-md transition-all flex flex-col justify-between overflow-hidden group"
                  >
                    <div>
                      {/* Laptop Photo Header - Taller & Completely Shown */}
                      <div className="relative h-60 sm:h-64 w-full bg-slate-50/90 flex items-center justify-center overflow-hidden border-b border-slate-100">
                        {laptop.image_url ? (
                          <>
                            {/* Ambient blurred backdrop to fill aspect ratio smoothly */}
                            <div
                              className="absolute inset-0 bg-cover bg-center filter blur-md opacity-25 scale-110 pointer-events-none"
                              style={{ backgroundImage: `url(${laptop.image_url})` }}
                            />
                            {/* Main laptop photo - completely shown with zero cropping */}
                            <img
                              src={laptop.image_url}
                              alt={laptop.title}
                              loading="lazy"
                              className="relative z-10 max-h-full max-w-full object-contain p-2 group-hover:scale-105 transition-transform duration-300 drop-shadow-xs"
                              onError={(e) => {
                                const target = e.currentTarget
                                target.style.display = "none"
                                const parent = target.parentElement
                                const fb = parent?.querySelector(".fallback-photo")
                                if (fb) fb.classList.remove("hidden")
                              }}
                            />
                          </>
                        ) : null}
                        <div
                          className={`fallback-photo ${laptop.image_url ? "hidden" : ""} w-full h-full flex flex-col items-center justify-center text-slate-300 bg-slate-50`}
                        >
                          <Laptop className="w-12 h-12 stroke-1 mb-1.5 text-slate-300" />
                          <span className="text-[11px] font-medium text-slate-400">Sem Fotografia</span>
                        </div>

                        {/* Floating Badges over Photo */}
                        <div className="absolute top-2.5 left-2.5 right-2.5 flex items-start justify-between gap-2 pointer-events-none z-20">
                          {(() => {
                            const s = (laptop.source || "olx").toLowerCase()
                            let logo: string | null = "/logos/olx.svg"
                            let label = laptop.source || "OLX"
                            if (s.includes("facebook")) { logo = "/logos/facebook.svg"; label = "Facebook" }
                            else if (s.includes("amazon")) { logo = "/logos/amazon.svg"; label = "Amazon" }
                            else if (s.includes("worten")) { logo = "/logos/worten.svg"; label = "Worten" }
                            else if (s.includes("cex")) { logo = "/logos/cex.svg"; label = "CeX" }
                            else if (s.includes("pcdiga")) { logo = "/logos/pcdiga.svg"; label = "PCDiga" }
                            else if (s.includes("pccomponentes")) { logo = "/logos/pccomponentes.svg"; label = "PcComponentes" }
                            else if (s.includes("globaldata")) { logo = "/logos/globaldata.svg"; label = "GlobalData" }
                            else if (!s.includes("olx")) { logo = null }

                            return (
                              <Badge
                                variant="secondary"
                                className="text-[10px] uppercase font-bold tracking-wider bg-white/95 backdrop-blur-xs text-slate-800 border border-slate-200/80 px-2 py-0.5 flex items-center gap-1.5 shadow-xs"
                              >
                                {logo && (
                                  <img src={logo} alt={label} className="w-3.5 h-3.5 object-contain" />
                                )}
                                <span>{label}</span>
                              </Badge>
                            )
                          })()}

                          <div className="flex items-center gap-1.5 flex-wrap justify-end">
                            {confirmedActiveIds.has(laptop.id) && (
                              <Badge
                                variant="secondary"
                                className="text-[10px] font-semibold bg-emerald-50/95 backdrop-blur-xs text-emerald-800 border border-emerald-200/90 px-1.5 py-0.5 flex items-center gap-1 shadow-xs"
                              >
                                <Check className="w-2.5 h-2.5 text-emerald-600" />
                                <span>{t("catalog.verifiedBadge")}</span>
                              </Badge>
                            )}

                            {laptop.contact_status === "offered" ? (
                              <Badge className="bg-indigo-600 text-white border-0 text-[10px] font-medium shadow-xs">
                                {t("catalog.offeredBadge")}
                              </Badge>
                            ) : typeof laptop.travel_distance_km === "number" && !isNaN(laptop.travel_distance_km) && laptop.travel_distance_km <= (userSettings?.max_distance_km || 40) ? (
                              <Badge className="bg-slate-800 text-white border-0 text-[10px] font-medium shadow-xs">
                                {t("catalog.localBadge")} ({laptop.travel_distance_km.toFixed(0)} km)
                              </Badge>
                            ) : laptop.supports_shipping !== 0 ? (
                              <Badge className="bg-slate-100 text-slate-700 border border-slate-200/80 text-[10px] font-medium shadow-2xs">
                                {t("catalog.shippingBadge")}
                              </Badge>
                            ) : null}
                          </div>
                        </div>
                      </div>

                      {/* Title & Location */}
                      <div className="p-4 pb-2">
                        <h3 className="font-bold text-sm text-slate-900 leading-snug line-clamp-2" title={laptop.title}>
                          {laptop.title}
                        </h3>
                        <div className="flex items-center gap-1.5 text-xs text-slate-500 mt-1.5">
                          <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                          <span className="truncate">{laptop.location || "Portugal"}</span>
                          {typeof laptop.travel_distance_km === "number" && !isNaN(laptop.travel_distance_km) ? (
                            <span className="text-[11px] text-slate-400">({laptop.travel_distance_km.toFixed(0)} km)</span>
                          ) : null}
                        </div>

                        {/* Condition & Warranty Badges */}
                        <div className="flex items-center gap-1.5 flex-wrap mt-2.5">
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 border border-slate-200">
                            {laptop.condition_grade || laptop.condition || t("catalog.badge.used")}
                          </span>
                          {laptop.has_warranty === 1 || laptop.has_warranty === true ? (
                            <span className="text-[10px] font-semibold px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-800 border border-emerald-200 flex items-center gap-1">
                              <ShieldCheck className="w-3 h-3 text-emerald-600 shrink-0" />
                              <span className="truncate max-w-[160px]">{laptop.warranty_details || t("catalog.badge.warranty")}</span>
                            </span>
                          ) : (
                            <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-md bg-slate-50 text-slate-400 border border-slate-200/60">
                              {t("catalog.badge.noWarranty")}
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Hardware Specification Grid */}
                      <div className="mx-4 my-2 p-3 bg-slate-50 rounded-lg border border-slate-100 grid grid-cols-2 gap-2 text-xs">
                        <div className="flex items-center gap-2">
                          <Cpu className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                          <span className="truncate text-slate-700 font-medium">{laptop.cpu || "CPU"}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Layers className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                          <span className="text-slate-700 font-medium">{laptop.ram_display || `${laptop.ram_gb || 16} GB`}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <HardDrive className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                          <span className="truncate text-slate-700 font-medium">{laptop.storage_display || `${laptop.storage_gb || 512} GB`}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Monitor className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                          <span className="truncate text-slate-700 font-medium">{laptop.gpu || "GPU"}</span>
                        </div>
                      </div>

                      {/* Pricing Comparison */}
                      <div className="px-4 py-3 flex items-baseline justify-between border-t border-slate-100 mt-2">
                        <div>
                          <span className="text-[10px] uppercase font-medium text-slate-400 block">{t("catalog.listedPrice")}</span>
                          <span className="text-lg font-bold text-slate-900">{rawPrice.toFixed(0)} €</span>
                        </div>
                        <div className="text-right">
                          <span className="text-[10px] uppercase font-medium text-slate-400 block">{t("catalog.targetOffer")} (-{discountPct}%)</span>
                          <span className="text-sm font-bold text-indigo-600">{targetOffer} €</span>
                        </div>
                      </div>
                    </div>

                    {/* Bottom Action Footer */}
                    <div className="p-4 pt-2 border-t border-slate-100 bg-slate-50/50 flex items-center justify-between gap-2">
                      <Button
                        size="sm"
                        onClick={() => handleOpenNegotiate(laptop)}
                        className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs h-8 px-3 shadow-xs flex items-center gap-1.5 flex-1"
                      >
                        <MessageSquare className="w-3.5 h-3.5" />
                        {t("catalog.negotiateBtn")}
                      </Button>

                      <a
                        href={laptop.url}
                        target="_blank"
                        rel="noreferrer"
                        className="h-8 px-2.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-100 text-slate-700 flex items-center justify-center transition-colors"
                        title={t("catalog.openOriginal")}
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    </div>
                  </Card>
                )
              })}
            </div>
          )}

          {/* Pagination & Load More Footer */}
          {!loading && filteredLaptops.length > 0 && (
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 py-4 px-4 border border-slate-200 bg-white shadow-xs rounded-xl mt-6">
              <div className="text-xs text-slate-600 font-medium">
                {t("catalog.showingCount")
                  .replace("{current}", String(filteredLaptops.length))
                  .replace("{total}", String(totalCount || stats.total_laptops || stats.total || laptops.length))}
              </div>

              <div className="flex items-center gap-2">
                {laptops.length < (totalCount || stats.total_laptops || 0) ? (
                  <>
                    <Button
                      size="sm"
                      onClick={() => {
                        const newLimit = limit + 100
                        setLimit(newLimit)
                        fetchLaptops(false, newLimit)
                      }}
                      className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs h-9 px-4 font-semibold shadow-xs flex items-center gap-1.5"
                    >
                      <ChevronDown className="w-4 h-4" />
                      <span>{t("catalog.loadMore")}</span>
                    </Button>

                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        const allLimit = totalCount || stats.total_laptops || 500
                        setLimit(allLimit)
                        fetchLaptops(false, allLimit)
                      }}
                      className="border-slate-200 text-slate-700 hover:bg-slate-100 text-xs h-9 px-3 font-medium"
                    >
                      {t("catalog.showAll").replace("{total}", String(totalCount || stats.total_laptops || 0))}
                    </Button>
                  </>
                ) : (
                  <span className="text-xs text-emerald-700 font-medium flex items-center gap-1.5 bg-emerald-50 border border-emerald-200 px-3 py-1.5 rounded-lg">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                    {t("catalog.allLoaded")} ({filteredLaptops.length})
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Negotiation Pitch Modal */}
      <Dialog
        open={negotiateModalOpen}
        onClose={() => setNegotiateModalOpen(false)}
        title={t("proposal.title")}
        description={t("proposal.desc")}
      >
        {selectedLaptop && (
          <div className="space-y-4 py-2">
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
              <span className="text-xs font-bold text-slate-900 block truncate">{selectedLaptop.title}</span>
              <div className="flex justify-between items-center mt-2 text-xs">
                <span className="text-slate-500">{t("catalog.listedPrice")}: <b className="text-slate-900">{typeof selectedLaptop.price === "number" ? selectedLaptop.price.toFixed(0) : selectedLaptop.price} €</b></span>
                <span className="text-indigo-600 font-bold">
                  {t("proposal.calculatedOffer")}: {Math.round(((typeof selectedLaptop.price === "number" ? selectedLaptop.price : parseFloat(String(selectedLaptop.price || 0))) || 500) * (1 - customDiscount / 100))} € (-{customDiscount}%)
                </span>
              </div>
            </div>

            <div>
              <div className="flex justify-between items-center mb-1">
                <label className="text-xs font-semibold text-slate-700">{t("proposal.adjustDiscount")}</label>
                <span className="text-xs font-bold text-indigo-600">{customDiscount}%</span>
              </div>
              <input
                type="range"
                min="5"
                max="40"
                step="5"
                value={customDiscount}
                onChange={(e) => handleDiscountChange(parseInt(e.target.value) || 20)}
                className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-700 block mb-1.5">
                {t("proposal.strategy")}
              </label>
              <div className="grid grid-cols-2 gap-1.5">
                {PITCH_STRATEGIES.map((strat) => (
                  <button
                    key={strat.id}
                    type="button"
                    onClick={() => handleStrategyChange(strat.id)}
                    className={`px-2.5 py-1.5 rounded-lg text-[11px] font-medium border text-left transition-all ${
                      activeStrategy === strat.id
                        ? "bg-indigo-50 border-indigo-200 text-indigo-700 font-semibold shadow-2xs"
                        : "bg-white border-slate-200 text-slate-600 hover:bg-slate-50"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="truncate">{strat.title}</span>
                      {activeStrategy === strat.id && <Check className="w-3 h-3 text-indigo-600 shrink-0" />}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <div className="flex justify-between items-center mb-1">
                <label className="text-xs font-semibold text-slate-700">{t("proposal.message")}</label>
                <div className="flex items-center gap-1">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={handleCopyPitch}
                    className="h-6 px-2 text-xs text-indigo-600 hover:text-indigo-700 flex items-center gap-1"
                  >
                    {copiedPitch ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                    {copiedPitch ? t("proposal.copied") : t("proposal.copy")}
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={handleSendEmail}
                    className="h-6 px-2 text-xs text-slate-600 hover:text-slate-900 flex items-center gap-1"
                    title="Abrir no cliente de email pré-preenchido"
                  >
                    <Mail className="w-3 h-3 text-indigo-600" />
                    {t("proposal.sendEmail")}
                  </Button>
                </div>
              </div>
              <textarea
                rows={4}
                value={composedPitch}
                onChange={(e) => setComposedPitch(e.target.value)}
                className="w-full p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-900 focus:bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500 font-sans"
              />
            </div>
          </div>
        )}

        <div className="flex items-center justify-between pt-4 border-t border-slate-100">
          {selectedLaptop?.url && (
            <a
              href={selectedLaptop.url}
              target="_blank"
              rel="noreferrer"
              className="text-xs text-indigo-600 hover:underline flex items-center gap-1.5 font-medium"
            >
              <span>{t("proposal.viewOfficial")}</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          )}

          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setNegotiateModalOpen(false)}
              className="text-xs border-slate-200"
            >
              {t("proposal.close")}
            </Button>
            <Button
              size="sm"
              onClick={handleSaveNegotiation}
              className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs"
            >
              {pitchSentSuccess ? t("proposal.saved") : t("proposal.saveProposal")}
            </Button>
          </div>
        </div>
      </Dialog>

      {/* Batch Pitch Launcher Modal */}
      <BatchPitchModal
        open={batchPitchModalOpen}
        onClose={() => setBatchPitchModalOpen(false)}
        onSuccess={() => {
          fetchLaptops(true)
          fetchStats()
        }}
        onOpenNegotiations={() => setActiveTab("negotiations")}
      />
    </div>
  )
}
