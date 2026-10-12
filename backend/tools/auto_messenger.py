#!/usr/bin/env python3
"""
tools/auto_messenger.py - Automated Playwright Proposal & Negotiation Dispatcher.

Automates sending tailored -20% purchase proposals to sellers of the top-rated hardware laptops
on OLX.pt (and Facebook Marketplace) using a persistent Playwright browser profile.

Usage:
  # 1. Login session setup (opens visible browser once to login to OLX/Facebook)
  python3 tools/auto_messenger.py --login

  # 2. Check if persistent session is authenticated
  python3 tools/auto_messenger.py --check

  # 3. Preview proposals for Top 10 Best Hardware laptops (Dry Run)
  python3 tools/auto_messenger.py --preview --limit 10

  # 4. Live batch dispatch to Top 10 laptops
  python3 tools/auto_messenger.py --send --limit 10 --yes
"""

import sys
import os
import time
import random
import asyncio
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# Add workspace root to sys.path
import types
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
src_module = types.ModuleType("src")
src_module.__path__ = [str(BASE_DIR)]
sys.modules["src"] = src_module

from playwright.async_api import async_playwright, BrowserContext, Page
from src.database import (
    get_connection,
    create_or_update_negotiation,
    get_laptop_by_id,
    record_negotiation_response
)
from src.negotiation import (
    calculate_negotiated_offer,
    compose_negotiation_message,
    is_laptop_negotiable
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("auto_messenger")

PROFILE_DIR = BASE_DIR / "data" / "playwright_profile"
SCREENSHOTS_DIR = BASE_DIR / "data" / "negotiation_screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
PROFILE_DIR.mkdir(parents=True, exist_ok=True)


def get_top_hardware_targets(
    sort_by: str = "hardware",
    limit: Optional[int] = 10,
    min_spec: float = 6.0,
    min_value: float = 0.0,
    platform: str = "all"
) -> List[Dict[str, Any]]:
    """
    Retrieves the uncontacted laptops with the highest hardware or value scores.
    If limit is None or <= 0, returns all eligible targets.
    """
    conn = get_connection()
    cursor = conn.cursor()

    order_clause = "spec_score DESC, value_score DESC" if sort_by == "hardware" else "value_score DESC, spec_score DESC"
    
    platform_filter = "LOWER(source) IN ('olx', 'facebook', 'custojusto')"
    if platform.lower() == "olx":
        platform_filter = "LOWER(source) = 'olx'"
    elif platform.lower() == "facebook":
        platform_filter = "LOWER(source) = 'facebook'"

    limit_sql = f"LIMIT {int(limit)}" if (limit is not None and limit > 0) else "LIMIT -1"

    query = f"""
        SELECT * FROM laptops
        WHERE {platform_filter}
          AND (contact_status IS NULL OR contact_status IN ('uncontacted', 'none'))
          AND (negotiation_status IS NULL OR negotiation_status IN ('none'))
          AND id NOT IN (SELECT COALESCE(laptop_id, -1) FROM olx_conversations)
          AND id NOT IN (SELECT laptop_id FROM laptop_negotiations WHERE status IN ('pending', 'agreed', 'counter_offer'))
          AND COALESCE(spec_score, 0) >= ?
          AND COALESCE(value_score, 0) >= ?
          AND price > 0
          AND url IS NOT NULL
          AND url != ''
        ORDER BY {order_clause}
        {limit_sql}
    """
    cursor.execute(query, (min_spec, min_value))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    from src.database import update_laptop_contact

    targets = []
    for laptop in rows:
        is_neg, reason = is_laptop_negotiable(laptop)
        if not is_neg:
            update_laptop_contact(laptop["id"], contact_status="non_negotiable", contact_notes=reason)
            continue

        orig_price = float(laptop.get("price") or 0)
        offer_price = calculate_negotiated_offer(orig_price, discount_pct=0.20)
        dist = laptop.get("travel_distance_km")
        method = "pickup" if (dist is not None and dist <= 35) else "ctt"
        offer_msg = compose_negotiation_message(laptop, offer_price, method=method)

        targets.append({
            "laptop": laptop,
            "orig_price": orig_price,
            "offer_price": offer_price,
            "discount_eur": orig_price - offer_price,
            "method": method,
            "offer_message": offer_msg
        })

    return targets


async def launch_login_session():
    """
    Launches a visible Chromium instance with the persistent profile.
    Allows the user to log in to OLX.pt and Facebook Marketplace.
    """
    print("\n" + "=" * 70)
    print(" SESSÃO DE AUTENTICAÇÃO PLAYWRIGHT (OLX & FACEBOOK)")
    print("=" * 70)
    print(f"Diretoria do Perfil: {PROFILE_DIR}")
    print("\n1. Vamos abrir uma janela do Chromium no teu ecrã.")
    print("2. Faz login na tua conta do OLX (e/ou Facebook se quiseres).")
    print("3. Quando tiveres a sessão iniciada com sucesso em ambas as plataformas,")
    print("   volta a este terminal e pressiona [ENTER] para guardar a sessão e fechar.\n")

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            viewport={"width": 1280, "height": 850},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ]
        )

        page_olx = context.pages[0] if context.pages else await context.new_page()
        print(" A abrir OLX...")
        await page_olx.goto("https://www.olx.pt/d/minha-conta/", wait_until="domcontentloaded")

        page_fb = await context.new_page()
        print(" A abrir Facebook Marketplace...")
        await page_fb.goto("https://www.facebook.com/marketplace/", wait_until="domcontentloaded")

        done_flag = BASE_DIR / "data" / "finish_login.flag"
        if done_flag.exists():
            try:
                done_flag.unlink()
            except Exception:
                pass

        print("\n A janela do browser já está aberta no teu ecrã!")
        print(" Faz login no OLX (e/ou Facebook).")
        print(" Quando terminares, podes simplesmente FECHAR A JANELA DO BROWSER (no X do canto superior)")
        print("   ou executar: touch data/finish_login.flag\n")

        # Keep browser open until user closes it or creates the flag
        while True:
            try:
                if not context.pages or all(p.is_closed() for p in context.pages):
                    print(" Janela do browser fechada pelo utilizador. A finalizar...")
                    break
            except Exception:
                break

            if done_flag.exists():
                print(" Sinal de conclusão recebido. A fechar browser...")
                try:
                    done_flag.unlink()
                except Exception:
                    pass
                break

            await asyncio.sleep(1)

        print("\n A consolidar cookies e tokens no perfil persistente...")
        try:
            await context.close()
        except Exception:
            pass
        print(" Sessão guardada com sucesso no perfil persistente!\n")


