import React, { useState, useEffect, useRef } from "react"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Dialog } from "@/components/ui/dialog"
import {
  Settings,
  DollarSign,
  MapPin,
  MessageSquare,
  KeyRound,
  Globe,
  Check,
  RefreshCw,
  ExternalLink,
  ShieldCheck,
  Save,
  SlidersHorizontal,
  X,
  Wrench,
  Layers,
  ChevronDown,
  Sparkles,
  Search,
  CheckCircle2,
  Navigation,
  Trash2,
  Copy,
  Info,
  RotateCcw,
  AlertTriangle,
  Database
} from "lucide-react"
import { LocationAutocomplete } from "./LocationAutocomplete"
import { useLanguage } from "@/i18n/LanguageContext"

export interface UserSettings {
  min_price: number
  max_price: number
  target_discount_pct: number
  pitch_type: string
  custom_pitch_template: string
  enabled_sources: string[]
  search_query: string
  home_location: string
  max_distance_km: number
  prefer_local_area: boolean
  prefer_lisbon?: boolean
  language?: "pt" | "en"
  include_second_hand?: boolean
  include_refurbished?: boolean
  include_new?: boolean
  only_with_warranty?: boolean
}

export interface PlatformInfo {
  id: string
  name: string
  logo?: string
  tools_count?: number
  description?: string
  requires_auth: boolean
  auth_note?: string
  auth_url: string
  profile_active: boolean
  session_status: string
}

interface SettingsViewProps {
  onSettingsSaved?: (newSettings?: UserSettings) => void
  onClose?: () => void
}

const DEFAULT_PLATFORMS: PlatformInfo[] = [
  {
    id: "olx",
    name: "OLX Portugal",
    logo: "/logos/olx.svg",
    tools_count: 3,
    description: "Pesquisa Pública + Login para Envio de Propostas/Pitch",
    requires_auth: true,
    auth_note: "Login obrigatório apenas para envio de mensagens/propostas",
    auth_url: "https://login.olx.pt",
    profile_active: false,
    session_status: "Não Conectado"
  },
  {
    id: "facebook",
    name: "Facebook Marketplace",
    logo: "/logos/facebook.svg",
    tools_count: 2,
    description: "Pesquisa Pública + Chat do Marketplace",
    requires_auth: true,
    auth_note: "Login obrigatório apenas para envio de mensagens no Marketplace",
    auth_url: "https://www.facebook.com/login/",
    profile_active: false,
    session_status: "Não Conectado"
  },
  {
    id: "amazon",
    name: "Amazon Prime / ES",
    logo: "/logos/amazon.svg",
    tools_count: 2,
    description: "Catálogo Público Prime & Recondicionados Oficiais",
    requires_auth: false,
    auth_note: "Acesso 100% público, sem necessidade de login",
    auth_url: "https://www.amazon.es",
    profile_active: true,
    session_status: "Acesso Aberto"
  },
  {
    id: "worten",
    name: "Worten Portugal",
    logo: "/logos/worten.svg",
    tools_count: 2,
    description: "Catálogo Público, Lojas & Worten Outlet",
    requires_auth: false,
    auth_note: "Acesso 100% público, sem necessidade de login",
    auth_url: "https://www.worten.pt",
    profile_active: true,
    session_status: "Acesso Aberto"
  },
  {
    id: "cex",
    name: "CeX Webuy PT",
    logo: "/logos/cex.svg",
    tools_count: 2,
    description: "Catálogo Público por Graus A/B/C & Garantia CeX",
    requires_auth: false,
    auth_note: "Acesso 100% público, sem necessidade de login",
    auth_url: "https://pt.webuy.com",
    profile_active: true,
    session_status: "Acesso Aberto"
  },
  {
    id: "pcdiga",
    name: "PCDiga",
    logo: "/logos/pcdiga.svg",
    tools_count: 2,
    description: "Catálogo Público & Promoções Gaming",
    requires_auth: false,
    auth_note: "Acesso 100% público, sem necessidade de login",
    auth_url: "https://www.pcdiga.com",
    profile_active: true,
    session_status: "Acesso Aberto"
  },
  {
    id: "pccomponentes",
    name: "PcComponentes",
    logo: "/logos/pccomponentes.svg",
    tools_count: 2,
    description: "Catálogo Público Ibérico, Ofertas & Recondicionados",
    requires_auth: false,
    auth_note: "Acesso 100% público, sem necessidade de login",
    auth_url: "https://www.pccomponentes.pt",
    profile_active: true,
    session_status: "Acesso Aberto"
  },
  {
    id: "globaldata",
    name: "GlobalData PT",
    logo: "/logos/globaldata.svg",
    tools_count: 2,
    description: "Catálogo Público & Hardware Gaming em Stock",
    requires_auth: false,
    auth_note: "Acesso 100% público, sem necessidade de login",
    auth_url: "https://www.globaldata.pt",
    profile_active: true,
    session_status: "Acesso Aberto"
  }
]

export interface PitchStrategy {
  id: string
  title: string
  desc: string
  template: string
}

