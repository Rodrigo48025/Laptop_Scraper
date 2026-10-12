#!/usr/bin/env python3
"""
tools/sync_chats.py - OLX Chat Synchronization Engine.

Extracts all active conversations and message threads from OLX (via persistent Playwright session),
detects seller replies and accepted purchase proposals, matches with laptops in SQLite,
and updates deal statuses in real time.
"""

import sys
import os
import re
import json
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import types
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
src_module = types.ModuleType("src")
src_module.__path__ = [str(BASE_DIR)]
sys.modules["src"] = src_module

from playwright.async_api import async_playwright
from src.database import get_connection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("sync_chats")

PROFILE_DIR = BASE_DIR / "data" / "playwright_profile"

AGREEMENT_KEYWORDS = [
    "sim", "aceito", "pode ser", "combinado", "fechado", "prefiro e facilita",
    "fechamos", "concordo", "está bem", "esta bem", "tudo bem", "ok", "aceite"
]

DECLINE_KEYWORDS = [
    "não", "nao", "não aceito", "pouco", "mínimo", "minimo", "já vendi", "ja vendi", "não posso"
]


def detect_deal_status(messages: List[Dict[str, Any]]) -> Tuple[bool, bool, Optional[float]]:
    """
    Analyzes conversation messages to detect if the seller replied and if the offer was accepted.
    Returns (has_seller_reply, is_agreed, agreed_price).
    """
    has_seller_reply = False
    is_agreed = False
    agreed_price = None

    last_offer = None
    for m in messages:
        text = m.get("text", "")
        # Extract offer price if it was an offer from "me"
        if m.get("sender") == "me":
            # Match patterns like "560€", "480 €", "fechar por 480€"
            match = re.search(r"(\d{2,4})\s*€", text)
            if match:
                try:
                    last_offer = float(match.group(1))
                except ValueError:
                    pass
        elif m.get("sender") == "seller":
            has_seller_reply = True
            lower = text.lower()
            
            # Check for agreement
            for kw in AGREEMENT_KEYWORDS:
                if kw in lower:
                    # Make sure it's not a negation like "não aceito"
                    if "não" not in lower and "nao" not in lower:
                        is_agreed = True
                        agreed_price = last_offer
                        break
                    elif "sim" in lower:
                        is_agreed = True
                        agreed_price = last_offer
                        break

    return has_seller_reply, is_agreed, agreed_price