async def check_session_status() -> Dict[str, Any]:
    """
    Checks if cookies or active sessions exist in the profile for OLX and Facebook.
    """
    if not PROFILE_DIR.exists() or not any(PROFILE_DIR.iterdir()):
        return {
            "profile_exists": False,
            "olx_logged_in": False,
            "facebook_logged_in": False,
            "message": "Nenhum perfil do Playwright encontrado. Executa com --login para iniciar sessão."
        }

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )

        page = context.pages[0] if context.pages else await context.new_page()
        
        # Check OLX
        olx_ok = False
        try:
            await page.goto("https://www.olx.pt/d/mensagens/", timeout=15000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
            url_now = page.url.lower()
            olx_ok = "login" not in url_now and "mensagens" in url_now
        except Exception as e:
            logger.warning(f"Erro ao verificar OLX: {e}")

        # Check Facebook
        fb_ok = False
        try:
            await page.goto("https://www.facebook.com/marketplace/", timeout=15000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
            url_now = page.url.lower()
            fb_ok = "login" not in url_now and "checkpoint" not in url_now
        except Exception as e:
            logger.warning(f"Erro ao verificar Facebook: {e}")

        await context.close()

        return {
            "profile_exists": True,
            "olx_logged_in": olx_ok,
            "facebook_logged_in": fb_ok,
            "message": "Sessão verificada."
        }


async def send_olx_proposal(
    page: Page,
    laptop: Dict[str, Any],
    offer_msg: str,
    dry_run: bool = False
) -> Tuple[bool, str]:
    """
    Navigates to an OLX ad, opens the chat interface, pastes the offer message and safely submits it.
    Includes fallbacks for inactive/expired ads and validates that the message was truly sent.
    """
    url = laptop["url"]
    laptop_id = laptop["id"]
    title = laptop.get("title", "")[:40]

    logger.info(f"A abrir anúncio OLX #{laptop_id} ({title}): {url}")
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(random.uniform(1500, 2500))

        # 1. Fallback: Check if ad is expired, ended or not found
        expired_patterns = [
            'div:has-text("anúncio não está ativo")',
            'div:has-text("terminado")',
            'div:has-text("Anúncio desativado")',
            'div:has-text("não se encontra disponível")',
            'div:has-text("Este anúncio já não está disponível")',
            'div:has-text("Ups! Parece que esta página não existe")'
        ]
        for pattern in expired_patterns:
            expired_elem = await page.query_selector(pattern)
            if expired_elem and await expired_elem.is_visible():
                from src.database import update_laptop_contact
                update_laptop_contact(laptop_id, contact_status="expired", contact_notes="Anúncio expirado/desativado no OLX")
                logger.warning(f" Anúncio #{laptop_id} está expirado/desativado. Marcado no banco de dados.")
                return False, "Anúncio expirado ou desativado no OLX."

        # Accept cookie banner if present
        try:
            cookie_btn = await page.query_selector("button#onetrust-accept-btn-handler")
            if cookie_btn and await cookie_btn.is_visible():
                await cookie_btn.click()
                await page.wait_for_timeout(800)
        except Exception:
            pass

        # 2. Look for chat button
        chat_btn = await page.query_selector(
            'button[data-testid="chat-button"], button:has-text("Enviar mensagem"), button[data-testid="ad-contact-message-button"]'
        )
        if not chat_btn:
            # Re-verify if ad is closed
            is_ended = await page.query_selector('div:has-text("anúncio não está ativo"), div:has-text("terminado")')
            if is_ended:
                from src.database import update_laptop_contact
                update_laptop_contact(laptop_id, contact_status="expired", contact_notes="Anúncio expirado no OLX")
                return False, "Anúncio expirado ou já não está ativo no OLX."
            return False, "Botão de chat 'Enviar mensagem' não encontrado na página."

        # Click chat button to open drawer / modal
        await chat_btn.click()
        await page.wait_for_timeout(random.uniform(2000, 3000))

        # Check if redirected to login
        if "login" in page.url.lower():
            return False, "Redirecionado para login do OLX. Inicia sessão com: python3 tools/auto_messenger.py --login"

        # 3. Locate form containing the chat textarea
        form = await page.wait_for_selector('form:has(textarea)', timeout=10000)
        if not form:
            return False, "Formulário de chat não encontrado após abrir conversa."

        textarea = await form.query_selector('textarea')
        if not textarea:
            return False, "Caixa de texto para escrever a mensagem não apareceu."

        # Safeguard: Check if we already have a previous sent message in this chat thread
        existing_sent = await page.query_selector_all('[data-testid="sent-message"]')
        if existing_sent and len(existing_sent) > 0:
            logger.warning(f" Já existe mensagem enviada para #{laptop_id} neste chat! A abortar envio para evitar duplicação.")
            from src.database import update_laptop_contact
            update_laptop_contact(laptop_id, contact_status="offered", contact_notes="Conversa já existente no OLX")
            return False, "Duplicação evitada: já existiam mensagens nesta conversa."

        # Type message
        await textarea.click()
        await page.wait_for_timeout(400)
        await textarea.fill(offer_msg)
        await page.wait_for_timeout(800)

        # Find submit button SCOPED inside this chat form (avoids header search button)
        send_btn = await form.query_selector(
            'button[aria-label="Submit message"], button[type="submit"]'
        )
        if not send_btn:
            return False, "Botão de envio da mensagem não encontrado dentro do formulário de chat."

        # Wait for submit button to be enabled (it is disabled when textarea is empty)
        try:
            await page.wait_for_function('btn => btn && !btn.disabled', send_btn, timeout=5000)
        except Exception:
            # Fallback: trigger input event via keyboard
            await textarea.press("End")
            await page.keyboard.type(" ")
            await textarea.press("Backspace")
            await page.wait_for_timeout(500)

        # Screenshot for audit / dry-run confirmation
        shot_path = SCREENSHOTS_DIR / f"olx_{laptop_id}_{'dryrun' if dry_run else 'sent'}.png"
        await page.screenshot(path=str(shot_path))

        if dry_run:
            logger.info(f" [DRY RUN] Mensagem preenchida com sucesso para #{laptop_id}! Captura guardada em {shot_path.name}")
            return True, f"Dry-run OK (captura {shot_path.name})"

        # 4. SUBMIT AND VERIFY
        logger.info(f" A submeter proposta para #{laptop_id}...")
        await send_btn.click()

        # Verification loop: check if textarea clears or sent bubble appears
        sent_confirmed = False
        for _ in range(8):
            await page.wait_for_timeout(600)
            try:
                val = await textarea.input_value()
                if val.strip() == "":
                    sent_confirmed = True
                    break
            except Exception:
                # Textarea might be unmounted/re-rendered on successful submit
                sent_confirmed = True
                break

            # Check if sent bubble appeared
            sent_bubble = await page.query_selector('[data-testid="sent-message"]')
            if sent_bubble:
                sent_confirmed = True
                break

        if not sent_confirmed:
            # Secondary attempt: form requestSubmit
            logger.warning(f"Tentativa secundária de envio via form.requestSubmit() para #{laptop_id}...")
            try:
                await form.evaluate("f => f.requestSubmit()")
                await page.wait_for_timeout(2000)
                val = await textarea.input_value()
                if val.strip() == "":
                    sent_confirmed = True
            except Exception:
                pass

        # Post-send screenshot
        shot_path_confirmed = SCREENSHOTS_DIR / f"olx_{laptop_id}_sent_confirmed.png"
        await page.screenshot(path=str(shot_path_confirmed))

        if sent_confirmed:
            logger.info(f" Proposta enviada e CONFIRMADA para #{laptop_id} ({title})!")
            return True, "Mensagem enviada e confirmada."
        else:
            return False, "O texto permaneceu no textarea após clique de envio. Possível restrição de envio."

    except Exception as e:
        logger.error(f" Erro ao enviar proposta no anúncio #{laptop_id}: {e}")
        return False, str(e)


async def send_facebook_proposal(
    page: Page,
    laptop: Dict[str, Any],
    offer_msg: str,
    dry_run: bool = False
) -> Tuple[bool, str]:
    """
    Navigates to a Facebook Marketplace item, opens the message dialog,
    pastes the offer message and submits it via Messenger.
    """
    url = laptop["url"]
    laptop_id = laptop["id"]
    title = laptop.get("title", "")[:40]

    logger.info(f"A abrir anúncio Facebook #{laptop_id} ({title}): {url}")
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(random.uniform(2000, 3000))

        # 1. Fallback: Check for expired, sold or unavailable ad
        expired_patterns = [
            'div:has-text("Esta página não está disponível")',
            'div:has-text("Este anúncio já não está disponível")',
            'div:has-text("marcado como vendido")',
            'div:has-text("Vendido")'
        ]
        for pattern in expired_patterns:
            expired_elem = await page.query_selector(pattern)
            if expired_elem and await expired_elem.is_visible():
                from src.database import update_laptop_contact
                update_laptop_contact(laptop_id, contact_status="expired", contact_notes="Anúncio expirado/vendido no Facebook")
                logger.warning(f" Anúncio #{laptop_id} está expirado/vendido no Facebook. Marcado no banco de dados.")
                return False, "Anúncio expirado ou vendido no Facebook."

        # Check if redirected to login / security checkpoint
        url_lower = page.url.lower()
        if "login" in url_lower or "checkpoint" in url_lower:
            return False, "Sessão do Facebook expirou ou requer verificação de segurança."

        # 2. Find visible 'Mensagem' button
        buttons = await page.query_selector_all('div[role="button"]')
        msg_btn = None
        for b in buttons:
            txt = (await b.inner_text()).strip()
            if "Mensagem" in txt and await b.is_visible():
                msg_btn = b
                break

        if not msg_btn:
            # Check if seller has already been contacted (e.g. 'Ver no Messenger')
            for b in buttons:
                txt = (await b.inner_text()).strip()
                if "Messenger" in txt and await b.is_visible():
                    from src.database import update_laptop_contact
                    update_laptop_contact(laptop_id, contact_status="offered", contact_notes="Conversa já existente no Messenger")
                    return False, "Duplicação evitada: conversa já existente no Messenger."
            return False, "Botão 'Mensagem' não encontrado na página do Facebook."

        # Click Mensagem button
        await msg_btn.click()
        await page.wait_for_timeout(random.uniform(2000, 3000))

        # 3. Locate dialog modal
        dialog = await page.wait_for_selector('div[role="dialog"]', timeout=8000)
        if not dialog:
            return False, "Diálogo de mensagem do Facebook não abriu após clicar em Mensagem."

        # Locate textarea inside dialog
        textarea = await dialog.query_selector('textarea')
        if not textarea or not await textarea.is_visible():
            return False, "Caixa de texto (textarea) não visível no diálogo do Facebook."

        # Type offer message
        await textarea.click()
        await page.wait_for_timeout(400)
        await textarea.fill(offer_msg)
        await page.wait_for_timeout(800)

        # Locate Send button inside dialog
        send_btn = await dialog.query_selector('div[role="button"]:has-text("Enviar mensagem"), button:has-text("Enviar mensagem")')
        if not send_btn:
            send_btn = await dialog.query_selector('div[aria-label="Enviar mensagem"]')

        if not send_btn:
            return False, "Botão 'Enviar mensagem' não encontrado no diálogo do Facebook."

        # Screenshot for dry-run or audit
        shot_path = SCREENSHOTS_DIR / f"fb_{laptop_id}_{'dryrun' if dry_run else 'sent'}.png"
        await page.screenshot(path=str(shot_path))

        if dry_run:
            logger.info(f" [DRY RUN] Mensagem Facebook preenchida com sucesso para #{laptop_id}! Captura guardada em {shot_path.name}")
            cancel_btn = await dialog.query_selector('div[role="button"]:has-text("Cancelar"), [aria-label="Fechar"]')
            if cancel_btn and await cancel_btn.is_visible():
                await cancel_btn.click()
            return True, f"Dry-run OK (captura {shot_path.name})"

        # 4. SUBMIT AND VERIFY
        logger.info(f" A submeter proposta Facebook para #{laptop_id}...")
        await send_btn.click()

        # Verification loop: check if dialog closes or button enters sent state
        sent_confirmed = False
        for _ in range(10):
            await page.wait_for_timeout(800)
            try:
                if not await dialog.is_visible():
                    sent_confirmed = True
                    break
            except Exception:
                sent_confirmed = True
                break

        # Post-send screenshot
        shot_path_confirmed = SCREENSHOTS_DIR / f"fb_{laptop_id}_sent_confirmed.png"
        await page.screenshot(path=str(shot_path_confirmed))

        if sent_confirmed:
            logger.info(f" Proposta enviada e CONFIRMADA para Facebook #{laptop_id} ({title})!")
            from src.database import update_laptop_contact
            update_laptop_contact(laptop_id, contact_status="offered", contact_notes="Proposta -20% enviada via Facebook Messenger")
            return True, "Mensagem enviada e confirmada no Facebook."
        else:
            return False, "O diálogo permaneceu aberto após clique de envio no Facebook."

    except Exception as e:
        logger.error(f" Erro ao enviar proposta no Facebook #{laptop_id}: {e}")
        return False, str(e)


async def run_batch_dispatch(
    targets: List[Dict[str, Any]],
    dry_run: bool = False,
    headless: bool = False,
    delay_min: int = 10,
    delay_max: int = 18
):
    """
    Executes automated proposal sending over the provided list of targets.
    """
    print("\n" + "=" * 70)
    print(f" DISPARO DE PROPOSTAS AUTOMÁTICAS ({'MODO DRY-RUN' if dry_run else 'MODO REAL'})")
    print(f"Total de Portáteis Alvo: {len(targets)}")
    print(f"Modo Headless: {'Sim (em background)' if headless else 'Não (janela visível)'}")
    print("=" * 70)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=headless,
            viewport={"width": 1280, "height": 850},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ]
        )

        page = context.pages[0] if context.pages else await context.new_page()

        success_count = 0
        failed_count = 0

        for idx, item in enumerate(targets, start=1):
            laptop = item["laptop"]
            laptop_id = laptop["id"]
            orig_p = item["orig_p"] if "orig_p" in item else item["orig_price"]
            offer_p = item["offer_price"]
            msg = item["offer_message"]

            print(f"\n[{idx}/{len(targets)}] Processando #{laptop_id}: {laptop.get('title')[:45]}...")
            print(f"    Preço: {orig_p:.0f}€  Oferta -20%: {offer_p:.0f}€ ({item['method'].upper()})")

            source = (laptop.get("source") or "").lower()
            if source == "olx":
                success, reason = await send_olx_proposal(page, laptop, msg, dry_run=dry_run)
            elif source == "facebook":
                success, reason = await send_facebook_proposal(page, laptop, msg, dry_run=dry_run)
            else:
                print(f"     Envio direto para '{source}' ainda não automatizado via Playwright. A saltar...")
                continue

            if success:
                success_count += 1
                if not dry_run:
                    # Update database records
                    create_or_update_negotiation(
                        laptop_id=laptop_id,
                        offer_price=offer_p,
                        original_price=orig_p,
                        discount_pct=20.0,
                        offer_message=msg
                    )
            else:
                failed_count += 1
                print(f"     Falha: {reason}")

            # Human-like delay between messages (if not last item)
            if idx < len(targets):
                wait_secs = random.randint(delay_min, delay_max)
                print(f"    ⏳ Pausa de segurança anti-bot: a aguardar {wait_secs} segundos...")
                for s in range(wait_secs, 0, -1):
                    await asyncio.sleep(1)

        await context.close()

    print("\n" + "=" * 70)
    print(" RELATÓRIO FINAL DE DISPARO")
    print(f"Sucessos: {success_count} / {len(targets)}")
    print(f"Falhas:   {failed_count} / {len(targets)}")
    print("=" * 70 + "\n")


