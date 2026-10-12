# Project: OLX Laptop Hunter

## Overview
Desktop application for automated OLX laptop deal scraping, hardware benchmarking, price estimation, discount negotiations, and OLX chat synchronization.

## Architecture & Tech Stack
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS, Lucide React icons.
- **Desktop Runtime**: Electron (`electron/main.cjs`).
- **Backend**: FastAPI (`backend/main.py`), SQLite (`backend/database.py`), Python 3 virtual environment (`.venv`).
- **Scraper Engine**: Playwright (`backend/laptop_scraper.py`) and BeautifulSoup4.
- **Process Orchestration**: PM2 (`ecosystem.config.cjs`) / Node script (`scripts/start-backend.cjs`).

## Non-Negotiable Rules & Constraints
- **Strictly No Emojis**: Never use emojis anywhere in the UI (buttons, cards, chips, badges, toasts, headers, text). Always use clean Lucide SVG icons.
- **Theme**: Crisp White/Light theme with slate/neutral accents (`bg-slate-50` canvas, `bg-white` cards, `border-slate-200`, `text-slate-900`).
- **Design Utility**: Keep the interface clean, high-utility, and focused on core deal hunting and analysis.
