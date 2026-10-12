import React, { useState, useEffect } from "react"
import { Dialog } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Send,
  MessageSquare,
  Check,
  CheckCircle2,
  ShieldCheck,
  ShieldAlert,
  AlertCircle,
  Key,
  Laptop,
  Sliders,
  DollarSign,
  X,
  RefreshCw,
  Info,
  ChevronDown,
  ChevronUp,
  Building2,
  Users,
  Sparkles,
  TrendingDown,
  Truck,
  MapPin,
  PackageCheck,
  Handshake,
  Upload
} from "lucide-react"
import { useLanguage } from "@/i18n/LanguageContext"

interface BatchPitchModalProps {
  open: boolean
  onClose: () => void
  onSuccess?: () => void
  onOpenNegotiations?: () => void
}

interface PitchTarget {
  id: number
  title: string
  price: number
  offer_price: number
  discount_pct: number
  discount_eur: number
  source: string
  url: string
  image_url: string
  location: string
  travel_distance_km?: number
  spec_score?: number
  deal_score?: number
  message: string
  has_session: boolean
}

interface PlatformSessionInfo {
  certified: boolean
  requires_login: boolean
}

const PLATFORM_LOGOS: Record<string, string> = {
  olx: "/logos/olx.svg",
  facebook: "/logos/facebook.svg",
  amazon: "/logos/amazon.svg",
  worten: "/logos/worten.svg",
  cex: "/logos/cex.svg",
  pcdiga: "/logos/pcdiga.svg",
  pccomponentes: "/logos/pccomponentes.svg",
  globaldata: "/logos/globaldata.svg"
}

export const PITCH_TEMPLATES_MATRIX: Record<string, Record<string, string>> = {
  ctt_cobranca: {
    direto: "Olá! Tenho muito interesse no portátil {title}. Aceita fechar negócio por {offer_price}€ com envio via CTT Expresso à cobrança (ou Entregas OLX) e pagamento no ato de entrega? Assumo eu a totalidade dos portes de envio. Obrigado!",
    dinheiro_imediato: "Olá! Tenho muito interesse no portátil {title}. Se aceitar fechar por {offer_price}€ com envio via CTT Expresso à cobrança, fecho negócio hoje mesmo e assumo a totalidade dos portes de envio. Obrigado!",
    estudante: "Boa tarde! Gostei muito do portátil {title}. Sou estudante e o meu orçamento limite é de {offer_price}€. Seria possível fechar negócio por esse valor com envio via CTT Expresso à cobrança (ou Entregas OLX)? Assumo eu os portes de envio. Muito obrigado!",
    suave: "Olá! O portátil {title} tem ótimas características. O valor anunciado está um pouco acima do que pretendia gastar. Seria viável considerar uma oferta de {offer_price}€ com envio via CTT à cobrança? Assumo eu os portes de envio. Obrigado!"
  },
  presencial: {
    direto: "Olá! Tenho muito interesse no portátil {title}. Consegue fazer por {offer_price}€ com levantamento presencial em mãos e pagamento a pronto em dinheiro ou MBWay? Posso passar a levantar em {location}. Obrigado!",
    dinheiro_imediato: "Olá! Tenho muito interesse no portátil {title}. Consegue fazer por {offer_price}€? Tenho o dinheiro disponível e posso passar a levantar em mãos hoje mesmo em {location} com pagamento a pronto em dinheiro ou MBWay. Obrigado!",
    estudante: "Boa tarde! Gostei muito do portátil {title}. Sou estudante e o meu orçamento limite é de {offer_price}€. Seria possível fechar negócio por esse valor com levantamento presencial em mãos em {location} e pagamento a pronto? Obrigado!",
    suave: "Olá! Gostei bastante do portátil {title}. Seria viável negociar o valor para {offer_price}€ com levantamento em mãos na sua zona ({location}) e pagamento a pronto em dinheiro ou MBWay? Muito obrigado!"
  },
  auto: {
    direto: "Olá! Tenho muito interesse no portátil {title}. Como resido na Marinha Grande, aceita fechar negócio por {offer_price}€ com envio à cobrança via CTT Expresso (ou Entregas OLX) e pagamento na entrega? Assumo eu os portes de envio. Muito obrigado!",
    dinheiro_imediato: "Olá! Tenho muito interesse no portátil {title}. Se aceitar {offer_price}€ com envio à cobrança via CTT Expresso, fecho negócio hoje mesmo e assumo a totalidade dos portes de envio. Muito obrigado!",
    estudante: "Boa tarde! Gostei muito do portátil {title}. Sou estudante e o meu orçamento limite é de {offer_price}€. Como resido na Marinha Grande, aceita fechar negócio por esse valor com envio via CTT à cobrança? Assumo eu os portes de envio. Muito obrigado!",
    suave: "Olá! Gostei bastante do portátil {title}. Como resido na Marinha Grande, seria viável considerar {offer_price}€ com envio à cobrança via CTT Expresso? Assumo eu os portes de envio. Muito obrigado!"
  }
}