NEW_DEALS_FLAG = BASE_DIR / "data" / "new_deals.flag"


async def run_continuous_dispatch(
    sort_by: str = "hardware",
    min_spec: float = 0.0,
    min_value: float = 0.0,
    platform: str = "all",
    dry_run: bool = False,
    headless: bool = True,
    delay_min: int = 10,
    delay_max: int = 18,
    batch_size: int = 10,
    empty_sleep_sec: int = 1200,
    continuous: bool = True
):
    """
    Continuously loops through uncontacted targets without artificial limits.
    Dispatches tailored -20% proposals with safe human delays (10-18s).
    When all available targets are contacted:
      - If continuous is False: completes execution.
      - If continuous is True: closes browser to free RAM, sleeps for 20 minutes,
        AND listens for 'new_deals.flag' from scraper-daemon to wake up instantly!
    """
    print("\n" + "=" * 70)
    print(f" DISPARO CONTÍNUO DE PROPOSTAS ({'MODO DRY-RUN' if dry_run else 'MODO REAL'})")
    print(f"Estratégia: {'Contínuo 24/7 (em loop)' if continuous else 'Até esgotar portáteis elegíveis'}")
    print(f"Critérios: min_spec={min_spec}, platform={platform}, sort={sort_by}")
    print(f"Modo Headless: {'Sim (em background)' if headless else 'Não (janela visível)'}")
    print("=" * 70 + "\n")

    stop_requested = False
    import signal
    from src.browser_lock import BrowserLock
    loop = asyncio.get_running_loop()

    def on_stop():
        nonlocal stop_requested
        logger.info(" Sinal de paragem recebido. A concluir a mensagem em curso e a fechar com segurança...")
        stop_requested = True

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, on_stop)
        except NotImplementedError:
            pass

    total_sent = 0
    total_failed = 0
    total_duplicate_skipped = 0
    cycle_count = 0

    while not stop_requested:
        # Check if there are any targets available
        initial_targets = get_top_hardware_targets(
            sort_by=sort_by,
            limit=batch_size,
            min_spec=min_spec,
            min_value=min_value,
            platform=platform
        )

        if not initial_targets:
            if not continuous:
                logger.info(" Não existem mais portáteis elegíveis para envio. Tarefa concluída!")
                break

            logger.info(
                f" Nenhum portátil elegível por contactar de momento. "
                f"A aguardar {empty_sleep_sec // 60} minutos (ou até o scraper-daemon capturar novos negócios)..."
            )
            # Sleep in 1s increments, wake up instantly if scraper finds new deals
            woke_early = False
            for _ in range(empty_sleep_sec):
                if stop_requested:
                    break
                if NEW_DEALS_FLAG.exists():
                    logger.info(" [Sincronização Ativa] O scraper-daemon capturou novos portáteis! A acordar imediatamente...")
                    try:
                        NEW_DEALS_FLAG.unlink()
                    except Exception:
                        pass
                    woke_early = True
                    break
                await asyncio.sleep(1)

            if not woke_early and not stop_requested:
                logger.info("⏰ Fim da pausa de 20 minutos. A verificar novos negócios na base de dados...")
            continue

        # Targets exist: acquire BrowserLock and launch Playwright session
        async with BrowserLock(timeout=60):
            async with async_playwright() as p:
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=str(PROFILE_DIR),
                    headless=headless,
                    viewport={"width": 1280, "height": 850},
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox"
                    ]
                )

                page = context.pages[0] if context.pages else await context.new_page()
                consecutive_navs = 0

                # Process batches while targets remain
                while not stop_requested:
                    targets = get_top_hardware_targets(
                        sort_by=sort_by,
                        limit=batch_size,
                        min_spec=min_spec,
                        min_value=min_value,
                        platform=platform
                    )

                    if not targets:
                        logger.info(" Todos os portáteis disponíveis nesta ronda foram processados com sucesso.")
                        break

                    cycle_count += 1
                    logger.info(f"\n [Lote #{cycle_count}] A processar {len(targets)} portáteis elegíveis...")

                    for idx, item in enumerate(targets, start=1):
                        if stop_requested:
                            break

                        consecutive_navs += 1
                        if consecutive_navs > 15:
                            try:
                                await page.close()
                            except Exception:
                                pass
                            page = await context.new_page()
                            consecutive_navs = 0

                        laptop = item["laptop"]
                        laptop_id = laptop["id"]
                        orig_p = item["orig_p"] if "orig_p" in item else item["orig_price"]
                        offer_p = item["offer_price"]
                        msg = item["offer_message"]

                        logger.info(f"[{idx}/{len(targets)}] A processar #{laptop_id}: {laptop.get('title')[:45]}...")
                        logger.info(f"    Preço: {orig_p:.0f}€  Oferta -20%: {offer_p:.0f}€ ({item['method'].upper()})")

                        source = (laptop.get("source") or "").lower()
                        if source == "olx":
                            success, reason = await send_olx_proposal(page, laptop, msg, dry_run=dry_run)
                        elif source == "facebook":
                            success, reason = await send_facebook_proposal(page, laptop, msg, dry_run=dry_run)
                        else:
                            logger.warning(f"     Envio direto para '{source}' ainda não automatizado via Playwright. A saltar...")
                            continue

                        if success:
                            total_sent += 1
                            if not dry_run:
                                create_or_update_negotiation(
                                    laptop_id=laptop_id,
                                    offer_price=offer_p,
                                    original_price=orig_p,
                                    discount_pct=20.0,
                                    offer_message=msg
                                )
                        else:
                            if "Duplicação evitada" in reason:
                                total_duplicate_skipped += 1
                            else:
                                total_failed += 1
                            logger.warning(f"     Resultado: {reason}")

                        if (idx < len(targets) or True) and not stop_requested:
                            wait_secs = random.randint(delay_min, delay_max)
                            logger.info(f"    ⏳ Pausa anti-bot natural: {wait_secs} segundos...")
                            for _ in range(wait_secs):
                                if stop_requested:
                                    break
                                await asyncio.sleep(1)

                try:
                    await context.close()
                except Exception:
                    pass

    print("\n" + "=" * 70)
    print(" RELATÓRIO DO DISPARADOR CONTÍNUO")
    print(f"Total Propostas Enviadas: {total_sent}")
    print(f"Total Falhas / Expirados:  {total_failed}")
    print(f"Duplicações Evitadas:     {total_duplicate_skipped}")
    print("=" * 70 + "\n")


