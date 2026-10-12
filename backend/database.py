"""
backend/database.py - Isolated SQLite database engine for Laptop Scraper & Deal Hunter.
Stores laptops, specifications, price negotiations, and OLX messages.
"""

import sqlite3
import os
import json
import re
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

logger = logging.getLogger("database")

DB_PATH = Path(__file__).resolve().parent / "laptops.db"

def extract_warranty_info(title: str = "", description: str = "", source: str = "") -> Tuple[bool, Optional[str]]:
    """
    Deterministically detects whether a laptop listing has active warranty
    and extracts the warranty details string.
    """
    text = f"{title or ''} {description or ''}".lower()
    source_lower = (source or "").lower()
    
    # 1. Retail stores with mandatory legal warranty in Portugal
    if "cex" in source_lower:
        return True, "Garantia 5 Anos CeX"
    if "pcdiga" in source_lower:
        if "recondicionado" in text:
            return True, "Garantia Recondicionado 1 Ano"
        return True, "Garantia Oficial 3 Anos"
    if "worten" in source_lower:
        return True, "Garantia Oficial 3 Anos"
    if "amazon" in source_lower:
        if "renewed" in text or "recondicionado" in text:
            return True, "Garantia Amazon Renewed 1 Ano"
        return True, "Garantia Oficial 3 Anos"
    if "globaldata" in source_lower or "pccomponentes" in source_lower:
        return True, "Garantia Oficial 3 Anos"
        
    # 2. Classifieds (OLX, Facebook Marketplace, CustoJusto):
    negative_warranty = [
        "sem garantia", "já não tem garantia", "ja nao tem garantia",
        "garantia expirou", "garantia terminada", "fora da garantia",
        "sem fatura nem garantia"
    ]
    if any(neg in text for neg in negative_warranty):
        return False, "Sem Garantia"
        
    # Check for specific dates/years
    m_until = re.search(r'garantia\s+at[eé]\s+(?:(?:o\s+)?m[eê]s\s+\w+\s+(?:de\s+)?)?((?:20\d{2})|(?:\d{1,2}/\d{4}))', text)
    if m_until:
        return True, f"Garantia até {m_until.group(1)}"
        
    m_years = re.search(r'garantia\s+(?:de\s+)?(\d)\s+ano', text)
    if m_years:
        return True, f"Garantia {m_years.group(1)} Anos"

    m_months = re.search(r'garantia\s+(?:de\s+)?(\d{1,2})\s+meses', text)
    if m_months:
        return True, f"Garantia {m_months.group(1)} Meses"
        
    positive_warranty_cues = [
        ("applecare+", "Garantia AppleCare+"),
        ("apple care", "Garantia AppleCare"),
        ("garantia oficial", "Garantia Oficial"),
        ("garantia de fábrica", "Garantia de Fábrica"),
        ("garantia de fabrica", "Garantia de Fábrica"),
        ("com fatura e garantia", "Fatura e Garantia"),
        ("fatura e garantia", "Fatura e Garantia"),
        ("com garantia", "Com Garantia"),
        ("garantia ativa", "Garantia Ativa"),
        ("garantia fnac", "Garantia FNAC"),
        ("garantia worten", "Garantia Worten"),
        ("garantia rádio popular", "Garantia Rádio Popular"),
        ("garantia radio popular", "Garantia Rádio Popular"),
        ("garantia pcdiga", "Garantia PCDIGA"),
        ("garantia lenovo", "Garantia Lenovo"),
        ("garantia dell", "Garantia Dell"),
        ("garantia asus", "Garantia ASUS"),
        ("garantia hp", "Garantia HP")
    ]
    for cue, label in positive_warranty_cues:
        if cue in text:
            return True, label
            
    if re.search(r'\bgarantia\b', text):
        return True, "Com Garantia Mencionada"
        
    return False, None

def extract_condition_info(title: str = "", description: str = "", source: str = "") -> str:
    """
    Classifies laptop condition into 'Novo', 'Recondicionado', or 'Usado'.
    """
    text = f"{title or ''} {description or ''}".lower()
    source_lower = (source or "").lower()
    
    if "cex" in source_lower:
        return "Recondicionado"
        
    if any(k in text for k in ["recondicionado", "refurbished", "renewed", "grade a", "grade b"]):
        return "Recondicionado"
        
    if any(k in text for k in ["novo selado", "selado em caixa", "selado na caixa", "nunca usado", "a estrear", "fatura novo"]):
        return "Novo (Selado)"
        
    if "olx" in source_lower or "facebook" in source_lower or "custojusto" in source_lower:
        return "Usado"
        
    if any(k in source_lower for k in ["pcdiga", "worten", "amazon", "globaldata", "pccomponentes"]):
        return "Novo"
        
    return "Usado"