export const PITCH_STRATEGIES: PitchStrategy[] = [
  {
    id: "dinheiro_imediato",
    title: "Dinheiro Imediato",
    desc: "Levantamento rápido em mão, maior taxa de aceitação imediata.",
    template: "Olá! Tenho interesse no portátil {title}. Consegue fazer por {offer_price}€ com levantamento presencial e pagamento imediato em dinheiro ou MBWay?"
  },
  {
    id: "tecnico_hardware",
    title: "Avaliação Técnica",
    desc: "Argumentação de especificações, uso e ciclo de bateria.",
    template: "Olá! Analisei as especificações do portátil {title}. Tendo em conta o tempo de uso do equipamento e o mercado atual de usados, consegue aceitar {offer_price}€?"
  },
  {
    id: "estudante_orcamento",
    title: "Orçamento Limitado",
    desc: "Apelo a teto orçamental máximo para estudos ou trabalho.",
    template: "Olá! Tenho muito interesse no portátil {title} para fins de estudo/trabalho, mas o meu orçamento limite disponível é de {offer_price}€. Seria viável fechar negócio por esse valor?"
  },
  {
    id: "personalizado",
    title: "Modelo Personalizado",
    desc: "Texto livre usando substituição automática de variáveis.",
    template: "Olá! Vi o seu anúncio ({title}) anunciado por {price}€. Gostaria de propor o valor de {offer_price}€ (-{discount_eur}€ de desconto). Tem interesse?"
  }
]

const POPULAR_HUBS = [
  "Leiria / Marinha Grande",
  "Porto",
  "Lisboa",
  "Coimbra",
  "Braga",
  "Aveiro",
  "Faro"
]