def print_preview_table(targets: List[Dict[str, Any]]):
    """
    Renders a formatted overview table of the target laptops and proposed offers.
    """
    print("\n" + "=" * 80)
    print(f" PREVIEW DOS MELHORES PORTÁTEIS DE HARDWARE SELECIONADOS ({len(targets)} negócios)")
    print("=" * 80)
    print(f"{'ID':<6} | {'Fonte':<8} | {'Original':<9} | {'Oferta -20%':<11} | {'Spec':<5} | {'Val':<5} | {'Título'}")
    print("-" * 80)

    for item in targets:
        lap = item["laptop"]
        spec = lap.get("spec_score") or 0.0
        val = lap.get("value_score") or 0.0
        print(
            f"#{lap['id']:<5} | {lap.get('source', ''):<8} | {item['orig_price']:>6.0f} €   | {item['offer_price']:>7.0f} €    | {spec:>4.1f} | {val:>4.1f} | {lap.get('title', '')[:35]}"
        )

    print("=" * 80)
    print(" Todas as ofertas incluem -20% de desconto, com assunção de portes CTT ou recolha presencial.")
    print("=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Automated Playwright Proposal & Negotiation Tool")
    parser.add_argument("--login", action="store_true", help="Launch visible browser to login to OLX and Facebook")
    parser.add_argument("--check", action="store_true", help="Check if persistent session is authenticated")
    parser.add_argument("--preview", action="store_true", help="Preview list of top hardware targets without sending")
    parser.add_argument("--send", action="store_true", help="Run proposal sending via Playwright")
    parser.add_argument("--continuous", action="store_true", help="Run continuously in a loop without stopping until stopped")
    parser.add_argument("--all", action="store_true", help="Run across all eligible laptops until exhausted")
    parser.add_argument("--dry-run", action="store_true", help="Simulate message filling and take screenshots without clicking send")
    parser.add_argument("--limit", type=int, default=10, help="Number of laptops to target per batch (default: 10)")
    parser.add_argument("--min-spec", type=float, default=0.0, help="Minimum hardware spec score (default: 0.0 for all eligible laptops)")
    parser.add_argument("--empty-sleep", type=int, default=1200, help="Seconds to sleep when queue is empty (default: 1200 = 20 min)")
    parser.add_argument("--sort", choices=["hardware", "value"], default="hardware", help="Sorting strategy")
    parser.add_argument("--platform", choices=["olx", "facebook", "all"], default="all", help="Platform to target (default: all)")
    parser.add_argument("--headless", action="store_true", help="Run browser in background headless mode")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt before sending")

    args = parser.parse_args()

    if args.login:
        asyncio.run(launch_login_session())
        return

    if args.check:
        print(" A verificar estado da sessão do Playwright...")
        res = asyncio.run(check_session_status())
        print(f"Perfil Existe: {'Sim' if res['profile_exists'] else 'Não'}")
        print(f"OLX Autenticado: {'Sim' if res['olx_logged_in'] else 'Não'}")
        print(f"Facebook Autenticado: {'Sim' if res['facebook_logged_in'] else 'Não'}")
        print(f"Mensagem: {res['message']}")
        return

    # Continuous or All Mode
    if args.continuous or args.all:
        if not args.yes and not args.dry_run:
            mode_name = "CONTÍNUO (24/7)" if args.continuous else "ATÉ ESGOTAR BASE DE DADOS"
            confirm = input(f" Desejas iniciar o modo {mode_name} para portáteis (min_spec={args.min_spec})? [s/N]: ").strip().lower()
            if confirm not in ("s", "sim", "y", "yes"):
                print("Operação cancelada pelo utilizador.")
                return

        asyncio.run(run_continuous_dispatch(
            sort_by=args.sort,
            min_spec=args.min_spec,
            platform=args.platform,
            dry_run=args.dry_run,
            headless=args.headless,
            batch_size=args.limit,
            empty_sleep_sec=args.empty_sleep,
            continuous=args.continuous
        ))
        return

    # Standard Batch Mode
    targets = get_top_hardware_targets(
        sort_by=args.sort,
        limit=args.limit,
        min_spec=args.min_spec,
        platform=args.platform
    )

    if not targets:
        print(" Nenhum portátil elegível encontrado para os critérios selecionados.")
        return

    print_preview_table(targets)

    if args.preview and not args.send:
        print("Para disparar, executa com: python3 tools/auto_messenger.py --send --limit 10")
        return

    if args.send:
        if not args.yes and not args.dry_run:
            confirm = input(f" Desejas disparar propostas reais para estes {len(targets)} portáteis? [s/N]: ").strip().lower()
            if confirm not in ("s", "sim", "y", "yes"):
                print("Operação cancelada pelo utilizador.")
                return

        asyncio.run(run_batch_dispatch(targets, dry_run=args.dry_run, headless=args.headless))


if __name__ == "__main__":
    main()