export function getCoherentTemplate(method: string, tone: string): string {
  const m = PITCH_TEMPLATES_MATRIX[method] || PITCH_TEMPLATES_MATRIX.auto
  return m[tone] || m.direto || PITCH_TEMPLATES_MATRIX.auto.direto
}

const PITCH_TONES = [
  { id: "direto", label: "Direto / Profissional", desc: "Claro e objetivo" },
  { id: "dinheiro_imediato", label: "Dinheiro Imediato (Hoje)", desc: "Liquidez e fecho rápido" },
  { id: "estudante", label: "Estudante (Limite)", desc: "Orçamento fixo justificado" },
  { id: "suave", label: "Suave / Negociável", desc: "Proposta flexível" }
]

export function BatchPitchModal({ open, onClose, onSuccess, onOpenNegotiations }: BatchPitchModalProps) {
  const { t } = useLanguage()

  // Step 1: Platforms & Session (Only OLX & Facebook require login)
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>(["olx", "facebook"])
  const [showRetailStores, setShowRetailStores] = useState(false)

  // Step 2: Pitch Order / Target Segment
  const [targetSection, setTargetSection] = useState<"value" | "specs" | "price_asc" | "all">("value")

  // Step 3: Delivery Method, Pitch Tone & Discount
  const [deliveryMethod, setDeliveryMethod] = useState<"auto" | "ctt_cobranca" | "presencial">("auto")
  const [pitchTone, setPitchTone] = useState<string>("direto")
  const [discountPct, setDiscountPct] = useState<number>(20)
  const [templateText, setTemplateText] = useState<string>(() => getCoherentTemplate("auto", "direto"))
  const [isCustomized, setIsCustomized] = useState<boolean>(false)

  // Data & State
  const [loading, setLoading] = useState(false)
  const [launchingPlatform, setLaunchingPlatform] = useState<string | null>(null)
  const [targets, setTargets] = useState<PitchTarget[]>([])
  const [sampleMessage, setSampleMessage] = useState<string>("")
  const [totalEligible, setTotalEligible] = useState<number>(0)
  const [platformSessions, setPlatformSessions] = useState<Record<string, PlatformSessionInfo>>({})
  const [dispatching, setDispatching] = useState(false)
  const [dispatchResult, setDispatchResult] = useState<{ success: boolean; count: number } | null>(null)

  // Remote Cookie Import
  const [cookieModalPlatform, setCookieModalPlatform] = useState<string | null>(null)
  const [cookieInput, setCookieInput] = useState("")
  const [cookieSaving, setCookieSaving] = useState(false)
  const [cookieError, setCookieError] = useState<string | null>(null)

  // Delivery & Payment Methods
  const DELIVERY_METHODS = [
    {
      id: "auto",
      name: "Auto-Adaptativo por Raio (Recomendado)",
      desc: "Presencial em mãos para vendedores perto de Leiria (< 50 km); Envio CTT à cobrança para o resto do país.",
      icon: Truck
    },
    {
      id: "ctt_cobranca",
      name: "Envio CTT à Cobrança / Entregas OLX",
      desc: "Pagamento apenas no ato de entrega após conferir o equipamento. Portes assumidos pelo comprador.",
      icon: PackageCheck
    },
    {
      id: "presencial",
      name: "Levantamento Presencial em Mãos",
      desc: "Encontro presencial na zona do vendedor com pagamento a pronto em dinheiro ou MBWay.",
      icon: Handshake
    }
  ]

  // C2C Direct Negotiation Platforms (Only OLX and Facebook require login/chat)
  const C2C_PLATFORMS = [
    { id: "olx", name: "OLX Portugal", tag: "Chat Direto C2C", defaultActive: true },
    { id: "facebook", name: "Facebook Marketplace", tag: "Chat Messenger", defaultActive: true }
  ]

  // Fixed Retail Stores (Non-negotiable in chat, including Amazon)
  const RETAIL_PLATFORMS = [
    { id: "amazon", name: "Amazon Marketplace / Prime" },
    { id: "worten", name: "Worten Portugal" },
    { id: "cex", name: "CeX Webuy" },
    { id: "pcdiga", name: "PCDiga" },
    { id: "pccomponentes", name: "PcComponentes" },
    { id: "globaldata", name: "GlobalData" }
  ]

  // Check which selected platforms require login and are not certified
  const missingSessionPlatforms = selectedPlatforms.filter(
    plat => (plat === "olx" || plat === "facebook") && !platformSessions[plat]?.certified
  )
  const canDispatch = missingSessionPlatforms.length === 0 && targets.length > 0

  // Selection handlers: Tone and Delivery Method seamlessly harmonize!
  const handleSelectDeliveryMethod = (method: "auto" | "ctt_cobranca" | "presencial") => {
    setDeliveryMethod(method)
    if (!isCustomized) {
      setTemplateText(getCoherentTemplate(method, pitchTone))
    }
  }

  const handleSelectPitchTone = (tone: string) => {
    setPitchTone(tone)
    if (!isCustomized) {
      setTemplateText(getCoherentTemplate(deliveryMethod, tone))
    }
  }

  const handleTemplateChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value
    setTemplateText(val)
    const expected = getCoherentTemplate(deliveryMethod, pitchTone)
    setIsCustomized(val.trim() !== expected.trim())
  }

  const handleResetToOptimized = () => {
    setTemplateText(getCoherentTemplate(deliveryMethod, pitchTone))
    setIsCustomized(false)
  }

  const handleInsertTag = (tag: string) => {
    setTemplateText(prev => prev.trim() ? `${prev.trim()} ${tag}` : tag)
    setIsCustomized(true)
  }

  // Instant client-side resolved sample message
  const resolvedSampleMessage = React.useMemo(() => {
    const baseTpl = templateText || getCoherentTemplate(deliveryMethod, pitchTone)
    const target = targets[0]
    const title = target?.title || "Portátil Gaming / Trabalho"
    const origPrice = target ? target.price : 500
    const offerPrice = Math.round(origPrice * (1.0 - discountPct / 100.0))
    const loc = target?.location || "Leiria"

    return baseTpl
      .replace(/\{title\}/g, title)
      .replace(/\{offer_price\}/g, `${offerPrice}`)
      .replace(/\{price\}/g, `${Math.round(origPrice)}`)
      .replace(/\{discount_pct\}/g, `${discountPct}`)
      .replace(/\{location\}/g, loc)
  }, [templateText, deliveryMethod, pitchTone, targets, discountPct])

  // Load preview data whenever criteria change
  useEffect(() => {
    if (!open) return
    loadPreview()
  }, [open, targetSection, selectedPlatforms, discountPct, deliveryMethod, pitchTone])

  // Debounced preview sync for manual template typing
  useEffect(() => {
    if (!open) return
    const timer = setTimeout(() => {
      loadPreview()
    }, 400)
    return () => clearTimeout(timer)
  }, [templateText])

  const loadPreview = async (overrideTemplate?: string) => {
    setLoading(true)
    setDispatchResult(null)
    try {
      const activeTpl = overrideTemplate !== undefined ? overrideTemplate : templateText
      const params = new URLSearchParams()
      params.append("section", targetSection)
      params.append("platforms", selectedPlatforms.join(","))
      params.append("discount_pct", String(discountPct))
      params.append("pitch_type", pitchTone)
      params.append("delivery_method", deliveryMethod)
      params.append("limit", "500") // Send to all eligible laptops in the selection
      if (activeTpl && activeTpl.trim()) {
        params.append("custom_template", activeTpl.trim())
      }

      const res = await fetch(`/api/pitches/preview?${params.toString()}`)
      if (res.ok) {
        const data = await res.json()
        setTargets(data.targets || [])
        setSampleMessage(data.sample_message || (data.targets && data.targets[0]?.message) || "")
        setTotalEligible(data.total_eligible || 0)
        setPlatformSessions(data.platform_sessions || {})
      }
    } catch (e) {
      console.error("Failed to load pitch preview:", e)
    } finally {
      setLoading(false)
    }
  }

  const togglePlatform = (platformId: string) => {
    if (selectedPlatforms.includes(platformId)) {
      if (selectedPlatforms.length > 1) {
        setSelectedPlatforms(selectedPlatforms.filter(p => p !== platformId))
      }
    } else {
      setSelectedPlatforms([...selectedPlatforms, platformId])
    }
  }

  const handleLaunchLogin = async (platformId: string) => {
    setLaunchingPlatform(platformId)
    try {
      const res = await fetch("/api/platforms/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ platform: platformId })
      })
      if (res.ok) {
        // Poll for 15 seconds to check if storage state was captured
        const poll = setInterval(async () => {
          const checkRes = await fetch("/api/platforms/status")
          if (checkRes.ok) {
            const data = await checkRes.json()
            const match = data.platforms?.find((p: any) => p.id === platformId)
            if (match?.profile_active) {
              clearInterval(poll)
              setLaunchingPlatform(null)
              loadPreview()
            }
          }
        }, 3000)

        setTimeout(() => {
          clearInterval(poll)
          setLaunchingPlatform(null)
          loadPreview()
        }, 20000)
      }
    } catch (e) {
      console.error("Failed to launch login session:", e)
      setLaunchingPlatform(null)
    }
  }

  const handleImportCookies = async () => {
    if (!cookieModalPlatform || !cookieInput.trim()) return
    setCookieSaving(true)
    setCookieError(null)
    try {
      const res = await fetch("/api/platforms/cookies", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          platform: cookieModalPlatform,
          cookies_raw: cookieInput.trim()
        })
      })
      if (res.ok) {
        setCookieModalPlatform(null)
        setCookieInput("")
        loadPreview()
      } else {
        const err = await res.json()
        setCookieError(err.detail || "Formato de cookies inválido.")
      }
    } catch (e: any) {
      setCookieError("Erro ao comunicar com o servidor: " + (e.message || "desconhecido"))
    } finally {
      setCookieSaving(false)
    }
  }

  const handleDispatchPitches = async () => {
    if (!canDispatch || targets.length === 0) return
    setDispatching(true)
    try {
      const formattedTargets = targets.map(t => {
        const title = t.title || "computador portátil"
        const origPrice = t.price || 500
        const offerPrice = t.offer_price || Math.round(origPrice * (1.0 - discountPct / 100.0))
        const loc = t.location || "Portugal"

        const finalMsg = templateText
          ? templateText
              .replace(/\{title\}/g, title)
              .replace(/\{offer_price\}/g, String(offerPrice))
              .replace(/\{price\}/g, String(Math.round(origPrice)))
              .replace(/\{discount_pct\}/g, String(discountPct))
              .replace(/\{location\}/g, loc)
          : t.message

        return {
          laptop_id: t.id,
          offer_price: offerPrice,
          discount_pct: discountPct,
          pitch_message: finalMsg,
          strategy_used: `${pitchTone}_${deliveryMethod}`
        }
      })

      const res = await fetch("/api/pitches/dispatch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          targets: formattedTargets,
          mode: "record"
        })
      })

      if (res.ok) {
        const data = await res.json()
        setDispatchResult({
          success: true,
          count: data.created_count || targets.length
        })
        if (onSuccess) onSuccess()
      }
    } catch (e) {
      console.error("Failed to dispatch pitches:", e)
    } finally {
      setDispatching(false)
    }
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Lançar Propostas & Pitches em Massa"
      description="Configure as plataformas de envio, a ordem de envio das propostas e o método de entrega."
      maxWidth="max-w-4xl"
      noBodyScroll={true}
    >
      <div className="flex flex-col h-[75vh] max-h-[75vh]">
        {/* Modal Scrollable Body (Single Scrollbar) */}
        <div className="flex-1 min-h-0 overflow-y-auto space-y-6 pr-2 pb-2">
          {/* Success Banner */}
          {dispatchResult && (
            <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 flex items-start justify-between gap-3 shadow-xs">
              <div className="flex items-start gap-3">
                <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
                <div>
                  <h3 className="text-xs font-bold text-emerald-900">
                    {dispatchResult.count} Propostas Lançadas a Toda a Seleção!
                  </h3>
                  <p className="text-xs text-emerald-700 mt-0.5">
                    As ofertas foram registadas na base de dados e marcadas no catálogo. Estão prontas para acompanhamento na aba "Negociações Ativas".
                  </p>
                </div>
              </div>
              {onOpenNegotiations && (
                <Button
                  size="sm"
                  onClick={() => {
                    onClose()
                    onOpenNegotiations()
                  }}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs h-8 px-3 font-semibold shadow-xs shrink-0"
                >
                  <MessageSquare className="w-3.5 h-3.5 mr-1.5" />
                  Ver Negociações
                </Button>
              )}
            </div>
          )}

          {/* TOPIC 1: Platforms & Session Certification */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-slate-800 uppercase tracking-wider block">
                1. Plataformas de Envio (Chat Direto C2C)
              </label>
              <button
                type="button"
                onClick={() => loadPreview()}
                className="text-[11px] text-indigo-600 hover:text-indigo-800 flex items-center gap-1 font-medium"
              >
                <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin" : ""}`} />
                <span>Atualizar Sessões</span>
              </button>
            </div>

            {/* C2C Platforms (Direct Chat) with official platform SVGs */}
            <div className="space-y-2">
              {C2C_PLATFORMS.map(plat => {
                const isSelected = selectedPlatforms.includes(plat.id)
                const session = platformSessions[plat.id]
                const isCertified = Boolean(session?.certified)

                return (
                  <div
                    key={plat.id}
                    className={`p-3 rounded-xl border transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                      isSelected
                        ? "bg-white border-slate-300 shadow-xs"
                        : "bg-slate-100/60 border-slate-200 opacity-60"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => togglePlatform(plat.id)}
                        className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 w-4 h-4 cursor-pointer"
                      />
                      <div className="w-7 h-7 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-center p-1 shrink-0">
                        {PLATFORM_LOGOS[plat.id] ? (
                          <img
                            src={PLATFORM_LOGOS[plat.id]}
                            alt={plat.name}
                            className="w-full h-full object-contain"
                          />
                        ) : (
                          <Laptop className="w-4 h-4 text-slate-400" />
                        )}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-slate-900">{plat.name}</span>
                          <span className="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded font-medium border border-slate-200">
                            {plat.tag}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-500 mt-0.5">
                          {plat.id === "olx"
                            ? "Plataforma primária C2C com envio de propostas para o chat de mensagens."
                            : plat.id === "facebook"
                            ? "Chat do Messenger para propostas diretas a particulares."
                            : "Ofertas de vendedores do Marketplace e recondicionados."}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 self-start sm:self-auto pl-7 sm:pl-0">
                      {isCertified ? (
                        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold">
                          <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                          <span>Sessão Ativa</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-2">
                          <div className="flex items-center gap-1 px-2 py-1 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-[11px] font-medium">
                            <AlertCircle className="w-3 h-3 text-amber-600" />
                            <span>{plat.id === "amazon" ? "Acesso Aberto" : "Sessão Necessária"}</span>
                          </div>

                          {plat.id !== "amazon" && (
                            <div className="flex items-center gap-1.5">
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => handleLaunchLogin(plat.id)}
                                disabled={launchingPlatform === plat.id}
                                className="text-xs h-7 px-2 border-slate-200 text-indigo-600 hover:text-indigo-700 hover:bg-indigo-50 font-medium flex items-center gap-1"
                                title="Abre o navegador Playwright na máquina host"
                              >
                                <Key className="w-3 h-3" />
                                <span>{launchingPlatform === plat.id ? "A Abrir..." : "Iniciar Sessão"}</span>
                              </Button>

                              <button
                                type="button"
                                onClick={() => {
                                  setCookieModalPlatform(plat.id)
                                  setCookieInput("")
                                  setCookieError(null)
                                }}
                                className="text-[11px] h-7 px-2 border border-slate-200 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100 flex items-center gap-1 font-medium transition-colors"
                                title="Importar cookies diretamente (Recomendado para Acesso Remoto)"
                              >
                                <Upload className="w-3 h-3 text-slate-500" />
                                <span className="hidden sm:inline">Colar Cookies</span>
                              </button>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>

            {/* Retail Stores Explanation & Optional Toggle */}
            <div className="p-3.5 rounded-xl border border-slate-200 bg-slate-50 text-xs space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-slate-700">
                  <Building2 className="w-4 h-4 text-slate-400" />
                  <span className="font-semibold text-slate-800">
                    Lojas de Retalho Oficial (Preço Fixo não Regateável)
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => setShowRetailStores(!showRetailStores)}
                  className="text-slate-500 hover:text-slate-800 flex items-center gap-1 font-medium text-[11px]"
                >
                  <span>{showRetailStores ? "Ocultar" : "Ver Lojas"}</span>
                  {showRetailStores ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                </button>
              </div>

              <p className="text-[11px] text-slate-500 leading-relaxed">
                As lojas de retalho oficial (<strong>Amazon, Worten, CeX, PCDiga, PcComponentes e GlobalData</strong>) têm preços fixos oficiais sem chat direto. Estão desativadas por padrão para evitar propostas redundantes, mas as suas ofertas permanecem monitorizadas no catálogo.
              </p>

              {showRetailStores && (
                <div className="pt-2 border-t border-slate-200 flex flex-wrap gap-2">
                  {RETAIL_PLATFORMS.map(r => (
                    <div
                      key={r.id}
                      className="px-2 py-1 rounded-md bg-white border border-slate-200 text-[10px] font-medium text-slate-600 flex items-center gap-1.5"
                    >
                      {PLATFORM_LOGOS[r.id] && (
                        <img src={PLATFORM_LOGOS[r.id]} alt={r.name} className="w-3.5 h-3.5 object-contain" />
                      )}
                      <span>{r.name} (Retalho Fixo)</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* TOPIC 2: Order of Pitches / Target Segment */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-bold text-slate-800 uppercase tracking-wider block">
                2. Ordem de Envio (Segmento Alvo)
              </label>
              <span className="text-xs text-slate-500 font-medium">
                {targets.length} portáteis elegíveis na seleção
              </span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
              {[
                { id: "value", label: "Melhor Relação Preço/Specs", desc: "Top pontuação qualidade/preço" },
                { id: "specs", label: "Melhores Specs Primeiro", desc: "Gaming & CPUs/GPUs de topo" },
                { id: "price_asc", label: "Preço Mais Baixo Primeiro", desc: "Oportunidades mais económicas" },
                { id: "all", label: "Todos os Elegíveis", desc: "Ordem natural da seleção" }
              ].map(sec => (
                <button
                  key={sec.id}
                  type="button"
                  onClick={() => setTargetSection(sec.id as any)}
                  className={`p-3 rounded-xl border text-left transition-all ${
                    targetSection === sec.id
                      ? "bg-white border-indigo-600 ring-2 ring-indigo-500/10 shadow-xs"
                      : "bg-white border-slate-200 text-slate-600 hover:border-slate-300 hover:bg-slate-50"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-bold text-slate-900">{sec.label}</span>
                    {targetSection === sec.id && <Check className="w-3.5 h-3.5 text-indigo-600" />}
                  </div>
                  <p className="text-[11px] text-slate-500 line-clamp-1">{sec.desc}</p>
                </button>
              ))}
            </div>
          </div>

          {/* TOPIC 3: Delivery, Payment & Discount Strategy */}
          <div className="space-y-4">
            <label className="text-xs font-bold text-slate-800 uppercase tracking-wider block">
              3. Método de Entrega, Pagamento & Desconto
            </label>

            {/* Delivery & Payment Method Selector */}
            <div className="space-y-2">
              <span className="text-xs font-semibold text-slate-700 block">
                Forma de Pagamento e Entrega na Proposta:
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                {DELIVERY_METHODS.map(m => {
                  const Icon = m.icon
                  const isSelected = deliveryMethod === m.id
                  return (
                    <button
                      key={m.id}
                      type="button"
                      onClick={() => handleSelectDeliveryMethod(m.id as any)}
                      className={`p-3 rounded-xl border text-left transition-all ${
                        isSelected
                          ? "bg-white border-indigo-600 ring-2 ring-indigo-500/10 shadow-xs"
                          : "bg-white border-slate-200 text-slate-600 hover:border-slate-300 hover:bg-slate-50"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-1.5">
                          <Icon className={`w-3.5 h-3.5 ${isSelected ? "text-indigo-600" : "text-slate-400"}`} />
                          <span className="text-xs font-bold text-slate-900">{m.name}</span>
                        </div>
                        {isSelected && <Check className="w-3.5 h-3.5 text-indigo-600 shrink-0" />}
                      </div>
                      <p className="text-[11px] text-slate-500 line-clamp-2 mt-0.5">{m.desc}</p>
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Pitch Tone & Strategy Selector (Harmonizes with Delivery Method!) */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-700 block">
                  Tom & Abordagem da Proposta:
                </span>
                <span className="text-[11px] text-slate-400">
                  Adapta-se automaticamente à forma de entrega selecionada
                </span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {PITCH_TONES.map(t => {
                  const isSelected = pitchTone === t.id
                  return (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => handleSelectPitchTone(t.id)}
                      className={`p-2.5 rounded-xl border text-left transition-all ${
                        isSelected
                          ? "bg-white border-indigo-600 ring-2 ring-indigo-500/10 shadow-xs"
                          : "bg-white border-slate-200 text-slate-600 hover:border-slate-300 hover:bg-slate-50"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-0.5">
                        <span className="text-xs font-bold text-slate-900">{t.label}</span>
                        {isSelected && <Check className="w-3 h-3 text-indigo-600 shrink-0" />}
                      </div>
                      <p className="text-[10px] text-slate-500 line-clamp-1">{t.desc}</p>
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Discount Slider */}
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-xs font-semibold text-slate-700">Desconto Pretendido na Oferta:</span>
                <span className="text-xs font-bold text-indigo-600">-{discountPct}%</span>
              </div>
              <input
                type="range"
                min="5"
                max="35"
                step="5"
                value={discountPct}
                onChange={(e) => setDiscountPct(Number(e.target.value))}
                className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
              />
              <div className="flex justify-between text-[10px] text-slate-400">
                <span>-5% (Oferta Suave)</span>
                <span>-20% (Padrão Recomendado)</span>
                <span>-35% (Oferta Agressiva)</span>
              </div>
            </div>

            {/* Visible & Editable Optimized Pitch Template Card */}
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-indigo-600 shrink-0" />
                  <span className="text-xs font-bold text-slate-900">
                    Texto Otimizado da Proposta:
                  </span>
                  {isCustomized ? (
                    <span className="text-[10px] bg-amber-50 text-amber-700 border border-amber-200 px-2 py-0.5 rounded font-medium">
                      Personalizado (Editado)
                    </span>
                  ) : (
                    <span className="text-[10px] bg-indigo-50 text-indigo-700 border border-indigo-200 px-2 py-0.5 rounded font-medium flex items-center gap-1">
                      <Check className="w-3 h-3 text-indigo-600" />
                      Otimizado: {deliveryMethod === "auto" ? "Auto" : deliveryMethod === "ctt_cobranca" ? "CTT Cobrança" : "Presencial"} + {PITCH_TONES.find(t => t.id === pitchTone)?.label}
                    </span>
                  )}
                </div>

                {isCustomized && (
                  <button
                    type="button"
                    onClick={handleResetToOptimized}
                    className="text-[11px] text-indigo-600 hover:text-indigo-800 font-medium flex items-center gap-1 self-start sm:self-auto"
                  >
                    <RefreshCw className="w-3 h-3" />
                    <span>Repor Padrão Otimizado</span>
                  </button>
                )}
              </div>

              {/* Full Editable Template Textarea */}
              <div className="relative">
                <textarea
                  rows={3}
                  value={templateText}
                  onChange={handleTemplateChange}
                  className="w-full p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-1 focus:ring-indigo-500 font-sans leading-relaxed"
                  placeholder="Escreva ou edite o template da proposta..."
                />
              </div>

              {/* Dynamic Variable Chips */}
              <div className="flex flex-wrap items-center gap-1.5 pt-1 border-t border-slate-100 text-[11px]">
                <span className="text-slate-400 font-medium mr-1">Tags dinâmicas (clique para inserir):</span>
                {[
                  { tag: "{title}", label: "Título do Portátil" },
                  { tag: "{offer_price}", label: "Preço c/ Desconto (€)" },
                  { tag: "{price}", label: "Preço Anunciado (€)" },
                  { tag: "{discount_pct}", label: "% Desconto" },
                  { tag: "{location}", label: "Localização" }
                ].map(v => (
                  <button
                    key={v.tag}
                    type="button"
                    onClick={() => handleInsertTag(v.tag)}
                    className="px-2 py-0.5 rounded bg-slate-100 hover:bg-indigo-50 hover:text-indigo-700 text-slate-700 border border-slate-200 font-mono text-[10px] transition-colors"
                    title={`Inserir ${v.label}`}
                  >
                    {v.tag}
                  </button>
                ))}
              </div>
            </div>

            {/* Live Pitch Message Preview (Direct Chat Bubble) */}
            <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs space-y-2">
              <div className="flex items-center justify-between text-xs font-semibold text-slate-700">
                <div className="flex items-center gap-1.5">
                  <MessageSquare className="w-3.5 h-3.5 text-indigo-600" />
                  <span>Pré-visualização da Mensagem (O que o vendedor recebe):</span>
                </div>
                <span className="text-[10px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-medium border border-slate-200">
                  {deliveryMethod === "auto" ? "Adaptada por Localização" : deliveryMethod === "ctt_cobranca" ? "CTT à Cobrança" : "Presencial em Mãos"}
                </span>
              </div>
              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-800 leading-relaxed font-sans whitespace-pre-wrap select-all">
                {resolvedSampleMessage || sampleMessage || "A gerar mensagem da proposta..."}
              </div>
              <div className="flex flex-col sm:flex-row sm:items-center justify-between text-[11px] text-slate-400 gap-1">
                <span>O título do portátil e o valor oferecido são preenchidos automaticamente com o desconto escolhido (-{discountPct}%).</span>
                {targets.length > 0 && (
                  <span className="text-slate-500 font-medium shrink-0">
                    Exemplo real: {targets[0].title.slice(0, 30)}...
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="p-3.5 border-t border-slate-200 bg-white shrink-0 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="text-xs text-slate-500 font-medium">
            Pronto para enviar propostas para{" "}
            <strong className="text-slate-900">{targets.length} portáteis</strong> da seleção.
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto">
            <Button
              variant="outline"
              size="sm"
              onClick={onClose}
              disabled={dispatching}
              className="text-xs border-slate-200 flex-1 sm:flex-none"
            >
              Cancelar
            </Button>

            <Button
              size="sm"
              onClick={handleDispatchPitches}
              disabled={dispatching || !canDispatch || targets.length === 0}
              className={`text-xs h-9 px-4 font-semibold shadow-xs flex items-center justify-center gap-1.5 flex-1 sm:flex-none transition-all ${
                !canDispatch
                  ? "bg-slate-200 text-slate-500 cursor-not-allowed hover:bg-slate-200"
                  : "bg-indigo-600 hover:bg-indigo-700 text-white"
              }`}
              title={
                !canDispatch
                  ? `Sessão necessária em ${missingSessionPlatforms.join(", ")} para enviar`
                  : `Disparar propostas para todos os ${targets.length} portáteis`
              }
            >
              {dispatching ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>A Lançar {targets.length} Propostas...</span>
                </>
              ) : !canDispatch ? (
                <>
                  <ShieldAlert className="w-3.5 h-3.5 text-amber-600" />
                  <span>Sessão Necessária ({missingSessionPlatforms.join(", ")})</span>
                </>
              ) : (
                <>
                  <Send className="w-3.5 h-3.5" />
                  <span>Lançar {targets.length} Propostas a Toda a Seleção</span>
                </>
              )}
            </Button>
          </div>
        </div>
      </div>

      {/* Remote Cookie Import Sub-Modal */}
      {cookieModalPlatform && (
        <div className="fixed inset-0 z-60 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full border border-slate-200 shadow-2xl p-5 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <Key className="w-4 h-4 text-indigo-600" />
                <h4 className="text-sm font-bold text-slate-900">
                  Importar Cookies para {cookieModalPlatform.toUpperCase()}
                </h4>
              </div>
              <button
                type="button"
                onClick={() => setCookieModalPlatform(null)}
                className="p-1 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-700"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="text-xs text-slate-600 space-y-2">
              <p>
                <strong>Ideal para Acesso Remoto:</strong> Se estiver a aceder remotamente sem ecrã gráfico na máquina host, pode exportar a sua sessão do navegador local e colar aqui.
              </p>
              <p className="text-[11px] text-slate-500 bg-slate-50 p-2 rounded-lg border border-slate-200">
                Formatos suportados: JSON de extensões como <em>Cookie-Editor</em>, JSON do Playwright <em>storage_state</em>, ou texto <code>document.cookie</code>.
              </p>
            </div>

            <textarea
              value={cookieInput}
              onChange={e => setCookieInput(e.target.value)}
              placeholder="Cole aqui o JSON de cookies ou o valor de document.cookie..."
              rows={5}
              className="w-full text-xs font-mono p-3 rounded-xl border border-slate-200 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
            />

            {cookieError && (
              <div className="text-xs text-rose-600 bg-rose-50 border border-rose-200 p-2.5 rounded-lg flex items-center gap-1.5">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{cookieError}</span>
              </div>
            )}

            <div className="flex items-center justify-end gap-2 pt-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => setCookieModalPlatform(null)}
                className="text-xs"
              >
                Cancelar
              </Button>
              <Button
                size="sm"
                onClick={handleImportCookies}
                disabled={cookieSaving || !cookieInput.trim()}
                className="text-xs bg-indigo-600 hover:bg-indigo-700 text-white"
              >
                {cookieSaving ? "A Guardar..." : "Guardar & Certificar Sessão"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </Dialog>
  )
}
