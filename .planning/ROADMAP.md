# Project Roadmap: OLX Laptop Hunter

## Phase 1: Core Scraping & Ingestion
- [x] OLX scraper script using Playwright & BeautifulSoup4 (`backend/laptop_scraper.py`).
- [x] Hardware spec parser (CPU, GPU, RAM, Storage, Screen, Battery).
- [x] Database schema & storage in SQLite (`backend/database.py`).
- [x] Scraper background logging and log streaming.

## Phase 2: Hardware Benchmark & Pricing Analytics
- [x] Hardware comparator & benchmark scoring (`backend/hardware_comparator.py`).
- [x] Geo utilities for seller distance calculation (`backend/geo_utils.py`).
- [x] Deal rating and undervalue detection engine.

## Phase 3: Desktop UI & Management
- [x] React 19 + Vite dashboard with filter bars, table, and detail modals.
- [x] Electron desktop wrapper with IPC communication.
- [x] Strict Lucide icons & White/Light theme enforcement.
- [ ] Integration audit of negotiations view and live scraper logs modal.

## Phase 4: Automated Negotiation Daemon & Outreach
- [x] Negotiation strategy daemon (`backend/negotiation_daemon.py`, `backend/negotiation.py`).
- [ ] Live OLX chat sync & automated offer sending verification.