def get_connection():
    conn = sqlite3.connect(str(DB_PATH), timeout=15.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 15000")
    conn.execute("PRAGMA cache_size = -64000")
    conn.execute("PRAGMA temp_store = MEMORY")
    return conn

def init_db():
    conn = get_connection()
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except Exception:
        pass
    with conn:
        cursor = conn.cursor()
        
        # 1. Laptops table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS laptops (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                price REAL,
                original_price REAL,
                location TEXT,
                latitude REAL,
                longitude REAL,
                travel_distance_km REAL,
                travel_duration_mins REAL,
                is_near_lisbon INTEGER DEFAULT 0,
                supports_shipping INTEGER DEFAULT 0,
                brand TEXT,
                cpu TEXT,
                ram_gb INTEGER,
                ram_type TEXT,
                ram_display TEXT,
                storage_gb INTEGER,
                storage_type TEXT,
                storage_display TEXT,
                gpu TEXT,
                screen_size TEXT,
                resolution TEXT,
                battery_health_pct INTEGER,
                battery_state TEXT,
                condition_grade TEXT,
                has_warranty INTEGER DEFAULT 0,
                warranty_details TEXT,
                description TEXT,
                spec_score REAL,
                value_score REAL,
                deal_score REAL,
                power_idle_watts INTEGER,
                power_peak_watts INTEGER,
                monthly_cost_eur REAL,
                deal_verdict TEXT,
                deal_pros TEXT,
                deal_cons TEXT,
                source TEXT DEFAULT 'olx',
                contact_status TEXT DEFAULT 'pending',
                contact_notes TEXT,
                negotiation_status TEXT DEFAULT 'pending',
                image_url TEXT,
                image_urls TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Laptop Negotiations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS laptop_negotiations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                laptop_id INTEGER NOT NULL UNIQUE,
                seller_id TEXT,
                seller_name TEXT,
                status TEXT DEFAULT 'pending',
                original_price REAL NOT NULL,
                offered_price REAL NOT NULL,
                discount_percentage REAL NOT NULL,
                strategy_used TEXT NOT NULL,
                pitch_message TEXT NOT NULL,
                seller_response TEXT,
                offer_sent_at TIMESTAMP,
                responded_at TIMESTAMP,
                follow_up_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (laptop_id) REFERENCES laptops (id) ON DELETE CASCADE
            )
        """)

        # 3. OLX Conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS olx_conversations (
                id TEXT PRIMARY KEY,
                seller_name TEXT,
                ad_id TEXT,
                ad_title TEXT,
                price REAL,
                image_url TEXT,
                is_inactive INTEGER DEFAULT 0,
                last_message TEXT,
                last_message_time TEXT,
                has_seller_reply INTEGER DEFAULT 0,
                is_deal_agreed INTEGER DEFAULT 0,
                agreed_price REAL,
                laptop_id INTEGER,
                raw_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (laptop_id) REFERENCES laptops (id) ON DELETE SET NULL
            )
        """)

        # 4. OLX Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS olx_messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                sender_type TEXT,
                text TEXT,
                created_at TEXT,
                raw_json TEXT,
                FOREIGN KEY (conversation_id) REFERENCES olx_conversations (id) ON DELETE CASCADE
            )
        """)

        # Migration: Ensure image_url, has_warranty, warranty_details exist in laptops table
        cursor.execute("PRAGMA table_info(laptops)")
        existing_cols = [col["name"] if isinstance(col, sqlite3.Row) else col[1] for col in cursor.fetchall()]
        if "image_url" not in existing_cols:
            cursor.execute("ALTER TABLE laptops ADD COLUMN image_url TEXT")
            logger.info("Migrated laptops table: Added image_url column.")
        if "has_warranty" not in existing_cols:
            cursor.execute("ALTER TABLE laptops ADD COLUMN has_warranty INTEGER DEFAULT 0")
            logger.info("Migrated laptops table: Added has_warranty column.")
        if "warranty_details" not in existing_cols:
            cursor.execute("ALTER TABLE laptops ADD COLUMN warranty_details TEXT")
            logger.info("Migrated laptops table: Added warranty_details column.")

        # Automatic backfill of warranty and condition for existing records
        try:
            cursor.execute("SELECT id, title, description, source, condition_grade, has_warranty, warranty_details FROM laptops WHERE has_warranty IS NULL OR has_warranty = 0 OR condition_grade IS NULL")
            to_backfill = cursor.fetchall()
            for r in to_backfill:
                t = r["title"] or ""
                d = r["description"] or ""
                s = r["source"] or ""
                has_w_bool, w_det = extract_warranty_info(t, d, s)
                cond = r["condition_grade"] or extract_condition_info(t, d, s)
                if has_w_bool or not r["condition_grade"]:
                    cursor.execute("""
                        UPDATE laptops SET 
                            has_warranty = ?,
                            warranty_details = COALESCE(warranty_details, ?),
                            condition_grade = COALESCE(condition_grade, ?)
                        WHERE id = ?
                    """, (1 if has_w_bool else 0, w_det, cond, r["id"]))
            if to_backfill:
                logger.info(f"Backfilled warranty & condition on {len(to_backfill)} existing laptop records.")
        except Exception as bf_err:
            logger.debug(f"Backfill note: {bf_err}")
    conn.close()

def get_laptops(
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
) -> Dict[str, Any]:
    conn = get_connection()
    conditions = []
    params: List[Any] = []

    if search:
        conditions.append("(title LIKE ? OR cpu LIKE ? OR gpu LIKE ? OR location LIKE ? OR brand LIKE ?)")
        wildcard = f"%{search}%"
        params.extend([wildcard, wildcard, wildcard, wildcard, wildcard])

    if source and source.lower() != "all":
        conditions.append("LOWER(source) = ?")
        params.append(source.lower())

    if condition and condition.lower() != "all":
        c_clean = condition.lower()
        if c_clean in ("usado", "used", "segunda_mao"):
            conditions.append("(LOWER(condition_grade) LIKE '%usado%' OR LOWER(condition_grade) LIKE '%segunda%')")
        elif c_clean in ("recondicionado", "refurbished", "renewed"):
            conditions.append("(LOWER(condition_grade) LIKE '%recondicionado%' OR LOWER(condition_grade) LIKE '%renewed%' OR LOWER(condition_grade) LIKE '%refurbished%')")
        elif c_clean in ("novo", "new"):
            conditions.append("(LOWER(condition_grade) LIKE '%novo%' OR LOWER(condition_grade) LIKE '%selado%')")

    if has_warranty is True or (isinstance(has_warranty, (int, str)) and str(has_warranty).lower() in ("true", "1")):
        conditions.append("has_warranty = 1")

    if min_price is not None:
        conditions.append("price >= ?")
        params.append(min_price)

    if max_price is not None:
        conditions.append("price <= ?")
        params.append(max_price)

    if min_ram is not None:
        conditions.append("ram_gb >= ?")
        params.append(min_ram)

    if min_storage is not None:
        conditions.append("storage_gb >= ?")
        params.append(min_storage)

    if min_score is not None:
        conditions.append("COALESCE(deal_score, spec_score, 0) >= ?")
        params.append(min_score)

    if negotiation_status and negotiation_status != "all":
        conditions.append("negotiation_status = ?")
        params.append(negotiation_status)

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) as total FROM laptops {where_clause}", params)
    total = cursor.fetchone()["total"]

    valid_sort_cols = {
        "deal_score": "COALESCE(deal_score, spec_score, 0)",
        "price": "price",
        "ram_gb": "ram_gb",
        "storage_gb": "storage_gb",
        "id": "id"
    }
    col = valid_sort_cols.get(sort_by, "COALESCE(deal_score, spec_score, 0)")
    direction = "DESC" if sort_order.lower() == "desc" else "ASC"
    order_clause = f"ORDER BY {col} {direction}"

    cursor.execute(f"SELECT * FROM laptops {where_clause} {order_clause} LIMIT ? OFFSET ?", params + [limit, offset])
    rows = cursor.fetchall()
    conn.close()

    from hardware_comparator import get_hardware_dossier
    laptops = []
    for r in rows:
        d = dict(r)
        d["hardware_dossier"] = get_hardware_dossier(d)
        laptops.append(d)

    return {"total": total, "laptops": laptops, "limit": limit, "offset": offset}

def get_laptop_stats() -> Dict[str, Any]:
    conn = get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as total FROM laptops")
        total = cursor.fetchone()["total"]

        cursor.execute("SELECT AVG(price) as avg_price FROM laptops WHERE price > 0")
        avg_price = cursor.fetchone()["avg_price"]

        cursor.execute("SELECT COUNT(*) as near_lisbon FROM laptops WHERE is_near_lisbon = 1")
        near_lisbon = cursor.fetchone()["near_lisbon"]

        cursor.execute("SELECT COUNT(*) as agreed FROM laptop_negotiations WHERE status = 'agreed'")
        agreed = cursor.fetchone()["agreed"]

        cursor.execute("SELECT COUNT(*) as pending FROM laptop_negotiations WHERE status = 'pending'")
        pending = cursor.fetchone()["pending"]

        cursor.execute("SELECT COUNT(*) as sent FROM laptop_negotiations WHERE status = 'sent'")
        sent = cursor.fetchone()["sent"]

        cursor.execute("SELECT COUNT(*) as chats FROM olx_conversations")
        chats = cursor.fetchone()["chats"]

        cursor.execute("SELECT COUNT(*) as with_warranty FROM laptops WHERE has_warranty = 1")
        with_warranty = cursor.fetchone()["with_warranty"]

        cursor.execute("SELECT COUNT(*) as second_hand FROM laptops WHERE LOWER(condition_grade) LIKE '%usado%' OR LOWER(condition_grade) LIKE '%segunda%'")
        second_hand = cursor.fetchone()["second_hand"]

        cursor.execute("SELECT COUNT(*) as refurbished FROM laptops WHERE LOWER(condition_grade) LIKE '%recondicionado%' OR LOWER(condition_grade) LIKE '%renewed%'")
        refurbished = cursor.fetchone()["refurbished"]

        cursor.execute("SELECT COUNT(*) as new_count FROM laptops WHERE LOWER(condition_grade) LIKE '%novo%' OR LOWER(condition_grade) LIKE '%selado%'")
        new_count = cursor.fetchone()["new_count"]

        return {
            "total": total,
            "total_laptops": total,
            "avg_price": round(avg_price, 2) if avg_price else 0.0,
            "near_lisbon": near_lisbon,
            "negotiated": agreed + pending + sent,
            "deals_agreed": agreed,
            "negotiations_pending": pending,
            "offers_sent": sent,
            "active_chats": chats,
            "with_warranty": with_warranty,
            "second_hand": second_hand,
            "refurbished": refurbished,
            "new_count": new_count
        }
    finally:
        conn.close()

def get_laptop_by_id(laptop_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM laptops WHERE id = ?", (laptop_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    from hardware_comparator import get_hardware_dossier
    d["hardware_dossier"] = get_hardware_dossier(d)
    return d

def update_laptop_contact(laptop_id: int, contact_status: str, contact_notes: Optional[str] = None) -> bool:
    conn = get_connection()
    with conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE laptops SET
                contact_status = ?,
                contact_notes = COALESCE(?, contact_notes),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (contact_status, contact_notes, laptop_id))
        updated = cursor.rowcount > 0
    conn.close()
    return updated

def create_or_update_negotiation(
    laptop_id: int,
    offer_price: float,
    original_price: Optional[float] = None,
    discount_pct: float = 20.0,
    offer_message: str = ""
) -> Dict[str, Any]:
    conn = get_connection()
    with conn:
        cursor = conn.cursor()
        cursor.execute("SELECT price, original_price FROM laptops WHERE id = ?", (laptop_id,))
        laptop = cursor.fetchone()
        if not laptop:
            conn.close()
            return {"error": "Laptop not found"}

        orig_price = original_price or laptop["original_price"] or laptop["price"]
        cursor.execute("""
            INSERT INTO laptop_negotiations (
                laptop_id, original_price, offered_price, discount_percentage,
                strategy_used, pitch_message, status, updated_at
            ) VALUES (?, ?, ?, ?, 'cash_deal', ?, 'pending', CURRENT_TIMESTAMP)
            ON CONFLICT(laptop_id) DO UPDATE SET
                offered_price = excluded.offered_price,
                discount_percentage = excluded.discount_percentage,
                pitch_message = excluded.pitch_message,
                updated_at = CURRENT_TIMESTAMP
        """, (laptop_id, orig_price, offer_price, discount_pct, offer_message))
    conn.close()
    return {"success": True, "laptop_id": laptop_id, "offered_price": offer_price}

def apply_negotiation_agreement(laptop_id: int, agreed_price: float, notes: str = "") -> bool:
    conn = get_connection()
    with conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE laptops
            SET price = ?,
                contact_status = 'agreed',
                negotiation_status = 'agreed',
                contact_notes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (agreed_price, notes, laptop_id))
        cursor.execute("""
            UPDATE laptop_negotiations
            SET status = 'agreed',
                responded_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE laptop_id = ?
        """, (laptop_id,))
    conn.close()
    return True

def record_negotiation_response(laptop_id: int, response_text: str, status: str = "countered") -> bool:
    conn = get_connection()
    with conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE laptop_negotiations
            SET seller_response = ?,
                status = ?,
                responded_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE laptop_id = ?
        """, (response_text, status, laptop_id))
    conn.close()
    return True

