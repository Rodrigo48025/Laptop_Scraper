# Project Session Memory: OLX Laptop Hunter

## 1. Project Overview & Architecture
- **Application**: OLX Laptop Hunter Desktop App.
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS, Lucide React icons, Electron.
- **Backend**: FastAPI (`backend/main.py`), SQLite (`backend/database.py`), Playwright & BeautifulSoup4 scrapers.
- **Runtime / Orchestration**: Electron wrapper (`electron/main.cjs`), PM2 / scripts (`scripts/start-backend.cjs`, `ecosystem.config.cjs`).

## 2. Core Constraints & Styling Rules
- **No Emojis**: Strictly prohibited in all UI elements, headings, chips, alerts, and toasts. Use Lucide SVG icons exclusively.
- **Theme**: Crisp White/Light theme with slate/neutral accents (`bg-slate-50` canvas, `bg-white` cards, `border-slate-200`, `text-slate-900`).
- **Design Philosophy**: High-utility, decluttered, clean engineering feel.

## 3. Current Session Context & Progress
- **Context Preservation Setup**: Configured automatic rule- and skill-based continuous memory (`AGENTS.md`, `.agents/rules/session_memory.md`, and `SESSION_MEMORY.md`) to prevent context drops during model switches or new chat sessions.
- **Active Workspace Documents**:
  - `backend/requirements.txt`
  - `backend/main.py`
  - `backend/database.py`
  - `backend/geo_utils.py`
  - `src/App.tsx`
  - `src/components/SettingsView.tsx`
  - `src/components/ScraperLogsModal.tsx`
  - `ecosystem.config.cjs`

## 4. Key Decisions & Roadmap
- Discarded external MCP memory servers in favor of deterministic workspace rules and skills for zero-latency, 100% reliable cross-session memory.
- Next active tasks: Reviewing scraper pipelines, database endpoints, and UI components as directed by the user.
