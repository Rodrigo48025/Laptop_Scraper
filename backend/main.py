"""
backend/main.py - Dedicated FastAPI backend for Laptop Scraper & Deal Hunter Desktop App.
Handles OLX scraping, hardware benchmarks, discount negotiations, and OLX chat sync.
"""

import os
import sys
import json
import time
import asyncio
from datetime import datetime
from collections import deque
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from fastapi import FastAPI, BackgroundTasks, HTTPException, Query, Response, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from link_verifier import verify_listing_active

# Ensure backend root is on sys.path and alias 'src' to backend directory
import types
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
src_module = types.ModuleType("src")
src_module.__path__ = [str(BASE_DIR)]
sys.modules["src"] = src_module

LOG_DIR = BASE_DIR / "data"
LOG_DIR.mkdir(parents=True, exist_ok=True)
SCRAPER_LOG_FILE = LOG_DIR / "scraper.log"
RECENT_LOGS = deque(maxlen=2000)

class AppLogHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            if "/api/health" in msg:
                return
            RECENT_LOGS.append(msg)
            with open(SCRAPER_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except Exception:
            pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("laptop_api")
app_handler = AppLogHandler()
app_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S"))
logging.getLogger().addHandler(app_handler)

from database import (
    init_db,
    reset_database,
    get_connection,
    get_laptops,
    get_laptop_stats,
    update_laptop_contact,
    get_laptop_by_id,
    create_or_update_negotiation,
    apply_negotiation_agreement,
    record_negotiation_response,
    get_negotiations,
    get_pending_negotiations
)
from laptop_scraper import LaptopDealScraper
from hardware_comparator import HardwareComparator, get_hardware_dossier
from negotiation import (
    is_laptop_negotiable,
    calculate_negotiated_offer,
    compose_negotiation_message,
    classify_seller_response,
    process_incoming_responses_queue
)

app = FastAPI(
    title="Laptop Scraper & Deal Hunter API",
    description="Dedicated desktop backend for OLX Laptop Scraping, AI Hardware Benchmarks, and Auto-Negotiation.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup():
    init_db()
    try:
        if not daemon_state["running"]:
            daemon_state["running"] = True
            daemon_state["started_at"] = time.time()
            daemon_state["task"] = asyncio.create_task(_daemon_loop())
            logger.info("Demon Maestro auto-iniciado no arranque da API.")
    except Exception as e:
        logger.warning(f"Nao foi possivel auto-iniciar o Demon no arranque: {e}")

@app.get("/api/health")
def health():
    return {"status": "ok", "app": "Laptop Scraper Desktop API", "version": "2.0.0"}

# Laptops Endpoints
@app.get("/api/laptops")
def fetch_laptops(
    search: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_ram: Optional[int] = None,
    min_storage: Optional[int] = None,
    gpu_type: Optional[str] = None,
    negotiation_status: Optional[str] = None,
    min_score: Optional[float] = None,
    source: Optional[str] = None,
    condition: Optional[str] = None,
    has_warranty: Optional[bool] = None,
    sort_by: str = "deal_score",
    sort_order: str = "desc",
    limit: int = 100,
    offset: int = 0
):
    return get_laptops(
        search=search,
        min_price=min_price,
        max_price=max_price,
        min_ram=min_ram,
        min_storage=min_storage,
        gpu_type=gpu_type,
        negotiation_status=negotiation_status,
        min_score=min_score,
        source=source,
        condition=condition,
        has_warranty=has_warranty,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset
    )

@app.get("/api/laptops/stats")
def fetch_laptop_stats():
    return get_laptop_stats()

@app.get("/api/laptops/verify-stream")
async def verify_laptops_stream(
    request: Request,
    limit: int = Query(250, ge=1, le=1000),
    source: Optional[str] = Query(None),
    query: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None)
):
    """
    Live streaming link verification for laptops in the catalog.
    Verifies each listing URL concurrently, deletes dead/expired listings from SQLite,
    and streams real-time progress events via Server-Sent Events (SSE).
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    conditions = []
    params = []
    
    if source and source.lower() != "all":
        conditions.append("LOWER(source) = ?")
        params.append(source.lower())
    if min_price is not None:
        conditions.append("price >= ?")
        params.append(min_price)
    if max_price is not None:
        conditions.append("price <= ?")
        params.append(max_price)
    if query and query.strip():
        conditions.append("(LOWER(title) LIKE ? OR LOWER(description) LIKE ?)")
        q_wild = f"%{query.strip().lower()}%"
        params.extend([q_wild, q_wild])
        
    where_sql = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    cursor.execute(f"SELECT id, url, title, source, price FROM laptops {where_sql} ORDER BY id DESC LIMIT ?", params + [limit])
    candidates = [dict(r) for r in cursor.fetchall()]
    conn.close()

    total_candidates = len(candidates)
    
    async def event_generator():
        start_event = {
            "type": "start",
            "total": total_candidates,
            "checked": 0,
            "removed_count": 0,
            "active_count": 0
        }
        yield f"data: {json.dumps(start_event)}\n\n"
        
        if total_candidates == 0:
            done_event = {
                "type": "complete",
                "total": 0,
                "checked": 0,
                "removed_count": 0,
                "active_count": 0
            }
            yield f"data: {json.dumps(done_event)}\n\n"
            return
            
        loop = asyncio.get_running_loop()
        sem = asyncio.Semaphore(15)  # 15 concurrent workers
        
        checked_count = 0
        removed_count = 0
        
        async def check_one(laptop_item):
            async with sem:
                is_active, reason = await loop.run_in_executor(
                    None,
                    verify_listing_active,
                    laptop_item.get("url", ""),
                    laptop_item.get("source", "")
                )
                return laptop_item, is_active, reason

        tasks = [asyncio.create_task(check_one(item)) for item in candidates]
        
        try:
            for fut in asyncio.as_completed(tasks):
                if await request.is_disconnected():
                    logger.info("Client disconnected from /api/laptops/verify-stream, cancelling tasks")
                    for t in tasks:
                        t.cancel()
                    break
                    
                laptop_item, is_active, reason = await fut
                checked_count += 1
                
                if not is_active:
                    removed_count += 1
                    try:
                        c_del = get_connection()
                        with c_del:
                            c_del.cursor().execute("DELETE FROM laptops WHERE id = ?", (laptop_item["id"],))
                        c_del.close()
                        logger.info(f"Verified dead link, removed laptop #{laptop_item['id']} ({reason}): {laptop_item.get('title')}")
                    except Exception as err:
                        logger.warning(f"Failed to delete laptop #{laptop_item['id']}: {err}")
                        
                    event = {
                        "type": "item",
                        "id": laptop_item["id"],
                        "title": laptop_item["title"],
                        "source": laptop_item["source"],
                        "status": "removed",
                        "reason": reason,
                        "checked": checked_count,
                        "total": total_candidates,
                        "removed_count": removed_count,
                        "active_count": checked_count - removed_count
                    }
                    yield f"data: {json.dumps(event)}\n\n"
                else:
                    event = {
                        "type": "item",
                        "id": laptop_item["id"],
                        "title": laptop_item["title"],
                        "source": laptop_item["source"],
                        "status": "active",
                        "checked": checked_count,
                        "total": total_candidates,
                        "removed_count": removed_count,
                        "active_count": checked_count - removed_count
                    }
                    yield f"data: {json.dumps(event)}\n\n"
        except asyncio.CancelledError:
            pass
            
        done_event = {
            "type": "complete",
            "total": total_candidates,
            "checked": checked_count,
            "removed_count": removed_count,
            "active_count": checked_count - removed_count
        }
        yield f"data: {json.dumps(done_event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/api/laptops/{laptop_id}")
def fetch_laptop_detail(laptop_id: int):
    laptop = get_laptop_by_id(laptop_id)
    if not laptop:
        raise HTTPException(status_code=404, detail="Laptop not found")
    return laptop

@app.delete("/api/laptops/{laptop_id}")
def delete_laptop_endpoint(laptop_id: int):
    conn = get_connection()
    with conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM laptops WHERE id = ?", (laptop_id,))
        deleted = cursor.rowcount > 0
    conn.close()
    if not deleted:
        raise HTTPException(status_code=404, detail="Laptop not found")
    return {"status": "deleted", "id": laptop_id}



@app.post("/api/laptops/rescore")
def rescore_all_laptops():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM laptops")
    rows = [dict(r) for r in cursor.fetchall()]
    comparator = HardwareComparator()
    with conn:
        for r in rows:
            dossier = comparator.get_laptop_hardware_dossier(r)
            cursor.execute("""
                UPDATE laptops SET 
                    spec_score = ?, value_score = ?, deal_score = ?,
                    monthly_cost_eur = ?, power_idle_watts = ?, power_peak_watts = ?
                WHERE id = ?
            """, (
                dossier.get("spec_score"), dossier.get("value_score"), dossier.get("deal_score"),
                dossier.get("monthly_cost_eur"), dossier.get("power_idle_watts"), dossier.get("power_peak_watts"),
                r["id"]
            ))
    conn.close()
    return {"status": "rescored", "total": len(rows)}

# Scraping
class ScrapeRequest(BaseModel):
    query: str = "portatil"
    min_price: float = 300.0
    max_price: float = 800.0
    sources: Optional[List[str]] = None
    headless: bool = True

current_scraper_instance: Optional[Any] = None
current_scrape_task: Optional[asyncio.Task] = None
daemon_scraper_instance: Optional[Any] = None

@app.post("/api/laptops/scrape")
async def trigger_laptop_scrape(req: ScrapeRequest):
    global current_scraper_instance, current_scrape_task
    # Prevent duplicated concurrent scrape jobs that waste CPU and lock SQLite
    if current_scrape_task and not current_scrape_task.done():
        logger.info("Extração de ofertas já em execução. Ignorando disparo duplicado.")
        return {
            "status": "already_running",
            "message": "A extração de ofertas já está a decorrer em segundo plano.",
            "query": req.query,
            "min_price": req.min_price,
            "max_price": req.max_price
        }

    scraper = LaptopDealScraper(headless=req.headless)
    current_scraper_instance = scraper

    async def _async_scrape_runner():
        try:
            await scraper.run_scrape_job(
                min_price=req.min_price,
                max_price=req.max_price,
                search=req.query,
                sources=req.sources
            )
        except asyncio.CancelledError:
            logger.info("Scrape job cancelado pelo utilizador.")
        except Exception as e:
            logger.error(f"Erro na execução do scrape job: {e}")

    current_scrape_task = asyncio.create_task(_async_scrape_runner())
    return {
        "status": "started",
        "query": req.query,
        "min_price": req.min_price,
        "max_price": req.max_price,
        "sources": req.sources or ["olx", "facebook", "amazon", "worten", "cex", "pcdiga", "pccomponentes", "globaldata"]
    }

# Contact & Negotiation
class LaptopContactUpdateRequest(BaseModel):
    contact_status: str
    contact_notes: Optional[str] = None

@app.patch("/api/laptops/{laptop_id}/contact")
def update_laptop_contact_endpoint(laptop_id: int, req: LaptopContactUpdateRequest):
    success = update_laptop_contact(laptop_id, req.contact_status, req.contact_notes)
    if not success:
        raise HTTPException(status_code=404, detail="Laptop not found")
    return {"status": "ok", "id": laptop_id, "contact_status": req.contact_status}

class LaptopNegotiateRequest(BaseModel):
    discount_pct: float = 0.20
    method: str = "dinheiro_imediato"
    custom_message: Optional[str] = None

@app.post("/api/laptops/{laptop_id}/negotiate")
def negotiate_laptop_offer(laptop_id: int, req: LaptopNegotiateRequest):
    laptop = get_laptop_by_id(laptop_id)
    if not laptop:
        raise HTTPException(status_code=404, detail="Laptop not found")

    orig_price = float(laptop.get("original_price") or laptop["price"])
    offer_price = calculate_negotiated_offer(orig_price, discount_pct=req.discount_pct)
    if req.custom_message and req.custom_message.strip():
        offer_msg = req.custom_message.strip()
    else:
        offer_msg = compose_negotiation_message(laptop, offer_price, method=req.method)

    res = create_or_update_negotiation(
        laptop_id=laptop_id,
        offer_price=offer_price,
        original_price=orig_price,
        discount_pct=req.discount_pct * 100.0,
        offer_message=offer_msg
    )

    return {
        "status": "offered",
        "laptop_id": laptop_id,
        "original_price": orig_price,
        "offer_price": offer_price,
        "discount_pct": req.discount_pct * 100.0,
        "discount_eur": orig_price - offer_price,
        "offer_message": offer_msg
    }

class LaptopSellerResponseRequest(BaseModel):
    response_text: str
    agreed: Optional[bool] = None
    counter_price: Optional[float] = None

@app.post("/api/laptops/{laptop_id}/respond")
def record_seller_response_endpoint(laptop_id: int, req: LaptopSellerResponseRequest):
    laptop = get_laptop_by_id(laptop_id)
    if not laptop:
        raise HTTPException(status_code=404, detail="Laptop not found")

    agreed = req.agreed
    counter_p = req.counter_price

    if agreed is None:
        classification = classify_seller_response(req.response_text)
        agreed = classification.get("agreed", False)
        if classification.get("counter_price"):
            counter_p = classification["counter_price"]

    record_negotiation_response(laptop_id, req.response_text, "agreed" if agreed else "countered")
    if agreed:
        apply_negotiation_agreement(laptop_id, counter_p or laptop["price"], f"Accepted: {req.response_text}")

    updated = get_laptop_by_id(laptop_id)
    return {
        "status": "agreed" if agreed else "countered",
        "laptop_id": laptop_id,
        "agreed": agreed,
        "price": updated.get("price")
    }

@app.get("/api/laptops/negotiations")
def list_negotiations_endpoint():
    return {
        "negotiations": get_negotiations(),
        "pending": get_pending_negotiations()
    }

@app.post("/api/laptops/negotiations/check")
def trigger_negotiations_check_cycle():
    processed = process_incoming_responses_queue()
    return {"status": "ok", "processed": processed}

# Daemon State & Control
daemon_state = {
    "running": False,
    "started_at": None,
    "task": None,
    "cycle_count": 0,
    "last_cycle_time": None,
    "last_error": None
}

async def _daemon_loop():
    logger.info("Demon Maestro iniciado: Pesquisa contínua e monitorização de negociações.")
    from negotiation_daemon import run_check_cycle
    from laptop_scraper import LaptopDealScraper
    global daemon_scraper_instance

    while daemon_state["running"]:
        try:
            settings = load_settings()
            min_price = float(settings.get("min_price", 250))
            max_price = float(settings.get("max_price", 750))
            search_query = settings.get("search_query", "portatil")
            sources = settings.get("enabled_sources", ["olx", "facebook", "amazon", "worten", "cex", "pcdiga", "pccomponentes", "globaldata"])

            # 1. Executar ciclo de extração de anúncios
            logger.info(f"Ciclo do Demon: A extrair anúncios de {sources} ({min_price}€ - {max_price}€)...")
            daemon_scraper_instance = LaptopDealScraper(headless=True)
            await daemon_scraper_instance.run_scrape_job(
                min_price=min_price,
                max_price=max_price,
                search=search_query,
                sources=sources
            )

            # 2. Executar ciclo de verificação de mensagens e respostas de negociação
            if not daemon_state["running"]:
                break

            logger.info("Ciclo do Demon: A verificar mensagens e respostas de negociação...")
            processed = await asyncio.to_thread(run_check_cycle)
            daemon_state["cycle_count"] += 1
            daemon_state["last_cycle_time"] = datetime.now().isoformat()
            logger.info(f"Ciclo do Demon concluído com sucesso. Respostas processadas: {processed}. Total ciclos: {daemon_state['cycle_count']}")
        except asyncio.CancelledError:
            logger.info("Ciclo do Demon cancelado pelo utilizador.")
            break
        except Exception as e:
            logger.error(f"Erro no ciclo do Demon: {e}")
            daemon_state["last_error"] = str(e)

        # Intervalo de espera de 300s (5 min), verificando a cada 1s para paragem imediata
        for _ in range(300):
            if not daemon_state["running"]:
                break
            await asyncio.sleep(1)
    logger.info("Demon Maestro terminado.")

@app.get("/api/daemon/status")
async def get_daemon_status():
    uptime = 0
    if daemon_state["running"] and daemon_state["started_at"]:
        uptime = int(time.time() - daemon_state["started_at"])
    return {
        "running": daemon_state["running"],
        "started_at": daemon_state["started_at"],
        "uptime_seconds": uptime,
        "cycle_count": daemon_state["cycle_count"],
        "last_cycle_time": daemon_state["last_cycle_time"],
        "last_error": daemon_state["last_error"]
    }

@app.post("/api/daemon/start")
async def start_daemon():
    if not daemon_state["running"]:
        daemon_state["running"] = True
        daemon_state["started_at"] = time.time()
        daemon_state["task"] = asyncio.create_task(_daemon_loop())
        logger.info("Negotiation Daemon INICIADO pelo utilizador.")
    return await get_daemon_status()

@app.post("/api/daemon/stop")
async def stop_daemon():
    global daemon_scraper_instance, current_scraper_instance, current_scrape_task
    daemon_state["running"] = False
    if daemon_state["task"] and not daemon_state["task"].done():
        daemon_state["task"].cancel()
        daemon_state["task"] = None

    # Abort any in-flight scraper instances and close browsers immediately (<20ms)
    if daemon_scraper_instance:
        await daemon_scraper_instance.abort()
        daemon_scraper_instance = None
    if current_scraper_instance:
        await current_scraper_instance.abort()
        current_scraper_instance = None
    if current_scrape_task and not current_scrape_task.done():
        current_scrape_task.cancel()
        current_scrape_task = None

    logger.info("Negotiation Daemon e processos activos PARADOS instantaneamente pelo utilizador.")
    return await get_daemon_status()

@app.get("/api/logs")
def get_logs_endpoint(limit: int = 150):
    lines = list(RECENT_LOGS)
    if not lines and SCRAPER_LOG_FILE.exists():
        try:
            with open(SCRAPER_LOG_FILE, "r", encoding="utf-8") as f:
                lines = [l.strip() for l in f.readlines() if l.strip()]
        except Exception:
            pass
    if not lines:
        pm2_log = Path("/home/rodrigo_costa/.pm2/logs/laptop-backend-out.log")
        if pm2_log.exists():
            try:
                with open(pm2_log, "r", encoding="utf-8", errors="ignore") as f:
                    lines = [l.strip() for l in f.readlines() if l.strip() and "/api/health" not in l]
            except Exception:
                pass
    return {"logs": lines[-limit:] if limit > 0 else lines}

@app.post("/api/logs/clear")
def clear_logs_endpoint():
    RECENT_LOGS.clear()
    try:
        with open(SCRAPER_LOG_FILE, "w", encoding="utf-8") as f:
            f.truncate(0)
    except Exception:
        pass
    logger.info("Registo de logs limpo pelo utilizador.")
    return {"status": "cleared"}

# Daemon & Automation Endpoints
@app.get("/api/daemons/status")
def get_daemons_status_endpoint():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM laptops WHERE contact_status = 'offered'")
    total_offered = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM laptops WHERE negotiation_status = 'agreed'")
    total_agreed = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM laptops WHERE contact_status IS NULL OR contact_status = 'pending'")
    total_uncontacted = c.fetchone()[0]

    c.execute("""
        SELECT n.*, l.title, l.url, l.location, l.spec_score, l.value_score
        FROM laptop_negotiations n
        JOIN laptops l ON n.laptop_id = l.id
        ORDER BY n.updated_at DESC
        LIMIT 8
    """)
    recent = [dict(r) for r in c.fetchall()]
    conn.close()

    uptime = 0
    if daemon_state["running"] and daemon_state["started_at"]:
        uptime = int(time.time() - daemon_state["started_at"])

    return {
        "daemons": {
            "negotiation_daemon": {
                "running": daemon_state["running"],
                "uptime_seconds": uptime,
                "cycles": daemon_state["cycle_count"]
            }
        },
        "daemon_running": daemon_state["running"],
        "uptime_seconds": uptime,
        "messenger_active": True,
        "scraper_active": True,
        "negotiation_active": True,
        "stats": {
            "total_offered": total_offered,
            "total_agreed": total_agreed,
            "total_uncontacted": total_uncontacted
        },
        "recent_dispatches": recent,
        "profile_exists": True
    }

@app.get("/api/negotiation/auto-messenger/targets")
def get_auto_messenger_targets_endpoint(sort: str = "hardware", limit: int = 10):
    try:
        from tools.auto_messenger import get_top_hardware_targets
        targets = get_top_hardware_targets(sort_by=sort, limit=limit)
    except Exception:
        targets = []
    return {"count": len(targets), "targets": targets}

@app.get("/api/negotiation/auto-messenger/status")
def get_auto_messenger_status_endpoint():
    return {"status": "ready", "profile_exists": True}

# OLX Chats API
@app.get("/api/negotiation/chats")
def list_synced_chats():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.*, l.title as db_laptop_title, l.price as current_db_price, l.spec_score
        FROM olx_conversations c
        LEFT JOIN laptops l ON c.laptop_id = l.id
        ORDER BY c.updated_at DESC
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"conversations": rows}

@app.post("/api/negotiation/chats/sync")
async def trigger_chat_sync(background_tasks: BackgroundTasks):
    try:
        from tools.sync_chats import sync_olx_chats
        background_tasks.add_task(sync_olx_chats, True)
    except Exception as e:
        logger.error(f"Error starting chat sync: {e}")
# User Settings & Constant Preferences
SETTINGS_FILE = BASE_DIR / "data" / "user_settings.json"
DEFAULT_SETTINGS = {
    "min_price": 250,
    "max_price": 750,
    "target_discount_pct": 20,
    "pitch_type": "dinheiro_imediato",
    "custom_pitch_template": "Olá! Tenho interesse no portátil. Consegue fazer por {offer_price}€ com levantamento e pagamento imediato em dinheiro?",
    "enabled_sources": ["olx", "facebook", "amazon", "worten", "cex", "pcdiga", "pccomponentes", "globaldata"],
    "search_query": "portatil",
    "home_location": "Leiria / Marinha Grande",
    "max_distance_km": 60,
    "prefer_local_area": True,
    "prefer_lisbon": False,
    "language": "pt",
    "include_second_hand": True,
    "include_refurbished": True,
    "include_new": True,
    "only_with_warranty": False
}

def load_settings():
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return {**DEFAULT_SETTINGS, **json.load(f)}
        except Exception:
            pass
    return DEFAULT_SETTINGS

@app.get("/api/settings")
def get_user_settings():
    return load_settings()

@app.post("/api/settings")
def save_user_settings(settings: Dict[str, Any]):
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    current = load_settings()
    current.update(settings)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2, ensure_ascii=False)
    return {"status": "saved", "settings": current}

class SystemResetRequest(BaseModel):
    backup: bool = True
    reset_settings: bool = False
    clear_logs: bool = True

@app.post("/api/system/reset")
def system_full_reset(req: Optional[SystemResetRequest] = None):
    """
    Executes a clean full reset of the Laptop Scraper system:
    1. Creates a backup of laptops.db (if backup=True)
    2. Drops all tables and re-initializes clean schema (0 deals)
    3. Clears logs and inbox queue
    4. Optionally resets search and user settings to default
    """
    req = req or SystemResetRequest()
    logger.info("A iniciar Full Reset do sistema Laptop Scraper...")
    
    # 1. Reset database
    db_result = reset_database(backup=req.backup)
    
    # 2. Clear application logs
    if req.clear_logs:
        RECENT_LOGS.clear()
        if SCRAPER_LOG_FILE.exists():
            with open(SCRAPER_LOG_FILE, "w", encoding="utf-8") as f:
                f.write(f"{datetime.now().strftime('%H:%M:%S')} [INFO] laptop_api: Sistema reinicializado com sucesso (0 portáteis).\n")
    
    # 3. Clear negotiation responses inbox queue
    inbox_file = BASE_DIR.parent / "data" / "incoming_negotiation_responses.json"
    if inbox_file.exists():
        with open(inbox_file, "w", encoding="utf-8") as f:
            json.dump([], f)

    # 4. Reset settings if requested
    if req.reset_settings:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_SETTINGS, f, indent=2, ensure_ascii=False)

    logger.info("Full Reset concluído com sucesso!")
    return {
        "status": "success",
        "message": "Full reset concluído com sucesso. Base de dados limpa.",
        "database": db_result,
        "logs_cleared": req.clear_logs,
        "settings_reset": req.reset_settings
    }

@app.get("/api/system/run-tests")
def run_test_suites():
    """
    Executes the TDD test suites (test_pitch_dispatch and test_warranty_condition)
    in an isolated subprocess and returns comprehensive results.
    """
    import subprocess
    import sys
    import shutil
    
    pycache = BASE_DIR / "tests" / "__pycache__"
    if pycache.exists():
        shutil.rmtree(pycache, ignore_errors=True)
        
    tests_dir = BASE_DIR / "tests"
    cmd = [sys.executable, "-B", "-m", "unittest", "discover", "-s", str(tests_dir), "-p", "test_*.py", "-v"]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(BASE_DIR))
    output = (res.stdout or "") + "\n" + (res.stderr or "")
    
    return {
        "success": res.returncode == 0,
        "returncode": res.returncode,
        "output": output
    }

# Playwright Platform Sessions Manager
PROFILE_DIR = BASE_DIR / "data" / "playwright_profile"

PLATFORMS_CONFIG = [
    {
        "id": "olx",
        "name": "OLX Portugal",
        "logo": "/logos/olx.svg",
        "tools_count": 3,
        "description": "Pesquisa Pública + Login para Envio de Propostas/Pitch",
        "requires_auth": True,
        "auth_note": "Login obrigatório apenas para envio de mensagens/propostas",
        "auth_url": "https://login.olx.pt"
    },
    {
        "id": "facebook",
        "name": "Facebook Marketplace",
        "logo": "/logos/facebook.svg",
        "tools_count": 2,
        "description": "Pesquisa Pública + Chat do Marketplace",
        "requires_auth": True,
        "auth_note": "Login obrigatório apenas para envio de mensagens no Marketplace",
        "auth_url": "https://www.facebook.com/login/"
    },
    {
        "id": "amazon",
        "name": "Amazon Prime / ES",
        "logo": "/logos/amazon.svg",
        "tools_count": 2,
        "description": "Catálogo Público Prime & Recondicionados Oficiais",
        "requires_auth": False,
        "auth_note": "Acesso 100% público, sem necessidade de login",
        "auth_url": "https://www.amazon.es"
    },
    {
        "id": "worten",
        "name": "Worten Portugal",
        "logo": "/logos/worten.svg",
        "tools_count": 2,
        "description": "Catálogo Público, Lojas & Worten Outlet",
        "requires_auth": False,
        "auth_note": "Acesso 100% público, sem necessidade de login",
        "auth_url": "https://www.worten.pt"
    },
    {
        "id": "cex",
        "name": "CeX Webuy PT",
        "logo": "/logos/cex.svg",
        "tools_count": 2,
        "description": "Catálogo Público por Graus A/B/C & Garantia CeX",
        "requires_auth": False,
        "auth_note": "Acesso 100% público, sem necessidade de login",
        "auth_url": "https://pt.webuy.com"
    },
    {
        "id": "pcdiga",
        "name": "PCDiga",
        "logo": "/logos/pcdiga.svg",
        "tools_count": 2,
        "description": "Catálogo Público & Promoções Gaming",
        "requires_auth": False,
        "auth_note": "Acesso 100% público, sem necessidade de login",
        "auth_url": "https://www.pcdiga.com"
    },
    {
        "id": "pccomponentes",
        "name": "PcComponentes",
        "logo": "/logos/pccomponentes.svg",
        "tools_count": 2,
        "description": "Catálogo Público Ibérico, Ofertas & Recondicionados",
        "requires_auth": False,
        "auth_note": "Acesso 100% público, sem necessidade de login",
        "auth_url": "https://www.pccomponentes.pt"
    },
    {
        "id": "globaldata",
        "name": "GlobalData PT",
        "logo": "/logos/globaldata.svg",
        "tools_count": 2,
        "description": "Catálogo Público & Hardware Gaming em Stock",
        "requires_auth": False,
        "auth_note": "Acesso 100% público, sem necessidade de login",
        "auth_url": "https://www.globaldata.pt"
    }
]

@app.get("/api/platforms/status")
def get_platform_sessions():
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    
    result = []
    for p in PLATFORMS_CONFIG:
        state_file = PROFILE_DIR / f"storage_state_{p['id']}.json"
        has_session = state_file.exists() and state_file.stat().st_size > 10
        if not has_session and p["requires_auth"]:
            # Check general cookies
            general_state = PROFILE_DIR / "storage_state.json"
            if general_state.exists():
                try:
                    with open(general_state, "r") as f:
                        data = json.load(f)
                        domains = [c.get("domain", "") for c in data.get("cookies", [])]
                        if any(p["id"] in d for d in domains):
                            has_session = True
                except Exception:
                    pass

        session_status = "Sessão Ativa" if has_session else ("Não Conectado" if p["requires_auth"] else "Acesso Aberto")
        result.append({
            **p,
            "profile_active": has_session,
            "session_status": session_status,
        })
    return {"platforms": result, "profile_dir": str(PROFILE_DIR)}

class LaunchLoginRequest(BaseModel):
    platform: str

class ImportCookiesRequest(BaseModel):
    platform: str
    cookies_raw: str

@app.post("/api/platforms/cookies")
def import_platform_cookies(req: ImportCookiesRequest):
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    platform_key = req.platform.lower()
    raw = req.cookies_raw.strip()
    
    cookie_list = []
    domain_map = {
        "olx": ".olx.pt",
        "facebook": ".facebook.com",
        "amazon": ".amazon.es",
        "worten": ".worten.pt",
        "cex": ".webuy.com",
        "pcdiga": ".pcdiga.com"
    }
    default_domain = domain_map.get(platform_key, f".{platform_key}.com")

    # Parse JSON if user pasted JSON array
    if raw.startswith("[") or raw.startswith("{"):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                cookie_list = parsed
            elif isinstance(parsed, dict) and "cookies" in parsed:
                cookie_list = parsed["cookies"]
        except Exception:
            pass

    # If raw string of key=value; key2=value2
    if not cookie_list and "=" in raw:
        items = [i.strip() for i in raw.split(";") if "=" in i]
        for item in items:
            k, v = item.split("=", 1)
            k = k.strip()
            v = v.strip()
            if k:
                cookie_list.append({
                    "name": k,
                    "value": v,
                    "domain": default_domain,
                    "path": "/",
                    "httpOnly": False,
                    "secure": True,
                    "sameSite": "Lax"
                })

    if not cookie_list:
        raise HTTPException(status_code=400, detail="Formato de cookies inválido.")

    state_data = {
        "cookies": cookie_list,
        "origins": []
    }
    state_file = PROFILE_DIR / f"storage_state_{platform_key}.json"
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state_data, f, indent=2)

    return {"status": "saved", "platform": platform_key, "count": len(cookie_list)}

@app.post("/api/platforms/clear")
def clear_platform_sessions(req: Optional[LaunchLoginRequest] = None):
    import shutil
    cleared = []
    if req and req.platform and req.platform != "all":
        p_file = PROFILE_DIR / f"storage_state_{req.platform.lower()}.json"
        if p_file.exists():
            p_file.unlink()
            cleared.append(req.platform)
    else:
        # Clear all
        if PROFILE_DIR.exists():
            for f in PROFILE_DIR.glob("*.json"):
                f.unlink()
            cleared.append("all")
            
    return {"status": "cleared", "platforms": cleared}

# ==========================================
# Batch Pitch & Negotiation Dispatcher API
# ==========================================
PITCH_TEMPLATES_MATRIX = {
    # CTT à Cobrança
    ("ctt_cobranca", "direto"): "Olá! Tenho muito interesse no portátil {title}. Aceita fechar negócio por {offer_price}€ com envio via CTT Expresso à cobrança (ou Entregas OLX) e pagamento no ato de entrega? Assumo eu a totalidade dos portes de envio. Obrigado!",
    ("ctt_cobranca", "dinheiro_imediato"): "Olá! Tenho muito interesse no portátil {title}. Se aceitar fechar por {offer_price}€ com envio via CTT Expresso à cobrança, fecho negócio hoje mesmo e assumo a totalidade dos portes de envio. Obrigado!",
    ("ctt_cobranca", "estudante"): "Boa tarde! Gostei muito do portátil {title}. Sou estudante e o meu orçamento limite é de {offer_price}€. Seria possível fechar negócio por esse valor com envio via CTT Expresso à cobrança (ou Entregas OLX)? Assumo eu a totalidade dos portes de envio. Muito obrigado!",
    ("ctt_cobranca", "suave"): "Olá! O portátil {title} tem ótimas características. O valor anunciado está um pouco acima do que pretendia gastar. Seria viável considerar uma oferta de {offer_price}€ com envio via CTT à cobrança? Assumo eu os portes de envio. Obrigado!",

    # Presencial em Mãos
    ("presencial", "direto"): "Olá! Tenho muito interesse no portátil {title}. Consegue fazer por {offer_price}€ com levantamento presencial em mãos e pagamento a pronto em dinheiro ou MBWay? Posso passar a levantar em {location}. Obrigado!",
    ("presencial", "dinheiro_imediato"): "Olá! Tenho muito interesse no portátil {title}. Consegue fazer por {offer_price}€? Tenho o dinheiro disponível e posso passar a levantar em mãos hoje mesmo em {location} com pagamento a pronto em dinheiro ou MBWay. Obrigado!",
    ("presencial", "estudante"): "Boa tarde! Gostei muito do portátil {title}. Sou estudante e o meu orçamento limite é de {offer_price}€. Seria possível fechar negócio por esse valor com levantamento presencial em mãos em {location} e pagamento a pronto? Obrigado!",
    ("presencial", "suave"): "Olá! Gostei bastante do portátil {title}. Seria viável negociar o valor para {offer_price}€ com levantamento em mãos na sua zona ({location}) e pagamento a pronto em dinheiro ou MBWay? Muito obrigado!",

    # Auto-Adaptativo por Raio (Long distance default; dist <= 50km will resolve to presencial)
    ("auto", "direto"): "Olá! Tenho muito interesse no portátil {title}. Como resido na Marinha Grande, aceita fechar negócio por {offer_price}€ com envio à cobrança via CTT Expresso (ou Entregas OLX) e pagamento na entrega? Assumo eu os portes de envio. Muito obrigado!",
    ("auto", "dinheiro_imediato"): "Olá! Tenho muito interesse no portátil {title}. Se aceitar {offer_price}€ com envio à cobrança via CTT Expresso, fecho negócio hoje mesmo e assumo a totalidade dos portes de envio. Muito obrigado!",
    ("auto", "estudante"): "Boa tarde! Gostei muito do portátil {title}. Sou estudante e o meu orçamento limite é de {offer_price}€. Como resido na Marinha Grande, aceita fechar negócio por esse valor com envio via CTT à cobrança? Assumo eu os portes de envio. Muito obrigado!",
    ("auto", "suave"): "Olá! Gostei bastante do portátil {title}. Como resido na Marinha Grande, seria viável considerar {offer_price}€ com envio à cobrança via CTT Expresso? Assumo eu os portes de envio. Muito obrigado!"
}

def get_pitch_template(delivery_method: str, pitch_tone: str, dist: Optional[float] = None) -> str:
    method = delivery_method.lower().strip() if delivery_method else "auto"
    if method in ["ctt", "cobranca"]:
        method = "ctt_cobranca"
    if method not in ["auto", "ctt_cobranca", "presencial"]:
        method = "auto"
    tone = pitch_tone.lower().strip() if pitch_tone else "direto"
    if tone in ["rapido", "dinheiro"]:
        tone = "dinheiro_imediato"
    if tone not in ["direto", "dinheiro_imediato", "estudante", "suave"]:
        tone = "direto"

    # In auto mode, if seller is within 50km, adapt dynamically to in-person template with the same tone!
    if method == "auto" and dist is not None and dist <= 50:
        return PITCH_TEMPLATES_MATRIX.get(("presencial", tone), PITCH_TEMPLATES_MATRIX[("presencial", "direto")])

    return PITCH_TEMPLATES_MATRIX.get((method, tone), PITCH_TEMPLATES_MATRIX[(method, "direto")])

PITCH_TEMPLATES = {f"{m}_{t}": tmpl for (m, t), tmpl in PITCH_TEMPLATES_MATRIX.items()}


def check_platform_session_certified(platform: str) -> bool:
    platform_key = platform.lower()
    state_file = PROFILE_DIR / f"storage_state_{platform_key}.json"
    if state_file.exists() and state_file.stat().st_size > 20:
        return True
    general_state = PROFILE_DIR / "storage_state.json"
    if general_state.exists():
        try:
            with open(general_state, "r") as f:
                data = json.load(f)
                domains = [c.get("domain", "") for c in data.get("cookies", [])]
                if any(platform_key in d for d in domains):
                    return True
        except Exception:
            pass
    return False

@app.get("/api/pitches/preview")
def preview_pitches(
    section: str = "value",
    platforms: str = "olx,facebook",
    discount_pct: float = 20.0,
    pitch_type: str = "dinheiro_imediato",
    delivery_method: str = "auto",
    custom_template: Optional[str] = None,
    limit: int = 500
):
    platform_list = [p.strip().lower() for p in platforms.split(",") if p.strip()]
    if not platform_list:
        platform_list = ["olx", "facebook"]

    conn = get_connection()
    cursor = conn.cursor()

    placeholders = ",".join("?" for _ in platform_list)

    order_clause = "COALESCE(deal_score, spec_score, 0) DESC"
    if section == "price_asc":
        order_clause = "price ASC"
    elif section == "specs":
        order_clause = "COALESCE(spec_score, 0) DESC"
    elif section == "all":
        order_clause = "id DESC"

    query = f"""
        SELECT * FROM laptops
        WHERE LOWER(source) IN ({placeholders})
          AND price > 0
          AND (contact_status IS NULL OR contact_status NOT IN ('offered', 'agreed', 'counter_offer'))
          AND url IS NOT NULL AND url != ''
        ORDER BY {order_clause}
        LIMIT ?
    """
    params = platform_list + [limit]
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]

    cursor.execute(f"""
        SELECT COUNT(*) as total FROM laptops
        WHERE LOWER(source) IN ({placeholders})
          AND price > 0
          AND (contact_status IS NULL OR contact_status NOT IN ('offered', 'agreed', 'counter_offer'))
    """, platform_list)
    total_eligible = cursor.fetchone()["total"]
    conn.close()

    targets = []
    for r in rows:
        orig_price = float(r.get("price") or 0)
        offer_price = round(orig_price * (1.0 - (discount_pct / 100.0)))
        title = r.get("title") or "computador portátil"
        location = r.get("location") or "Portugal"
        source = (r.get("source") or "olx").lower()
        dist = r.get("travel_distance_km")

        # Dynamic template replacement based on delivery method & pitch tone matrix
        if custom_template and custom_template.strip():
            msg = custom_template.strip()
            msg = msg.replace("{title}", title)
            msg = msg.replace("{offer_price}", str(offer_price))
            msg = msg.replace("{price}", str(int(orig_price)))
            msg = msg.replace("{discount_pct}", str(int(discount_pct)))
            msg = msg.replace("{location}", location)
        else:
            base_tmpl = get_pitch_template(delivery_method, pitch_type, dist)
            msg = (base_tmpl
                .replace("{title}", title)
                .replace("{offer_price}", str(offer_price))
                .replace("{price}", str(int(orig_price)))
                .replace("{discount_pct}", str(int(discount_pct)))
                .replace("{location}", location))

        has_session = check_platform_session_certified(source)

        targets.append({
            "id": r.get("id"),
            "title": title,
            "price": orig_price,
            "offer_price": offer_price,
            "discount_pct": discount_pct,
            "discount_eur": round(orig_price - offer_price),
            "source": source,
            "url": r.get("url"),
            "image_url": r.get("image_url"),
            "location": location,
            "travel_distance_km": dist,
            "spec_score": r.get("spec_score"),
            "deal_score": r.get("deal_score"),
            "message": msg,
            "has_session": has_session
        })

    sessions_status = {
        p: {
            "certified": check_platform_session_certified(p),
            "requires_login": p in ["olx", "facebook"]
        }
        for p in platform_list
    }

    missing_session_platforms = [
        p.upper() for p in platform_list
        if sessions_status[p]["requires_login"] and not sessions_status[p]["certified"]
    ]
    can_dispatch = len(missing_session_platforms) == 0

    default_template = get_pitch_template(delivery_method, pitch_type)

    sample_msg = targets[0]["message"] if targets else None
    if not sample_msg:
        dummy_price = int(500 * (1 - (discount_pct / 100.0)))
        active_t = custom_template.strip() if (custom_template and custom_template.strip()) else default_template
        sample_msg = (active_t
            .replace("{title}", "Portátil Gaming / Trabalho")
            .replace("{offer_price}", str(dummy_price))
            .replace("{price}", "500")
            .replace("{discount_pct}", str(int(discount_pct)))
            .replace("{location}", "Leiria"))

    return {
        "targets": targets,
        "sample_target": targets[0] if targets else None,
        "sample_message": sample_msg,
        "default_template": default_template,
        "available_templates": PITCH_TEMPLATES,
        "total_eligible": total_eligible,
        "section": section,
        "delivery_method": delivery_method,
        "platform_sessions": sessions_status,
        "can_dispatch": can_dispatch,
        "missing_session_platforms": missing_session_platforms
    }


class TargetItem(BaseModel):
    laptop_id: int
    offer_price: float
    discount_pct: float
    pitch_message: str
    strategy_used: str

class BatchPitchDispatchRequest(BaseModel):
    targets: List[TargetItem]
    mode: str = "record"

@app.post("/api/pitches/dispatch")
def dispatch_pitches(req: BatchPitchDispatchRequest):
    conn = get_connection()
    created = []
    with conn:
        cursor = conn.cursor()
        for t in req.targets:
            cursor.execute("SELECT * FROM laptops WHERE id = ?", (t.laptop_id,))
            laptop = cursor.fetchone()
            if not laptop:
                continue
            laptop_dict = dict(laptop)
            orig_price = float(laptop_dict.get("price") or t.offer_price)
            seller_name = laptop_dict.get("seller_name") or "Vendedor"
            source = (laptop_dict.get("source") or "olx").lower()

            # Enforce active session on C2C platforms: block dispatch without active session
            if source in ["olx", "facebook"] and not check_platform_session_certified(source):
                raise HTTPException(
                    status_code=400,
                    detail=f"Sessão necessária na plataforma {source.upper()} para envio de propostas. Inicie sessão no Playwright antes de disparar."
                )

            cursor.execute("""
                INSERT INTO laptop_negotiations (
                    laptop_id, seller_name, original_price, offered_price,
                    discount_percentage, strategy_used, pitch_message, status,
                    offer_sent_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'sent', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (
                t.laptop_id,
                seller_name,
                orig_price,
                t.offer_price,
                t.discount_pct,
                t.strategy_used,
                t.pitch_message
            ))
            neg_id = cursor.lastrowid

            cursor.execute("""
                UPDATE laptops
                SET contact_status = 'offered',
                    negotiation_status = 'sent',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (t.laptop_id,))

            created.append({
                "negotiation_id": neg_id,
                "laptop_id": t.laptop_id,
                "title": laptop_dict.get("title"),
                "offered_price": t.offer_price,
                "source": laptop_dict.get("source"),
                "url": laptop_dict.get("url")
            })
    conn.close()

    logger.info(f"[Batch Pitch] Lançadas com sucesso {len(created)} propostas a toda a seleção.")
    return {
        "status": "success",
        "created_count": len(created),
        "dispatched": created
    }

@app.post("/api/platforms/login")
async def launch_platform_login(req: LaunchLoginRequest, background_tasks: BackgroundTasks):
    platform_key = req.platform.lower()
    match = next((p for p in PLATFORMS_CONFIG if p["id"] == platform_key), None)
    url = match["auth_url"] if match else "https://login.olx.pt"
    
    async def _open_session():
        try:
            # Set default X11 display for Linux desktop / AnyDesk sessions if not set
            if "DISPLAY" not in os.environ:
                os.environ["DISPLAY"] = ":1"
            if "XAUTHORITY" not in os.environ:
                xauth = Path("/run/user/1000/gdm/Xauthority")
                if xauth.exists():
                    os.environ["XAUTHORITY"] = str(xauth)

            from playwright.async_api import async_playwright
            PROFILE_DIR.mkdir(parents=True, exist_ok=True)
            async with async_playwright() as p:
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=str(PROFILE_DIR),
                    headless=False,
                    viewport={"width": 1024, "height": 720},
                    args=[
                        "--window-size=1024,768",
                        "--window-position=120,80",
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox"
                    ],
                    user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                )
                page = context.pages[0] if context.pages else await context.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=35000)

                state_file = PROFILE_DIR / f"storage_state_{platform_key}.json"
                # Keep browser open while user completes login (up to 10 min, or until closed)
                for _ in range(300):
                    if not context.pages or all(pg.is_closed() for pg in context.pages):
                        break
                    try:
                        await context.storage_state(path=str(state_file))
                    except Exception:
                        pass
                    await asyncio.sleep(2)

                try:
                    await context.storage_state(path=str(state_file))
                    logger.info(f"Sessão e cookies guardados com sucesso para {platform_key} em {state_file}")
                except Exception as e:
                    logger.warning(f"Erro ao guardar storage_state final para {platform_key}: {e}")

                try:
                    await context.close()
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Erro na sessão de login visível para {platform_key}: {e}")

    background_tasks.add_task(_open_session)
    return {"status": "launched", "platform": req.platform, "url": url}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8001))
    host = os.environ.get("HOST", "127.0.0.1")
    uvicorn.run("main:app", host=host, port=port, reload=True, app_dir=str(BASE_DIR))