def get_negotiations() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT n.*, l.title, l.url, l.location, l.cpu, l.gpu, l.ram_gb, l.storage_gb
        FROM laptop_negotiations n
        JOIN laptops l ON n.laptop_id = l.id
        ORDER BY n.updated_at DESC
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_pending_negotiations() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT n.*, l.title, l.url
        FROM laptop_negotiations n
        JOIN laptops l ON n.laptop_id = l.id
        WHERE n.status = 'pending'
        ORDER BY n.created_at ASC
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

UPSERT_LAPTOP_SQL = """
    INSERT INTO laptops (
        url, title, price, original_price, location,
        latitude, longitude, travel_distance_km, travel_duration_mins,
        is_near_lisbon, supports_shipping, brand, cpu,
        ram_gb, ram_type, ram_display, storage_gb,
        storage_type, storage_display, gpu, screen_size,
        resolution, condition_grade, has_warranty, warranty_details, description, spec_score,
        value_score, deal_score, power_idle_watts, power_peak_watts,
        monthly_cost_eur, deal_verdict, deal_pros, deal_cons,
        source, image_url, image_urls, updated_at
    ) VALUES (
        :url, :title, :price, :original_price, :location,
        :latitude, :longitude, :travel_distance_km, :travel_duration_mins,
        :is_near_lisbon, :supports_shipping, :brand, :cpu,
        :ram_gb, :ram_type, :ram_display, :storage_gb,
        :storage_type, :storage_display, :gpu, :screen_size,
        :resolution, :condition_grade, :has_warranty, :warranty_details, :description, :spec_score,
        :value_score, :deal_score, :power_idle_watts, :power_peak_watts,
        :monthly_cost_eur, :deal_verdict, :deal_pros, :deal_cons,
        :source, :image_url, :image_urls, CURRENT_TIMESTAMP
    )
    ON CONFLICT(url) DO UPDATE SET
        title = excluded.title,
        price = excluded.price,
        location = excluded.location,
        condition_grade = COALESCE(excluded.condition_grade, laptops.condition_grade),
        has_warranty = COALESCE(excluded.has_warranty, laptops.has_warranty),
        warranty_details = COALESCE(excluded.warranty_details, laptops.warranty_details),
        image_url = COALESCE(excluded.image_url, laptops.image_url),
        image_urls = COALESCE(excluded.image_urls, laptops.image_urls),
        spec_score = COALESCE(excluded.spec_score, laptops.spec_score),
        deal_score = COALESCE(excluded.deal_score, laptops.deal_score),
        value_score = COALESCE(excluded.value_score, laptops.value_score),
        updated_at = CURRENT_TIMESTAMP
"""