def find_matching_laptop_id(ad_id: Optional[str], ad_title: Optional[str], price: Optional[float]) -> Optional[int]:
    """
    Finds the corresponding laptop in leads.db by OLX ad_id or fuzzy title match.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Match by ad_id in URL
    if ad_id:
        cursor.execute("SELECT id FROM laptops WHERE url LIKE ? LIMIT 1", (f"%{ad_id}%",))
        row = cursor.fetchone()
        if row:
            conn.close()
            return row["id"]

    # 2. Match by title
    if ad_title:
        clean_title = re.sub(r"[^\w\s]", "", ad_title.lower()).strip()
        words = [w for w in clean_title.split() if len(w) > 3][:4]
        if words:
            query = "SELECT id, title FROM laptops WHERE " + " AND ".join(["LOWER(title) LIKE ?" for _ in words]) + " LIMIT 1"
            params = [f"%{w}%" for w in words]
            cursor.execute(query, params)
            row = cursor.fetchone()
            if row:
                conn.close()
                return row["id"]

    conn.close()
    return None


async def sync_olx_chats(headless: bool = True) -> Dict[str, Any]:
    """
    Extracts all conversations and messages from OLX Portugal via Playwright.
    Updates SQLite database and returns summary.
    """
    if not PROFILE_DIR.exists() or not any(PROFILE_DIR.iterdir()):
        return {
            "success": False,
            "error": "Perfil do Playwright não encontrado. Executa python3 tools/auto_messenger.py --login primeiro."
        }

    logger.info("A iniciar sincronização de chats OLX via Playwright...")
    synced_conversations = []
    from src.browser_lock import BrowserLock

    async with BrowserLock(timeout=45):
        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=str(PROFILE_DIR),
                headless=headless,
                viewport={"width": 1280, "height": 850},
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
            )

            page = context.pages[0] if context.pages else await context.new_page()

        try:
            # 1. Navigate to OLX chat answers
            logger.info("A navegar para https://www.olx.pt/myaccount/answers/?my_ads=0 ...")
            await page.goto("https://www.olx.pt/myaccount/answers/?my_ads=0", wait_until="domcontentloaded", timeout=25000)
            await page.wait_for_timeout(2500)

            # Accept cookies if any
            try:
                cookie_btn = await page.query_selector("button#onetrust-accept-btn-handler")
                if cookie_btn and await cookie_btn.is_visible():
                    await cookie_btn.click()
            except Exception:
                pass

            # 2. Wait for conversation cards to mount
            try:
                await page.wait_for_selector('[data-testid*="conversations-list-item-"]', timeout=10000)
            except Exception:
                await page.wait_for_timeout(3000)

            # Extract card info for all conversations
            cards_data = await page.evaluate(r'''() => {
                const cards = [];
                document.querySelectorAll('[data-testid*="conversations-list-item-"]').forEach(card => {
                    const lines = card.innerText.split('\n').map(l => l.trim()).filter(Boolean);
                    const img = card.querySelector('img');
                    const testId = card.getAttribute('data-testid');
                    cards.push({
                        id: testId.replace('conversations-list-item-', ''),
                        lines: lines,
                        image_url: img ? img.src : null
                    });
                });
                return cards;
            }''')

            logger.info(f"📋 Encontradas {len(cards_data)} conversas ativas no OLX.")

            conn = get_connection()
            cursor = conn.cursor()

            for idx, card in enumerate(cards_data, start=1):
                cid = card["id"]
                lines = card["lines"]
                image_url = card.get("image_url")

                seller_name = lines[0] if lines else "Vendedor"
                is_card_inactive = len(lines) > 1 and ("DESATIVADO" in lines[1].upper() or "DESATIVADO" in lines[0].upper())
                if is_card_inactive:
                    ad_title = lines[2] if len(lines) > 2 else ""
                else:
                    ad_title = lines[1] if len(lines) > 1 else ""

                logger.info(f"[{idx}/{len(cards_data)}] A processar: {seller_name} - {ad_title[:35]}...")

                # Click to load messages in right pane
                sel = f'[data-testid="conversations-list-item-{cid}"]'
                btn = await page.query_selector(sel)
                if btn:
                    await btn.click()
                    await page.wait_for_timeout(1000)

                # Extract messages and ad details from the opened thread
                thread_data = await page.evaluate(r'''() => {
                    const messages = [];
                    document.querySelectorAll('[data-testid="sent-message"], [data-testid="received-message"]').forEach((m, idx) => {
                        const isSent = m.getAttribute('data-testid') === 'sent-message';
                        const textEl = m.querySelector('[data-testid="message"]') || m;
                        const timeEl = m.querySelector('[data-testid="message-status-label"]');
                        messages.push({
                            id: idx + 1,
                            sender: isSent ? 'me' : 'seller',
                            text: textEl ? textEl.innerText.trim() : '',
                            time: timeEl ? timeEl.innerText.trim() : ''
                        });
                    });

                    // Check ad price from header if available
                    let price = null;
                    const bodyText = document.body.innerText;
                    const priceMatch = bodyText.match(/(\d{2,5})\s*€/);
                    if (priceMatch) price = parseFloat(priceMatch[1]);

                    return { messages: messages, price: price };
                }''')

                messages = thread_data.get("messages", [])
                ad_price = thread_data.get("price")

                has_reply, is_agreed, agreed_price = detect_deal_status(messages)
                last_msg = messages[-1]["text"] if messages else (lines[2] if len(lines) > 2 else "")
                last_time = messages[-1]["time"] if messages else (lines[-1] if lines else "")

                # Link with laptop in leads.db
                laptop_id = find_matching_laptop_id(None, ad_title, ad_price)

                cursor.execute('''
                    INSERT INTO olx_conversations (
                        id, seller_name, ad_id, ad_title, price, image_url,
                        is_inactive, last_message, last_message_time,
                        has_seller_reply, is_deal_agreed, agreed_price,
                        laptop_id, raw_json, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(id) DO UPDATE SET
                        seller_name = excluded.seller_name,
                        ad_title = excluded.ad_title,
                        price = excluded.price,
                        image_url = excluded.image_url,
                        is_inactive = excluded.is_inactive,
                        last_message = excluded.last_message,
                        last_message_time = excluded.last_message_time,
                        has_seller_reply = excluded.has_seller_reply,
                        is_deal_agreed = excluded.is_deal_agreed,
                        agreed_price = excluded.agreed_price,
                        laptop_id = COALESCE(excluded.laptop_id, olx_conversations.laptop_id),
                        raw_json = excluded.raw_json,
                        updated_at = CURRENT_TIMESTAMP;
                ''', (
                    cid, seller_name, None, ad_title, ad_price, image_url,
                    1 if is_card_inactive else 0, last_msg, last_time,
                    1 if has_reply else 0, 1 if is_agreed else 0, agreed_price,
                    laptop_id, json.dumps(messages)
                ))

                # Save individual messages
                for m in messages:
                    msg_id = f"{cid}_{m['id']}"
                    cursor.execute('''
                        INSERT INTO olx_messages (id, conversation_id, sender_type, text, created_at, raw_json)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(id) DO UPDATE SET
                            text = excluded.text,
                            created_at = excluded.created_at;
                    ''', (msg_id, cid, m["sender"], m["text"], m["time"], json.dumps(m)))

                # If deal agreed, update laptop record and negotiation status in DB!
                if is_agreed and agreed_price and laptop_id:
                    logger.info(f"[NEGOCIO FECHADO] Vendedor '{seller_name}' aceitou {agreed_price}€ no portátil #{laptop_id} ({ad_title})!")
                    cursor.execute('''
                        UPDATE laptops
                        SET price = ?,
                            contact_status = 'agreed',
                            negotiation_status = 'agreed',
                            contact_notes = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?;
                    ''', (agreed_price, f"Proposta aceite por {seller_name} ({agreed_price}€)", laptop_id))

                    cursor.execute('''
                        UPDATE laptop_negotiations
                        SET status = 'agreed',
                            seller_response = ?,
                            responded_at = CURRENT_TIMESTAMP,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE laptop_id = ?;
                    ''', (f"Aceitou {agreed_price}€", laptop_id))

                    agreed_deals.append({
                        "conversation_id": cid,
                        "seller_name": seller_name,
                        "ad_title": ad_title,
                        "agreed_price": agreed_price,
                        "laptop_id": laptop_id
                    })

                synced_conversations.append({
                    "id": cid,
                    "seller_name": seller_name,
                    "ad_title": ad_title,
                    "ad_price": ad_price,
                    "is_inactive": is_card_inactive,
                    "has_seller_reply": has_reply,
                    "is_deal_agreed": is_agreed,
                    "agreed_price": agreed_price,
                    "laptop_id": laptop_id,
                    "messages_count": len(messages)
                })

            conn.commit()
            conn.close()

        finally:
            await context.close()

    logger.info(f"Sincronização concluída: {len(synced_conversations)} conversas processadas, {len(agreed_deals)} negócios aceites!")
    return {
        "success": True,
        "total_conversations": len(synced_conversations),
        "conversations": synced_conversations,
        "agreed_deals": agreed_deals
    }


def main():
    res = asyncio.run(sync_olx_chats(headless=True))
    print("\n" + "=" * 60)
    print("RESULTADO DA SINCRONIZAÇÃO DE CHATS OLX")
    print("=" * 60)
    print(f"Total de Conversas: {res.get('total_conversations', 0)}")
    for c in res.get("conversations", []):
        status_sym = "[ACEITE]" if c.get("is_deal_agreed") else ("[RESPOSTA]" if c.get("has_seller_reply") else "[AGUARDANDO]")
        print(f"- [{status_sym}] {c.get('seller_name')} | {c.get('ad_title')[:35]} | {c.get('messages_count')} msgs")
        if c.get("is_deal_agreed"):
            print(f"    -> Valor Fechado: {c.get('agreed_price')}€ (Portátil #{c.get('laptop_id')})")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
