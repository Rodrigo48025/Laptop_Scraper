import React, { Component, ErrorInfo, ReactNode } from "react"
import { AlertCircle, RefreshCw, Laptop } from "lucide-react"

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null
  }

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught runtime error caught by ErrorBoundary:", error, errorInfo)
  }

  private handleReload = () => {
    window.location.reload()
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6 font-sans">
          <div className="max-w-md w-full bg-white rounded-2xl border border-slate-200/90 shadow-sm p-6 text-center">
            <div className="w-12 h-12 rounded-xl bg-red-50 border border-red-200 flex items-center justify-center mx-auto mb-4">
              <AlertCircle className="w-6 h-6 text-red-600" />
            </div>

            <h2 className="text-base font-bold text-slate-900 mb-1.5">
              Ocorreu um erro na interface
            </h2>
            <p className="text-xs text-slate-500 mb-4 leading-relaxed">
              A aplicação encontrou um problema inesperado ao renderizar este ecrã.
            </p>

            {this.state.error?.message && (
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-left mb-5">
                <span className="text-[10px] font-mono font-semibold uppercase text-slate-400 block mb-1">
                  Detalhe Técnico
                </span>
                <p className="text-xs font-mono text-slate-700 break-words">
                  {this.state.error.message}
                </p>
              </div>
            )}

            <div className="flex items-center justify-center gap-3">
              <button
                type="button"
                onClick={this.handleReload}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg shadow-xs flex items-center gap-2 transition-colors"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Recarregar Aplicação</span>
              </button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
