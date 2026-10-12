"""
24/7 Background Negotiation Response Daemon
Runs every 5 minutes (300 seconds) to check for incoming seller responses,
classify their intent (Agreed, Declined, Counter-Offer),
and immediately update laptop prices when the seller agrees to a 20% discount offer.
"""

import sys
import time
import signal
import logging
from datetime import datetime
from pathlib import Path

from database import get_pending_negotiations, get_laptop_stats
from negotiation import (
    process_incoming_responses_queue,
    INCOMING_RESPONSES_FILE
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [NegotiationDaemon] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("negotiation-daemon")

# 5-minute interval in seconds
CHECK_INTERVAL_SECONDS = 300

running = True

def handle_shutdown(signum, frame):
    global running
    logger.info(f"Received signal {signum}. Stopping Negotiation Daemon...")
    running = False

signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)

def run_check_cycle() -> int:
    """Executes a single check cycle for incoming negotiation responses."""
    cycle_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"--- [Cycle {cycle_time}] Checking negotiation inbox & active deals ---")

    # 1. Sync live OLX messages via Playwright in background
    try:
        import asyncio
        from tools.sync_chats import sync_olx_chats
        logger.info("A sincronizar conversas do OLX via Playwright...")
        sync_res = asyncio.run(sync_olx_chats(headless=True))
        if sync_res.get("success"):
            agreed = sync_res.get("agreed_deals", [])
            if agreed:
                for deal in agreed:
                    logger.info(
                        f"[ACORDO FECHADO NO OLX] Vendedor {deal.get('seller_name')} aceitou "
                        f"{deal.get('agreed_price')}€ no portátil #{deal.get('laptop_id')} ({deal.get('ad_title')})!"
                    )
            else:
                logger.info(f"Chats OLX sincronizados: {sync_res.get('total_conversations', 0)} conversas.")
    except Exception as e:
        logger.warning(f"Erro ao sincronizar chats OLX no daemon: {e}")

    # 2. Check pending negotiations in database
    pending = get_pending_negotiations()
    logger.info(f"Active negotiations in flight: {len(pending)}")

    # 3. Process incoming response queue (data/incoming_negotiation_responses.json)
    processed = process_incoming_responses_queue()
    if processed:
        for item in processed:
            action = item.get("action")
            lid = item.get("laptop_id")
            if action == "price_updated":
                logger.info(
                    f"[ACORDO ACEITE] Portátil #{lid} atualizado! "
                    f"Preço: {item.get('old_price')}€ -> {item.get('new_price')}€ | "
                    f"Novo Value Score: {item.get('value_score')} | "
                    f"Vendedor respondeu: \"{item.get('response')}\""
                )
            elif action == "counter_offer_recorded":
                logger.info(
                    f"[CONTRAPROPOSTA] Portátil #{lid} recebeu contraproposta de {item.get('counter_price')}€"
                )
            elif action == "declined_recorded":
                logger.info(f"[RECUSADA] Portátil #{lid} proposta recusada pelo vendedor")
            else:
                logger.info(f"[MENSAGEM] Portátil #{lid}: {item.get('response')}")
    else:
        logger.info(f"Nenhuma resposta pendente no ficheiro de inbox ({INCOMING_RESPONSES_FILE.name}).")

    return len(processed)

def main():
    logger.info("==================================================")
    logger.info("24/7 Laptop Negotiation Response Daemon started")
    logger.info(f"Check cycle interval: every 5 minutes ({CHECK_INTERVAL_SECONDS}s)")
    logger.info(f"Inbox: {INCOMING_RESPONSES_FILE}")
    logger.info("==================================================")

    # Initial run on boot
    run_check_cycle()

    while running:
        # Sleep in 1-second ticks so PM2 or terminal shutdown is responsive
        sleep_end = time.time() + CHECK_INTERVAL_SECONDS
        while running and time.time() < sleep_end:
            time.sleep(1)

        if not running:
            break

        run_check_cycle()

    logger.info("🛑 Negotiation Daemon terminated gracefully.")

if __name__ == "__main__":
    main()
