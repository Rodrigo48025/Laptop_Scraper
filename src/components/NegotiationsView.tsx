import React, { useState, useEffect } from "react"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  MessageSquare,
  Copy,
  Check,
  ExternalLink,
  RefreshCw,
  Clock,
  TrendingDown,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Laptop
} from "lucide-react"
import { useLanguage } from "@/i18n/LanguageContext"

export function NegotiationsView() {
  const { t } = useLanguage()
  const [negotiations, setNegotiations] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [copiedId, setCopiedId] = useState<number | null>(null)

  useEffect(() => {
    fetchNegotiations()
  }, [])

  const fetchNegotiations = async () => {
    setLoading(true)
    try {
      const res = await fetch("/api/daemons/status")
      if (res.ok) {
        const data = await res.json()
        setNegotiations(data.recent_dispatches || [])
      }
    } catch (e) {
      console.error("Failed to load negotiations:", e)
    } finally {
      setLoading(false)
    }
  }

  const handleCopy = (id: number, text: string) => {
    navigator.clipboard.writeText(text)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2500)
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "agreed":
        return (
          <Badge className="bg-emerald-50 text-emerald-700 border-emerald-200 border flex items-center gap-1 font-medium">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
            {t("negotiations.badge.agreed")}
          </Badge>
        )
      case "declined":
        return (
          <Badge className="bg-red-50 text-red-700 border-red-200 border flex items-center gap-1 font-medium">
            <XCircle className="w-3 h-3 text-red-600" />
            {t("negotiations.badge.declined")}
          </Badge>
        )
      case "countered":
        return (
          <Badge className="bg-amber-50 text-amber-700 border-amber-200 border flex items-center gap-1 font-medium">
            <TrendingDown className="w-3 h-3 text-amber-600" />
            {t("negotiations.badge.countered")}
          </Badge>
        )
      default:
        return (
          <Badge className="bg-slate-100 text-slate-700 border-slate-200 border flex items-center gap-1 font-medium">
            <Clock className="w-3 h-3 text-slate-500" />
            {t("negotiations.badge.sent")}
          </Badge>
        )
    }
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-white p-6 rounded-xl border border-slate-200 shadow-xs">
        <div>
          <div className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-indigo-600" />
            <h2 className="text-xl font-bold text-slate-900 tracking-tight">{t("negotiations.title")}</h2>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            {t("negotiations.subtitle")}
          </p>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={fetchNegotiations}
          disabled={loading}
          className="border-slate-200 text-slate-700 hover:bg-slate-50 flex items-center gap-2"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          {t("negotiations.refreshBtn")}
        </Button>
      </div>

      {negotiations.length === 0 ? (
        <Card className="bg-white border-slate-200 p-12 text-center shadow-xs">
          <div className="w-12 h-12 rounded-full bg-slate-100 text-slate-400 mx-auto flex items-center justify-center mb-3">
            <MessageSquare className="w-6 h-6" />
          </div>
          <h3 className="text-sm font-semibold text-slate-800">{t("negotiations.emptyTitle")}</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
            {t("negotiations.emptyDesc")}
          </p>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {negotiations.map((neg) => {
            const origPrice = parseFloat(neg.original_price || 0)
            const offerPrice = parseFloat(neg.offered_price || 0)
            const discountEur = origPrice - offerPrice

            return (
              <Card key={neg.id} className="bg-white border-slate-200 shadow-xs p-5">
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
                  <div>
                    <h3 className="font-semibold text-sm text-slate-900">{neg.title || "Portátil"}</h3>
                    <p className="text-xs text-slate-500 mt-0.5">{neg.location || "Portugal"}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    {getStatusBadge(neg.status)}
                    {neg.url && (
                      <a
                        href={neg.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-slate-400 hover:text-indigo-600 transition-colors p-1"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </a>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 py-3 text-xs border-b border-slate-100">
                  <div>
                    <span className="text-slate-500 block">{t("catalog.listedPrice")}</span>
                    <span className="font-semibold text-slate-900">{origPrice.toFixed(0)} €</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">{t("negotiations.offeredValue")}</span>
                    <span className="font-bold text-indigo-600">{offerPrice.toFixed(0)} €</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">{t("negotiations.savings")}</span>
                    <span className="font-semibold text-emerald-600">-{discountEur.toFixed(0)} € ({neg.discount_percentage || 20}%)</span>
                  </div>
                </div>

                {neg.pitch_message && (
                  <div className="mt-3 bg-slate-50 p-3 rounded-lg border border-slate-100 flex items-start justify-between gap-3">
                    <p className="text-xs text-slate-700 italic leading-relaxed">
                      "{neg.pitch_message}"
                    </p>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleCopy(neg.id, neg.pitch_message)}
                      className="h-7 px-2 text-slate-500 hover:text-indigo-600 shrink-0"
                    >
                      {copiedId === neg.id ? (
                        <Check className="w-3.5 h-3.5 text-emerald-600" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                    </Button>
                  </div>
                )}
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