export function SettingsView({ onSettingsSaved, onClose }: SettingsViewProps) {
  const { t, language, setLanguage } = useLanguage()
  // Connections tab is FIRST by default as requested
  const [activeSubTab, setActiveSubTab] = useState<"connections" | "location" | "pricing" | "system">("connections")
  const [settings, setSettings] = useState<UserSettings>({
    min_price: 250,
    max_price: 750,
    target_discount_pct: 20,
    pitch_type: "dinheiro_imediato",
    custom_pitch_template: "Olá! Tenho interesse no portátil. Consegue fazer por {offer_price}€ com levantamento e pagamento imediato em dinheiro?",
    enabled_sources: ["olx", "facebook", "amazon", "worten", "cex", "pcdiga", "pccomponentes", "globaldata"],
    search_query: "portatil",
    home_location: "Leiria / Marinha Grande",
    max_distance_km: 60,
    prefer_local_area: true,
    prefer_lisbon: false,
    language: language || "pt",
    include_second_hand: true,
    include_refurbished: true,
    include_new: true,
    only_with_warranty: false
  })

  const [platforms, setPlatforms] = useState<PlatformInfo[]>(DEFAULT_PLATFORMS)
  const [loading, setLoading] = useState(false)
  const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "saved" | "error">("idle")
  const [loginMessage, setLoginMessage] = useState<string | null>(null)

  // Auto-Save Management
  const initialLoadedRef = useRef(false)
  const saveTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const latestSettingsRef = useRef<UserSettings>(settings)
  const latestLanguageRef = useRef<"pt" | "en">(language || "pt")

  latestSettingsRef.current = settings
  latestLanguageRef.current = language || "pt"

  // Interactive Cookie / Session Sync Modal
  const [cookieModalPlatform, setCookieModalPlatform] = useState<PlatformInfo | null>(null)
  const [cookieInput, setCookieInput] = useState("")
  const [cookieSaving, setCookieSaving] = useState(false)
  const [clearingSessions, setClearingSessions] = useState(false)
  const [copiedScript, setCopiedScript] = useState(false)

  // Full System Reset States
  const [resetting, setResetting] = useState(false)
  const [resetSuccess, setResetSuccess] = useState<string | null>(null)
  const [resetError, setResetError] = useState<string | null>(null)
  const [confirmResetOpen, setConfirmResetOpen] = useState(false)
  const [resetOptions, setResetOptions] = useState({
    backup: true,
    reset_settings: false,
    clear_logs: true
  })

  const persistSettings = async (targetSettings: UserSettings, targetLang: "pt" | "en") => {
    setSaveStatus("saving")
    try {
      const payload: UserSettings = { ...targetSettings, language: targetLang }
      const res = await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      })
      if (res.ok) {
        setSaveStatus("saved")
        if (onSettingsSaved) onSettingsSaved(payload)
      } else {
        setSaveStatus("error")
      }
    } catch (e) {
      console.error("Auto-save failed:", e)
      setSaveStatus("error")
    }
  }

  // Auto-save whenever settings or language changes
  useEffect(() => {
    if (!initialLoadedRef.current) return

    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current)
    }

    setSaveStatus("saving")

    saveTimeoutRef.current = setTimeout(() => {
      persistSettings(settings, language || "pt")
      saveTimeoutRef.current = null
    }, 400)

    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current)
      }
    }
  }, [settings, language])

  const handleClose = () => {
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current)
      saveTimeoutRef.current = null
      persistSettings(latestSettingsRef.current, latestLanguageRef.current)
    }
    if (onClose) onClose()
  }

  const handleFullReset = async () => {
    setResetting(true)
    setResetError(null)
    setResetSuccess(null)
    try {
      const res = await fetch("/api/system/reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(resetOptions)
      })
      if (!res.ok) throw new Error("Erro ao executar reset do sistema")
      const data = await res.json()
      setResetSuccess(data.message || "Reset concluído com sucesso!")
      setConfirmResetOpen(false)
      onSettingsSaved?.()
      if (resetOptions.reset_settings) {
        fetchSettings()
      }
    } catch (err: any) {
      setResetError(err.message || "Falha na comunicação com o servidor.")
    } finally {
      setResetting(false)
    }
  }

  useEffect(() => {
    fetchSettings()
    fetchPlatforms()
  }, [])

  const fetchSettings = async () => {
    setLoading(true)
    try {
      const res = await fetch("/api/settings")
      if (res.ok) {
        const data = await res.json()
        if (data.language && (data.language === "pt" || data.language === "en")) {
          setLanguage(data.language)
        }
        setSettings({
          ...data,
          language: data.language || language,
          home_location: data.home_location || "Leiria / Marinha Grande",
          prefer_local_area: data.prefer_local_area !== undefined ? data.prefer_local_area : true
        })
      }
    } catch (e) {
      console.error("Failed to load settings:", e)
    } finally {
      setLoading(false)
      setTimeout(() => {
        initialLoadedRef.current = true
      }, 150)
    }
  }

  const fetchPlatforms = async () => {
    try {
      const res = await fetch("/api/platforms/status")
      if (res.ok) {
        const data = await res.json()
        if (data.platforms && data.platforms.length > 0) {
          setPlatforms(data.platforms)
        }
      }
    } catch (e) {
      console.error("Failed to load platforms:", e)
    }
  }

  // Opens login tab in Brave and opens session import helper
  const handleConnectPlatform = (platform: PlatformInfo) => {
    // 1. Immediately open the official login page in a new browser tab in Brave
    window.open(platform.auth_url, "_blank")

    // 2. Also ensure platform is checked in enabled sources
    if (!settings.enabled_sources.includes(platform.id)) {
      setSettings(prev => ({ ...prev, enabled_sources: [...prev.enabled_sources, platform.id] }))
    }

    // 3. Open session sync dialog if requires auth
    if (platform.requires_auth) {
      setCookieModalPlatform(platform)
      setCookieInput("")
    }
  }

  // Clears all stored sessions
  const handleClearAllSessions = async () => {
    setClearingSessions(true)
    try {
      await fetch("/api/platforms/clear", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ platform: "all" })
      })
      setLoginMessage("Todas as sessões e cookies foram limpos com sucesso. Modo convidado ativo.")
      fetchPlatforms()
      setTimeout(() => setLoginMessage(null), 4000)
    } catch (e) {
      console.error("Failed to clear sessions:", e)
    } finally {
      setClearingSessions(false)
    }
  }

  // Clear single platform session
  const handleClearSinglePlatform = async (platformId: string) => {
    try {
      await fetch("/api/platforms/clear", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ platform: platformId })
      })
      setLoginMessage(`Sessão de ${platformId.toUpperCase()} terminada.`)
      fetchPlatforms()
      setTimeout(() => setLoginMessage(null), 3000)
    } catch (e) {
      console.error(e)
    }
  }

  // Save imported cookies into backend storageState
  const handleSaveCookies = async () => {
    if (!cookieModalPlatform || !cookieInput.trim()) return
    setCookieSaving(true)
    try {
      const res = await fetch("/api/platforms/cookies", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          platform: cookieModalPlatform.id,
          cookies_raw: cookieInput.trim()
        })
      })
      if (res.ok) {
        setCookieModalPlatform(null)
        setLoginMessage(`Sessão de ${cookieModalPlatform.name} ligada com sucesso ao Scraper!`)
        fetchPlatforms()
        setTimeout(() => setLoginMessage(null), 4000)
      } else {
        alert("Formato de cookies não reconhecido. Pode colar o valor de document.cookie ou formato JSON.")
      }
    } catch (e) {
      console.error("Failed to save cookies:", e)
    } finally {
      setCookieSaving(false)
    }
  }

  const toggleSource = (sourceId: string) => {
    const list = settings.enabled_sources || []
    if (list.includes(sourceId)) {
      setSettings({ ...settings, enabled_sources: list.filter(s => s !== sourceId) })
    } else {
      setSettings({ ...settings, enabled_sources: [...list, sourceId] })
    }
  }

  return (
    <div className="space-y-4">
      {/* Top Header with Language Switcher */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
        <div>
          <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">{t("settings.title")}</h3>
          <p className="text-[11px] text-slate-500 mt-0.5">{t("settings.desc")}</p>
        </div>

        {/* Language Selection Pills */}
        <div className="flex items-center gap-1.5 bg-slate-100 p-1 rounded-xl border border-slate-200 self-start sm:self-auto shrink-0 shadow-2xs">
          <Globe className="w-3.5 h-3.5 text-slate-500 ml-1.5 shrink-0" />
          <button
            type="button"
            onClick={() => {
              setLanguage("pt")
              setSettings((prev) => ({ ...prev, language: "pt" }))
            }}
            className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-all ${
              language === "pt"
                ? "bg-white text-slate-900 shadow-xs border border-slate-200/80 font-bold"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Português (PT)
          </button>
          <button
            type="button"
            onClick={() => {
              setLanguage("en")
              setSettings((prev) => ({ ...prev, language: "en" }))
            }}
            className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-all ${
              language === "en"
                ? "bg-white text-slate-900 shadow-xs border border-slate-200/80 font-bold"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            English (EN)
          </button>
        </div>
      </div>

      {/* Sub-navigation tabs: Connections is first */}
      <div className="flex items-center gap-1.5 p-1.5 bg-slate-100/90 rounded-xl border border-slate-200 overflow-x-auto">
        <button
          type="button"
          onClick={() => setActiveSubTab("connections")}
          className={`flex-1 min-w-max py-2 px-3.5 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-all ${
            activeSubTab === "connections"
              ? "bg-white text-slate-900 shadow-xs"
              : "text-slate-600 hover:text-slate-900"
          }`}
        >
          <Globe className="w-3.5 h-3.5 text-indigo-600" />
          <span>{t("settings.tabs.connections")}</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveSubTab("location")}
          className={`flex-1 min-w-max py-2 px-3.5 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-all ${
            activeSubTab === "location"
              ? "bg-white text-slate-900 shadow-xs"
              : "text-slate-600 hover:text-slate-900"
          }`}
        >
          <MapPin className="w-3.5 h-3.5 text-indigo-600" />
          <span>{t("settings.tabs.location")}</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveSubTab("pricing")}
          className={`flex-1 min-w-max py-2 px-3.5 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-all ${
            activeSubTab === "pricing"
              ? "bg-white text-slate-900 shadow-xs"
              : "text-slate-600 hover:text-slate-900"
          }`}
        >
          <DollarSign className="w-3.5 h-3.5 text-indigo-600" />
          <span>{t("settings.tabs.pricing")}</span>
        </button>


        <button
          type="button"
          onClick={() => setActiveSubTab("system")}
          className={`flex-1 min-w-max py-2 px-3.5 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-all ${
            activeSubTab === "system"
              ? "bg-white text-slate-900 shadow-xs"
              : "text-slate-600 hover:text-slate-900"
          }`}
        >
          <RotateCcw className="w-3.5 h-3.5 text-rose-600" />
          <span>{t("settings.tabs.system")}</span>
        </button>
      </div>

      {loginMessage && (
        <div className="bg-indigo-50 border border-indigo-200 text-indigo-900 p-3 rounded-xl flex items-center gap-2.5 text-xs">
          <ShieldCheck className="w-4 h-4 text-indigo-600 shrink-0" />
          <p className="flex-1">{loginMessage}</p>
          <button
            type="button"
            onClick={() => setLoginMessage(null)}
            className="text-indigo-400 hover:text-indigo-700"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Tab 1: COMPOSIO-STYLE CONNECTIONS GRID */}
      {activeSubTab === "connections" && (
        <div className="space-y-3">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 pb-1">
            <div>
              <h3 className="text-xs font-bold text-slate-900">{t("connections.title")}</h3>
              <p className="text-[11px] text-slate-500">
                {t("connections.subtitle")}
              </p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <Button
                variant="outline"
                size="sm"
                onClick={handleClearAllSessions}
                disabled={clearingSessions}
                className="text-[11px] h-7 px-2.5 border-slate-200 text-red-600 hover:bg-red-50 hover:border-red-200 flex items-center gap-1.5"
                title={t("connections.clearAll")}
              >
                <Trash2 className="w-3 h-3 text-red-500" />
                <span>{t("connections.clearAll")}</span>
              </Button>

              <Button
                variant="outline"
                size="sm"
                onClick={fetchPlatforms}
                className="text-[11px] h-7 px-2.5 border-slate-200 text-slate-600 hover:bg-slate-50 flex items-center gap-1.5"
              >
                <RefreshCw className="w-3 h-3" />
                <span>{t("connections.refresh")}</span>
              </Button>
            </div>
          </div>

          {/* Composio-styled Integration Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3.5">
            {platforms.map((platform) => {
              const isEnabled = (settings.enabled_sources || []).includes(platform.id)
              const isSessionActive = platform.profile_active
              const toolsCount = platform.tools_count || (platform.id === "olx" ? 3 : 2)

              return (
                <div
                  key={platform.id}
                  className={`p-4 rounded-xl border bg-white transition-all shadow-xs flex flex-col justify-between ${
                    isEnabled
                      ? "border-slate-200 hover:border-slate-300"
                      : "border-slate-200/60 opacity-80 bg-slate-50/50"
                  }`}
                >
                  {/* Top Row: Logo + Name + Verified Badge + Status Action */}
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3 min-w-0">
                      {/* Brand Logo Box */}
                      <div className="w-10 h-10 rounded-xl bg-slate-50 border border-slate-200/80 p-1 flex items-center justify-center shrink-0 overflow-hidden shadow-2xs">
                        {platform.logo ? (
                          <img
                            src={platform.logo}
                            alt={platform.name}
                            className="max-w-full max-h-full object-contain"
                            onError={(e) => {
                              (e.target as HTMLElement).style.display = "none"
                            }}
                          />
                        ) : (
                          <Globe className="w-5 h-5 text-slate-500" />
                        )}
                      </div>

                      {/* Brand Title & Shield */}
                      <div className="min-w-0">
                        <div className="flex items-center gap-1">
                          <span className="font-bold text-xs text-slate-900 truncate">
                            {platform.name}
                          </span>
                          <span title="Verificado">
                            <ShieldCheck className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                          </span>
                        </div>
                        <div className="flex items-center gap-1 text-[11px] text-slate-500 mt-0.5 whitespace-nowrap">
                          <Wrench className="w-3 h-3 text-slate-400 shrink-0" />
                          <span>{toolsCount} {t("connections.tools")}</span>
                        </div>
                      </div>
                    </div>

                    {/* Right Side: Composio Status or Connect Button */}
                    <div className="shrink-0 flex items-center gap-1.5">
                      {!platform.requires_auth ? (
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-semibold text-slate-700 bg-slate-100 px-2 py-0.5 rounded-md border border-slate-200/80 flex items-center gap-1 whitespace-nowrap">
                            <ShieldCheck className="w-3 h-3 text-emerald-600" />
                            Público
                          </span>
                          <input
                            type="checkbox"
                            checked={isEnabled}
                            onChange={() => toggleSource(platform.id)}
                            className="rounded text-indigo-600 focus:ring-indigo-500 w-4 h-4 cursor-pointer"
                            title="Ativar/Desativar na pesquisa"
                          />
                        </div>
                      ) : isSessionActive ? (
                        <div className="flex items-center gap-2">
                          <span className="text-[11px] font-semibold text-emerald-600 flex items-center gap-1 whitespace-nowrap">
                            <Check className="w-3 h-3 text-emerald-600" />
                            {t("connections.active")}
                          </span>
                          <input
                            type="checkbox"
                            checked={isEnabled}
                            onChange={() => toggleSource(platform.id)}
                            className="rounded text-indigo-600 focus:ring-indigo-500 w-4 h-4 cursor-pointer"
                            title="Ativar/Desativar na pesquisa"
                          />
                        </div>
                      ) : (
                        <Button
                          size="sm"
                          onClick={() => handleConnectPlatform(platform)}
                          className="bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs h-7 px-2.5 rounded-lg flex items-center gap-1 shadow-xs shrink-0 whitespace-nowrap"
                        >
                          <span className="text-white font-semibold">{t("connections.connect")}</span>
                          <ChevronDown className="w-3 h-3 text-white" />
                        </Button>
                      )}
                    </div>
                  </div>

                  {/* Bottom Row: Description & Actions */}
                  <div className="mt-3.5 pt-2.5 border-t border-slate-100 flex items-center justify-between text-[11px] gap-2">
                    <span className="text-slate-600 truncate min-w-0 font-medium" title={platform.auth_note || platform.description}>
                      {!platform.requires_auth
                        ? "Catálogo público (Sem login obrigatório)"
                        : isSessionActive
                        ? t("connections.connected")
                        : (platform.auth_note || platform.description || t("connections.notConnected"))}
                    </span>

                    <div className="flex items-center gap-1.5 shrink-0">
                      {platform.requires_auth && isSessionActive && (
                        <button
                          type="button"
                          onClick={() => handleClearSinglePlatform(platform.id)}
                          className="text-[11px] text-slate-500 hover:text-red-600 transition-colors mr-1 font-medium"
                          title="Desconectar sessão deste portal"
                        >
                          {t("connections.disconnect")}
                        </button>
                      )}

                      {platform.requires_auth ? (
                        <button
                          type="button"
                          onClick={() => handleConnectPlatform(platform)}
                          className="px-2.5 py-1 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-800 font-semibold text-[10px] flex items-center gap-1 transition-colors shadow-2xs whitespace-nowrap shrink-0"
                          title={t("connections.openLogin")}
                        >
                          <ExternalLink className="w-3 h-3 text-slate-600" />
                          <span>{t("connections.openLogin")}</span>
                        </button>
                      ) : (
                        <a
                          href={platform.auth_url}
                          target="_blank"
                          rel="noreferrer"
                          className="px-2.5 py-1 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-[10px] flex items-center gap-1 transition-colors shadow-2xs whitespace-nowrap shrink-0"
                          title="Abrir website oficial no navegador"
                        >
                          <ExternalLink className="w-3 h-3 text-slate-500" />
                          <span>Visitar Loja</span>
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Tab 2: LOCATION & METROPOLITAN AREA CUSTOMIZATION */}
      {activeSubTab === "location" && (
        <div className="space-y-4">
          <div className="p-4 bg-slate-50/70 rounded-xl border border-slate-200/90 space-y-4">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <MapPin className="w-4 h-4 text-indigo-600" />
                <h3 className="text-xs font-bold text-slate-900">
                  {t("location.title")}
                </h3>
              </div>
              <p className="text-[11px] text-slate-500 mb-3">
                {t("location.subtitle")}
              </p>

              {/* Autocomplete Location Input */}
              <LocationAutocomplete
                value={settings.home_location}
                onChange={(loc) => setSettings({ ...settings, home_location: loc })}
                placeholder={t("location.placeholder")}
              />

              {/* Quick Select Hub Pills */}
              <div className="flex flex-wrap gap-1.5 mt-2.5">
                <span className="text-[10px] font-semibold text-slate-400 self-center mr-1">
                  {t("location.suggestions")}
                </span>
                {POPULAR_HUBS.map((hub) => (
                  <button
                    key={hub}
                    type="button"
                    onClick={() => setSettings({ ...settings, home_location: hub })}
                    className={`px-2 py-0.5 rounded-md text-[11px] font-medium border transition-colors ${
                      settings.home_location === hub
                        ? "bg-indigo-50 border-indigo-200 text-indigo-700 font-semibold"
                        : "bg-white border-slate-200 text-slate-600 hover:bg-slate-50"
                    }`}
                  >
                    {hub}
                  </button>
                ))}
              </div>
            </div>

            {/* Radius Slider */}
            <div className="pt-2 border-t border-slate-200/70">
              <div className="flex justify-between items-center mb-1">
                <label className="text-xs font-semibold text-slate-700">
                  {t("location.radiusLabel")}
                </label>
                <span className="text-xs font-bold text-indigo-600">{settings.max_distance_km} km</span>
              </div>
              <input
                type="range"
                min="10"
                max="250"
                step="10"
                value={settings.max_distance_km}
                onChange={(e) => setSettings({ ...settings, max_distance_km: parseInt(e.target.value) || 60 })}
                className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
              />
              <div className="flex justify-between text-[10px] text-slate-400 mt-1">
                <span>{t("location.radiusCouncil")}</span>
                <span>{t("location.radiusDistrict")}</span>
                <span>{t("location.radiusNational")}</span>
              </div>
            </div>

            {/* Local Prioritization Toggle */}
            <div className="pt-2 border-t border-slate-200/70">
              <label className="flex items-center gap-3 p-2.5 bg-white rounded-lg border border-slate-200 cursor-pointer hover:bg-slate-50 transition-colors">
                <input
                  type="checkbox"
                  checked={settings.prefer_local_area}
                  onChange={(e) => setSettings({ ...settings, prefer_local_area: e.target.checked })}
                  className="rounded text-indigo-600 focus:ring-indigo-500 w-4 h-4 cursor-pointer"
                />
                <div>
                  <span className="text-xs font-semibold text-slate-900 block">
                    {t("location.prioritizeLabel")}
                  </span>
                  <span className="text-[11px] text-slate-500 block">
                    {t("location.prioritizeDesc")} ({settings.home_location || "Área Base"}).
                  </span>
                </div>
              </label>
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: PRICING & SEARCH CONSTANTS */}
      {activeSubTab === "pricing" && (
        <div className="space-y-4">
          <div className="p-4 bg-slate-50/70 rounded-xl border border-slate-200/90 space-y-4">
            <div>
              <span className="text-xs font-bold text-slate-900 block mb-1">Termo de Pesquisa Padrão</span>
              <Input
                type="text"
                value={settings.search_query}
                onChange={(e) => setSettings({ ...settings, search_query: e.target.value })}
                placeholder="ex: portatil lenovo thinkpad i7"
                className="bg-white border-slate-200 text-slate-900 text-xs h-9"
              />
            </div>

            <div className="grid grid-cols-2 gap-3 pt-2 border-t border-slate-200/70">
              <div>
                <label className="text-xs font-semibold text-slate-700 block mb-1">Preço Mínimo (€)</label>
                <Input
                  type="number"
                  value={settings.min_price}
                  onChange={(e) => setSettings({ ...settings, min_price: parseFloat(e.target.value) || 0 })}
                  className="bg-white border-slate-200 text-slate-900 text-xs h-8"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-700 block mb-1">Preço Máximo (€)</label>
                <Input
                  type="number"
                  value={settings.max_price}
                  onChange={(e) => setSettings({ ...settings, max_price: parseFloat(e.target.value) || 0 })}
                  className="bg-white border-slate-200 text-slate-900 text-xs h-8"
                />
              </div>
            </div>

            <div className="pt-2 border-t border-slate-200/70">
              <div className="flex justify-between items-center mb-1">
                <label className="text-xs font-semibold text-slate-700">Desconto Pretendido na Oferta (%)</label>
                <span className="text-xs font-bold text-indigo-600">{settings.target_discount_pct}%</span>
              </div>
              <input
                type="range"
                min="5"
                max="40"
                step="5"
                value={settings.target_discount_pct}
                onChange={(e) => setSettings({ ...settings, target_discount_pct: parseInt(e.target.value) || 20 })}
                className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
              />
              <span className="text-[11px] text-slate-500 block mt-1">
                Exemplo: Num portátil anunciado a 500 €, a oferta automática sugerida será de {500 * (1 - settings.target_discount_pct / 100)} € (-{500 * (settings.target_discount_pct / 100)} €).
              </span>
            </div>

            {/* Condition & Warranty Preferences */}
            <div className="pt-3 border-t border-slate-200/70 space-y-3">
              <div className="flex items-center gap-1.5 mb-1">
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                <span className="text-xs font-bold text-slate-900">{t("pricing.conditionTitle")}</span>
              </div>

              {/* Toggle: Second-Hand / Used */}
              <label className="flex items-start gap-2.5 cursor-pointer select-none group p-2 rounded-lg bg-white border border-slate-200 hover:border-slate-300 transition-colors">
                <input
                  type="checkbox"
                  checked={settings.include_second_hand ?? true}
                  onChange={(e) => setSettings({ ...settings, include_second_hand: e.target.checked })}
                  className="mt-0.5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 accent-indigo-600 cursor-pointer h-4 w-4"
                />
                <div className="flex-1">
                  <span className="text-xs font-semibold text-slate-800 block group-hover:text-slate-950">
                    {t("pricing.includeSecondHand")}
                  </span>
                  <span className="text-[11px] text-slate-500 block">
                    {t("pricing.includeSecondHandDesc")}
                  </span>
                </div>
              </label>

              {/* Toggle: Refurbished */}
              <label className="flex items-start gap-2.5 cursor-pointer select-none group p-2 rounded-lg bg-white border border-slate-200 hover:border-slate-300 transition-colors">
                <input
                  type="checkbox"
                  checked={settings.include_refurbished ?? true}
                  onChange={(e) => setSettings({ ...settings, include_refurbished: e.target.checked })}
                  className="mt-0.5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 accent-indigo-600 cursor-pointer h-4 w-4"
                />
                <div className="flex-1">
                  <span className="text-xs font-semibold text-slate-800 block group-hover:text-slate-950">
                    {t("pricing.includeRefurbished")}
                  </span>
                  <span className="text-[11px] text-slate-500 block">
                    {t("pricing.includeRefurbishedDesc")}
                  </span>
                </div>
              </label>

              {/* Toggle: New / Sealed */}
              <label className="flex items-start gap-2.5 cursor-pointer select-none group p-2 rounded-lg bg-white border border-slate-200 hover:border-slate-300 transition-colors">
                <input
                  type="checkbox"
                  checked={settings.include_new ?? true}
                  onChange={(e) => setSettings({ ...settings, include_new: e.target.checked })}
                  className="mt-0.5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 accent-indigo-600 cursor-pointer h-4 w-4"
                />
                <div className="flex-1">
                  <span className="text-xs font-semibold text-slate-800 block group-hover:text-slate-950">
                    {t("pricing.includeNew")}
                  </span>
                  <span className="text-[11px] text-slate-500 block">
                    {t("pricing.includeNewDesc")}
                  </span>
                </div>
              </label>

              {/* Toggle: Warranty Only */}
              <label className="flex items-start gap-2.5 cursor-pointer select-none group p-2.5 rounded-lg bg-emerald-50/60 border border-emerald-200/80 hover:border-emerald-300 transition-colors">
                <input
                  type="checkbox"
                  checked={settings.only_with_warranty ?? false}
                  onChange={(e) => setSettings({ ...settings, only_with_warranty: e.target.checked })}
                  className="mt-0.5 rounded border-emerald-400 text-emerald-600 focus:ring-emerald-500 accent-emerald-600 cursor-pointer h-4 w-4"
                />
                <div className="flex-1">
                  <span className="text-xs font-semibold text-emerald-950 block flex items-center gap-1.5">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                    <span>{t("pricing.onlyWithWarranty")}</span>
                  </span>
                  <span className="text-[11px] text-emerald-800/80 block mt-0.5">
                    {t("pricing.onlyWithWarrantyDesc")}
                  </span>
                </div>
              </label>
            </div>
          </div>
        </div>
      )}


      {/* Tab 5: SYSTEM MAINTENANCE & FULL RESET */}
      {activeSubTab === "system" && (
        <div className="space-y-4">
          {resetSuccess && (
            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center justify-between text-xs text-emerald-800">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span className="font-medium">{resetSuccess}</span>
              </div>
              <button
                type="button"
                onClick={() => setResetSuccess(null)}
                className="text-emerald-500 hover:text-emerald-800"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          {resetError && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl flex items-center justify-between text-xs text-rose-800">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
                <span className="font-medium">{resetError}</span>
              </div>
              <button
                type="button"
                onClick={() => setResetError(null)}
                className="text-rose-500 hover:text-rose-800"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          {/* Database and GitHub Readiness Status */}
          <div className="p-4 bg-slate-50/70 rounded-xl border border-slate-200/90 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Database className="w-4 h-4 text-slate-700" />
                <h3 className="text-xs font-bold text-slate-900">Estado do Armazenamento Local</h3>
              </div>
              <Badge variant="outline" className="text-[10px] bg-white border-slate-200 text-slate-700 font-semibold">
                SQLite 3
              </Badge>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
              <div className="p-2.5 bg-white rounded-lg border border-slate-200">
                <span className="text-[10px] font-semibold text-slate-500 block uppercase">Ficheiro Ativo</span>
                <span className="text-xs font-bold text-slate-900 font-mono">backend/laptops.db</span>
              </div>
              <div className="p-2.5 bg-white rounded-lg border border-slate-200">
                <span className="text-[10px] font-semibold text-slate-500 block uppercase">Backup de Segurança</span>
                <span className="text-xs font-bold text-slate-900 font-mono">laptops.db.backup</span>
              </div>
              <div className="p-2.5 bg-white rounded-lg border border-slate-200">
                <span className="text-[10px] font-semibold text-slate-500 block uppercase">Proteção GitHub (.gitignore)</span>
                <span className="text-xs font-bold text-emerald-600 flex items-center gap-1">
                  <Check className="w-3 h-3" /> Ativo & Seguro
                </span>
              </div>
            </div>
          </div>

          {/* Danger Zone: Full Reset */}
          <div className="p-4 bg-rose-50/40 rounded-xl border border-rose-200/80 space-y-3">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2 text-rose-800">
                  <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
                  <h3 className="text-xs font-bold text-rose-950">Full Reset (Recomeçar do Zero)</h3>
                </div>
                <p className="text-[11px] text-slate-600 mt-1 leading-relaxed">
                  Apaga todos os portáteis raspados, negociações ativas, histórico de conversas e ficheiros de log temporários.
                  Permite testar o fluxo do scraper e do daemon a partir de uma instalação limpa para validar o projeto antes de publicar no GitHub.
                </p>
              </div>
            </div>

            <div className="space-y-2 pt-2 border-t border-rose-200/50">
              <label className="flex items-center gap-2 text-xs text-slate-700 cursor-pointer">
                <input
                  type="checkbox"
                  checked={resetOptions.backup}
                  onChange={(e) => setResetOptions({ ...resetOptions, backup: e.target.checked })}
                  className="rounded text-rose-600 focus:ring-rose-500 w-3.5 h-3.5"
                />
                <span className="font-medium">Criar cópia de segurança antes do reset (laptops.db.backup)</span>
              </label>

              <label className="flex items-center gap-2 text-xs text-slate-700 cursor-pointer">
                <input
                  type="checkbox"
                  checked={resetOptions.clear_logs}
                  onChange={(e) => setResetOptions({ ...resetOptions, clear_logs: e.target.checked })}
                  className="rounded text-rose-600 focus:ring-rose-500 w-3.5 h-3.5"
                />
                <span>Limpar ficheiro de logs e fila de respostas pendentes</span>
              </label>

              <label className="flex items-center gap-2 text-xs text-slate-700 cursor-pointer">
                <input
                  type="checkbox"
                  checked={resetOptions.reset_settings}
                  onChange={(e) => setResetOptions({ ...resetOptions, reset_settings: e.target.checked })}
                  className="rounded text-rose-600 focus:ring-rose-500 w-3.5 h-3.5"
                />
                <span>Repor definições e filtros para valores de fábrica</span>
              </label>
            </div>

            <div className="pt-2 flex justify-end">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setConfirmResetOpen(true)}
                className="border-rose-300 text-rose-700 hover:bg-rose-50 hover:text-rose-800 text-xs font-semibold h-8 px-3.5 flex items-center gap-1.5 shadow-xs"
              >
                <Trash2 className="w-3.5 h-3.5 text-rose-600" />
                <span>Iniciar Full Reset</span>
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Actions Footer with Real-Time Auto-Save Feedback */}
      <div className="pt-3 border-t border-slate-100 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          {saveStatus === "saving" && (
            <span className="text-xs font-medium text-slate-500 flex items-center gap-1.5 animate-pulse">
              <RefreshCw className="w-3.5 h-3.5 animate-spin text-indigo-600" />
              {t("settings.autoSave.saving")}
            </span>
          )}
          {saveStatus === "saved" && (
            <span className="text-xs font-semibold text-emerald-600 flex items-center gap-1.5 transition-all">
              <Check className="w-3.5 h-3.5 text-emerald-600" />
              {t("settings.autoSave.saved")}
            </span>
          )}
          {saveStatus === "idle" && (
            <span className="text-[11px] text-slate-400 font-medium flex items-center gap-1.5">
              <Check className="w-3 h-3 text-slate-400" />
              {t("settings.autoSave.hint")}
            </span>
          )}
          {saveStatus === "error" && (
            <span className="text-xs font-semibold text-rose-600 flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
              Erro ao guardar
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <Button
            type="button"
            onClick={handleClose}
            className="bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold h-8 px-4 shadow-xs flex items-center gap-1.5"
          >
            {t("settings.close")}
          </Button>
        </div>
      </div>

      {/* Dedicated Session / Cookie Import Dialog */}
      <Dialog
        open={Boolean(cookieModalPlatform)}
        onClose={() => setCookieModalPlatform(null)}
        title={`Ligar Sessão: ${cookieModalPlatform?.name}`}
        description="Sincronize a sua sessão do navegador com o motor Playwright para efetuar pesquisas e propostas como utilizador autenticado."
        maxWidth="max-w-lg"
      >
        <div className="space-y-4 py-2">
          <div className="bg-slate-50 p-3 rounded-xl border border-slate-200 space-y-2 text-xs">
            <div className="flex items-start gap-2 text-slate-700">
              <Info className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <p className="font-semibold text-slate-900">Como sincronizar em 2 passos:</p>
                <p className="text-slate-600">
                  1. O separador de login oficial de <b>{cookieModalPlatform?.name}</b> acabou de ser aberto no seu navegador. Inicie sessão normalmente.
                </p>
                <p className="text-slate-600">
                  2. Para importar a sessão para o Scraper, copie e cole aqui os cookies da sua sessão ou utilize o script de 1-clique:
                </p>
              </div>
            </div>

            <div className="pt-2 border-t border-slate-200/80 flex items-center justify-between gap-2">
              <code className="text-[10px] bg-white px-2 py-1 rounded border border-slate-200 text-slate-700 truncate max-w-[260px]">
                javascript:navigator.clipboard.writeText(document.cookie)
              </code>
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  navigator.clipboard.writeText("navigator.clipboard.writeText(document.cookie)")
                  setCopiedScript(true)
                  setTimeout(() => setCopiedScript(false), 2000)
                }}
                className="text-[10px] h-6 px-2 text-indigo-600 hover:text-indigo-700 border-indigo-200 flex items-center gap-1 shrink-0"
              >
                {copiedScript ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                <span>{copiedScript ? "Copiado!" : "Copiar Script"}</span>
              </Button>
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-700 block mb-1">
              Cole aqui os cookies da sessão (ou valor de document.cookie):
            </label>
            <textarea
              rows={4}
              value={cookieInput}
              onChange={(e) => setCookieInput(e.target.value)}
              placeholder="ex: c_user=1000...; xs=...; sb=... ou formato JSON de cookies"
              className="w-full p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-900 focus:bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500 font-mono"
            />
          </div>

          <div className="flex items-center justify-between pt-2 border-t border-slate-100">
            <a
              href={cookieModalPlatform?.auth_url}
              target="_blank"
              rel="noreferrer"
              className="text-xs text-indigo-600 hover:underline flex items-center gap-1"
            >
              Reabrir Página de Login
              <ExternalLink className="w-3 h-3" />
            </a>

            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCookieModalPlatform(null)}
                className="text-xs border-slate-200"
              >
                Cancelar
              </Button>

              <Button
                size="sm"
                onClick={handleSaveCookies}
                disabled={cookieSaving || !cookieInput.trim()}
                className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-xs"
              >
                {cookieSaving ? "A guardar..." : "Guardar Sessão no Scraper"}
              </Button>
            </div>
          </div>
        </div>
      </Dialog>

      {/* Confirmation Dialog for Full Reset */}
      <Dialog
        open={confirmResetOpen}
        onClose={() => setConfirmResetOpen(false)}
        title="Confirmar Full Reset do Sistema"
        description="Esta ação irá esvaziar as tabelas da base de dados e reiniciar o sistema do zero."
        maxWidth="max-w-md"
      >
        <div className="space-y-4 py-2">
          <div className="p-3 bg-rose-50 rounded-xl border border-rose-200 text-xs text-rose-900 space-y-2">
            <div className="flex items-center gap-2 font-bold text-rose-950">
              <AlertTriangle className="w-4 h-4 text-rose-600" />
              <span>Atenção: Ação de Reinicialização</span>
            </div>
            <p className="text-slate-700">
              Todos os negócios raspados e mensagens guardadas serão removidos da base de dados ativa.
              {resetOptions.backup && " Uma cópia de segurança completa será guardada em backend/laptops.db.backup."}
            </p>
          </div>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setConfirmResetOpen(false)}
              disabled={resetting}
              className="text-xs border-slate-200"
            >
              Cancelar
            </Button>
            <Button
              type="button"
              size="sm"
              onClick={handleFullReset}
              disabled={resetting}
              className="bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold shadow-xs flex items-center gap-1.5"
            >
              {resetting ? (
                <RefreshCw className="w-3 h-3 animate-spin" />
              ) : (
                <Trash2 className="w-3 h-3" />
              )}
              <span>{resetting ? "A reiniciar..." : "Confirmar e Limpar"}</span>
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  )
}
