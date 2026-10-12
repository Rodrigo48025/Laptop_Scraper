import * as React from "react"
import { cn } from "@/lib/utils"
import { X } from "lucide-react"

interface DialogProps {
  open: boolean
  onClose: () => void
  children: React.ReactNode
  title?: string
  description?: string
  maxWidth?: string
  noBodyScroll?: boolean
  className?: string
}

export function Dialog({
  open,
  onClose,
  children,
  title,
  description,
  maxWidth = "max-w-lg",
  noBodyScroll = false,
  className
}: DialogProps) {
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose()
    }
    if (open) {
      document.body.style.overflow = "hidden"
      window.addEventListener("keydown", handleKeyDown)
    } else {
      document.body.style.overflow = "unset"
    }
    return () => {
      document.body.style.overflow = "unset"
      window.removeEventListener("keydown", handleKeyDown)
    }
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 overflow-hidden">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs transition-opacity"
        onClick={onClose}
      />
      {/* Content Card */}
      <div
        className={cn(
          "relative z-50 w-full rounded-2xl border border-slate-200 bg-white p-6 shadow-xl duration-200 animate-in fade-in-0 zoom-in-95 my-auto max-h-[92vh] flex flex-col",
          maxWidth,
          className
        )}
      >
        <div className="flex items-start justify-between pb-3 border-b border-slate-100 shrink-0">
          <div className="space-y-1 pr-4">
            {title && <h2 className="text-base font-bold text-slate-900 tracking-tight leading-snug">{title}</h2>}
            {description && <p className="text-xs text-slate-500 leading-normal">{description}</p>}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors shrink-0"
            title="Fechar"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        {noBodyScroll ? (
          <div className="flex-1 min-h-0 flex flex-col">{children}</div>
        ) : (
          <div className="py-3 flex-1 min-h-0 overflow-y-auto">{children}</div>
        )}
      </div>
    </div>
  )
}
