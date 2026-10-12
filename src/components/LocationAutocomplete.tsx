import React, { useState, useRef, useEffect, useMemo } from "react"
import { Input } from "@/components/ui/input"
import { PORTUGUESE_LOCATIONS_DATA, PortugueseLocation } from "@/data/portugueseLocations"
import { MapPin, Building2, Search, X, Check, Compass } from "lucide-react"

interface LocationAutocompleteProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  className?: string
}

function normalizeStr(str: string): string {
  return str
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
}

export function LocationAutocomplete({
  value,
  onChange,
  placeholder = "Pesquise por concelho, cidade ou área metropolitana...",
  className = ""
}: LocationAutocompleteProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [highlightedIndex, setHighlightedIndex] = useState<number>(-1)
  const containerRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLDivElement>(null)

  // Filter locations dynamically as the user types
  const filteredLocations = useMemo(() => {
    const q = normalizeStr(value)
    if (!q) {
      // If empty, return metropolitan areas first followed by main hubs
      return PORTUGUESE_LOCATIONS_DATA.slice(0, 12)
    }

    return PORTUGUESE_LOCATIONS_DATA.filter((loc) => {
      const nameNorm = normalizeStr(loc.name)
      const metroNorm = normalizeStr(loc.metroArea)
      const descNorm = loc.description ? normalizeStr(loc.description) : ""
      const aliasesNorm = (loc.aliases || []).map(normalizeStr)

      return (
        nameNorm.includes(q) ||
        metroNorm.includes(q) ||
        descNorm.includes(q) ||
        aliasesNorm.some((a) => a.includes(q))
      )
    })
  }, [value])

  // Reset highlighted index when filter results change
  useEffect(() => {
    setHighlightedIndex(-1)
  }, [filteredLocations])

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  // Auto scroll highlighted item into view in the list
  useEffect(() => {
    if (highlightedIndex >= 0 && listRef.current) {
      const highlightedEl = listRef.current.children[highlightedIndex] as HTMLElement
      if (highlightedEl) {
        highlightedEl.scrollIntoView({ block: "nearest" })
      }
    }
  }, [highlightedIndex])

  const handleSelect = (loc: PortugueseLocation) => {
    onChange(loc.name)
    setIsOpen(false)
    inputRef.current?.blur()
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!isOpen) {
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        setIsOpen(true)
        return
      }
    }

    if (e.key === "ArrowDown") {
      e.preventDefault()
      setHighlightedIndex((prev) =>
        prev < filteredLocations.length - 1 ? prev + 1 : 0
      )
    } else if (e.key === "ArrowUp") {
      e.preventDefault()
      setHighlightedIndex((prev) =>
        prev > 0 ? prev - 1 : filteredLocations.length - 1
      )
    } else if (e.key === "Enter") {
      if (isOpen && highlightedIndex >= 0 && highlightedIndex < filteredLocations.length) {
        e.preventDefault()
        handleSelect(filteredLocations[highlightedIndex])
      }
    } else if (e.key === "Escape") {
      setIsOpen(false)
    }
  }

  return (
    <div ref={containerRef} className="relative w-full">
      <div className="relative">
        <Input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => {
            onChange(e.target.value)
            setIsOpen(true)
          }}
          onFocus={() => setIsOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className={`bg-white border-slate-200 text-slate-900 text-xs h-9 pl-8 pr-8 focus:bg-white focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 ${className}`}
        />
        <Compass className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />

        {value && (
          <button
            type="button"
            onClick={() => {
              onChange("")
              inputRef.current?.focus()
            }}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors p-0.5"
            title="Limpar localização"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Autocomplete Dropdown */}
      {isOpen && (
        <div
          ref={listRef}
          className="absolute z-50 left-0 right-0 mt-1 max-h-64 overflow-y-auto rounded-xl border border-slate-200 bg-white p-1.5 shadow-lg backdrop-blur-md duration-150 animate-in fade-in-0 zoom-in-98"
        >
          {filteredLocations.length === 0 ? (
            <div className="p-3 text-center text-xs text-slate-500">
              <p className="font-medium">Nenhum concelho pré-configurado encontrado.</p>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Pode manter o texto digitado como localização livre.
              </p>
            </div>
          ) : (
            <>
              <div className="px-2 py-1 text-[10px] font-semibold text-slate-400 uppercase tracking-wider flex items-center justify-between">
                <span>Sugestões de Áreas Metropolitanas & Concelhos</span>
                <span>{filteredLocations.length} opções</span>
              </div>

              {filteredLocations.map((loc, idx) => {
                const isSelected = normalizeStr(value) === normalizeStr(loc.name)
                const isHighlighted = idx === highlightedIndex

                return (
                  <button
                    key={`${loc.name}-${idx}`}
                    type="button"
                    onMouseEnter={() => setHighlightedIndex(idx)}
                    onClick={() => handleSelect(loc)}
                    className={`w-full text-left px-2.5 py-2 rounded-lg text-xs transition-colors flex items-start justify-between gap-2 ${
                      isHighlighted
                        ? "bg-indigo-50/80 text-indigo-950"
                        : isSelected
                        ? "bg-slate-50 text-slate-900 font-semibold"
                        : "text-slate-700 hover:bg-slate-50"
                    }`}
                  >
                    <div className="flex items-start gap-2 min-w-0">
                      {loc.isMetro ? (
                        <Building2
                          className={`w-3.5 h-3.5 mt-0.5 shrink-0 ${
                            isHighlighted ? "text-indigo-600" : "text-indigo-500"
                          }`}
                        />
                      ) : (
                        <MapPin
                          className={`w-3.5 h-3.5 mt-0.5 shrink-0 ${
                            isHighlighted ? "text-indigo-600" : "text-slate-400"
                          }`}
                        />
                      )}

                      <div className="min-w-0">
                        <div className="flex items-center gap-1.5">
                          <span className="font-bold truncate">{loc.name}</span>
                          {loc.isMetro && (
                            <span className="text-[9px] uppercase font-bold tracking-wider px-1.5 py-0.2 rounded bg-indigo-100 text-indigo-700">
                              Área Metro
                            </span>
                          )}
                        </div>

                        {loc.description && (
                          <p className="text-[11px] text-slate-500 truncate mt-0.5">
                            {loc.description}
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0 pt-0.5">
                      <span className="text-[10px] text-slate-400 hidden sm:inline">
                        {loc.metroArea}
                      </span>
                      {isSelected && <Check className="w-3.5 h-3.5 text-indigo-600" />}
                    </div>
                  </button>
                )
              })}
            </>
          )}
        </div>
      )}
    </div>
  )
}