def _prepare_laptop_params(deal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    url = deal.get("url") or deal.get("link")
    if not url:
        return None

    images = deal.get("image_urls") or deal.get("image_url")
    single_image = deal.get("image_url")
    if isinstance(images, list):
        image_urls_str = json.dumps(images)
        if not single_image and len(images) > 0:
            single_image = images[0]
    elif images:
        image_urls_str = str(images)
        if not single_image and str(images).startswith("http"):
            single_image = str(images)
    else:
        image_urls_str = None

    raw_title = deal.get("title") or "Unknown Laptop"
    raw_desc = deal.get("description") or ""
    raw_src = deal.get("source") or "olx"

    has_w = deal.get("has_warranty")
    w_details = deal.get("warranty_details")
    if has_w is None:
        has_w_bool, w_det = extract_warranty_info(raw_title, raw_desc, raw_src)
        has_w = 1 if has_w_bool else 0
        w_details = w_det
    else:
        has_w = 1 if has_w else 0

    cond_grade = deal.get("condition_grade") or deal.get("condition")
    if not cond_grade:
        cond_grade = extract_condition_info(raw_title, raw_desc, raw_src)

    return {
        "url": url,
        "title": raw_title,
        "price": deal.get("price"),
        "original_price": deal.get("original_price") or deal.get("price"),
        "location": deal.get("location"),
        "latitude": deal.get("latitude"),
        "longitude": deal.get("longitude"),
        "travel_distance_km": deal.get("travel_distance_km"),
        "travel_duration_mins": deal.get("travel_duration_mins"),
        "is_near_lisbon": 1 if deal.get("is_near_lisbon") else 0,
        "supports_shipping": 1 if deal.get("supports_shipping") else 0,
        "brand": deal.get("brand"),
        "cpu": deal.get("cpu"),
        "ram_gb": deal.get("ram_gb"),
        "ram_type": deal.get("ram_type"),
        "ram_display": deal.get("ram_display"),
        "storage_gb": deal.get("storage_gb"),
        "storage_type": deal.get("storage_type"),
        "storage_display": deal.get("storage_display"),
        "gpu": deal.get("gpu"),
        "screen_size": deal.get("screen_size"),
        "resolution": deal.get("resolution"),
        "condition_grade": cond_grade,
        "has_warranty": has_w,
        "warranty_details": w_details,
        "description": raw_desc,
        "spec_score": deal.get("spec_score"),
        "value_score": deal.get("value_score"),
        "deal_score": deal.get("deal_score") or deal.get("deal_rating_score") or deal.get("spec_score"),
        "power_idle_watts": deal.get("power_idle_watts"),
        "power_peak_watts": deal.get("power_peak_watts"),
        "monthly_cost_eur": deal.get("monthly_cost_eur"),
        "deal_verdict": deal.get("deal_verdict") or deal.get("deal_rating"),
        "deal_pros": json.dumps(deal["deal_pros"]) if isinstance(deal.get("deal_pros"), list) else deal.get("deal_pros"),
        "deal_cons": json.dumps(deal["deal_cons"]) if isinstance(deal.get("deal_cons"), list) else deal.get("deal_cons"),
        "source": raw_src,
        "image_url": single_image,
        "image_urls": image_urls_str
    }

def insert_or_update_laptop(deal: Dict[str, Any]) -> bool:
    """Inserts a new laptop or updates an existing one based on URL."""
    params = _prepare_laptop_params(deal)
    if not params:
        return False

    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(UPSERT_LAPTOP_SQL, params)
        return True
    except Exception as e:
        logger.error(f"[Database] Error inserting laptop {params.get('url')}: {e}")
        return False
    finally:
        conn.close()

def insert_or_update_laptops_batch(deals: List[Dict[str, Any]]) -> int:
    """Batch insert or update laptops in a single ACID transaction for instant speed."""
    if not deals:
        return 0
    count = 0
    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            for deal in deals:
                params = _prepare_laptop_params(deal)
                if not params:
                    continue
                try:
                    cursor.execute(UPSERT_LAPTOP_SQL, params)
                    count += 1
                except Exception as row_err:
                    logger.debug(f"[Database] Error upserting laptop: {row_err}")
    except Exception as e:
        logger.error(f"[Database] Error in batch insert: {e}")
    finally:
        conn.close()
    return count

def reset_database(backup: bool = True) -> Dict[str, Any]:
    """
    Safely resets the laptops database:
    1. If backup is True and DB exists, creates laptops.db.backup
    2. Drops existing tables and re-initializes pristine schema
    3. VACUUMs the database file
    """
    import shutil
    backup_file = None
    if backup and DB_PATH.exists():
        backup_file = DB_PATH.with_suffix(".db.backup")
        shutil.copy2(DB_PATH, backup_file)
    
    conn = get_connection()
    with conn:
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS olx_messages")
        cursor.execute("DROP TABLE IF EXISTS olx_conversations")
        cursor.execute("DROP TABLE IF EXISTS laptop_negotiations")
        cursor.execute("DROP TABLE IF EXISTS laptops")
    conn.close()

    init_db()

    conn = get_connection()
    conn.execute("VACUUM")
    conn.close()

    return {
        "status": "success",
        "message": "Database reset to pristine state (0 deals, 0 negotiations).",
        "backup_created": str(backup_file) if backup_file else None
    }


