"""
Deterministic Negotiation Engine for Second-Hand Laptops (Portugal)
Handles 20% discount calculation, Portuguese bargaining templates,
and response classification (Agreed / Declined / Counter-Offer).
"""

import re
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from database import (
    get_connection,
    create_or_update_negotiation,
    apply_negotiation_agreement,
    record_negotiation_response,
    get_pending_negotiations,
    get_negotiations
)

logger = logging.getLogger("negotiation")
logging.basicConfig(level=logging.INFO)

INCOMING_RESPONSES_FILE = Path(__file__).resolve().parent.parent / "data" / "incoming_negotiation_responses.json"
ARCHIVE_RESPONSES_FILE = Path(__file__).resolve().parent.parent / "data" / "negotiation_responses_archive.json"

NON_NEGOTIABLE_KEYWORDS = [
    "não negociável", "nao negociavel", "preço fixo", "preco fixo",
    "valor fixo", "valor não negociável", "sem margem", "preço não negociável",
    "sem trocas nem negociação", "indiscutível", "fixo e final"
]

AGREED_PHRASES = [
    r"\baceito\b", r"\bconcordo\b", r"\bpode ser\b", r"\bcombinado\b",
    r"\bfechado\b", r"\bfechamos\b", r"\baceite\b", r"\bsim\b",
    r"\bestá bem\b", r"\besta bem\b", r"\bpor mim sim\b", r"\bpor mim ok\b",
    r"\bpode mandar\b", r"\benvio\b", r"\bfaço por esse valor\b",
    r"\bok combinado\b", r"\bok pode ser\b", r"\bsim pode ser\b",
    r"\baceito a proposta\b", r"\baceito a oferta\b", r"\bfechamos negócio\b",
    r"\bpodemos fechar\b", r"\bfecho pelos\b", r"\bvamos a isso\b"
]

DECLINED_PHRASES = [
    r"\bnão aceito\b", r"\bnao aceito\b", r"\bmuito baixo\b", r"\bjá vendi\b",
    r"\bja vendi\b", r"\bnem pensar\b", r"\bpreço fixo\b", r"\bnão tenho interesse\b",
    r"\bmínimo é\b", r"\bsem margem\b", r"\bproposta ridícula\b", r"\bnão obrigado\b",
    r"\bnao obrigado\b"
]

def is_laptop_negotiable(laptop: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Determines if a laptop ad is negotiable:
    - Peer-to-peer marketplaces (OLX, Facebook Marketplace, CustoJusto) are negotiable by default in Portugal.
    - Retail shops (Worten, CeX, PCDiga, FNAC) are non-negotiable fixed price.
    - Listings that explicitly state 'preço fixo' or 'não negociável' are flagged non-negotiable.
    """
    source = (laptop.get("source") or "").strip().lower()
    if source not in ("olx", "facebook", "custojusto"):
        return False, f"Loja fixa ({laptop.get('source')} - preço tabelado não negociável)"

    price = float(laptop.get("price") or 0)
    if price <= 0:
        return False, "Preço zero ou sob consulta"

    title = (laptop.get("title") or "").lower()
    desc = (laptop.get("description") or laptop.get("raw_snippet") or "").lower()
    combined = f"{title} {desc}"

    for kw in NON_NEGOTIABLE_KEYWORDS:
        if kw in combined:
            return False, f"Vendedor declarou expressamente '{kw}' no anúncio"

    return True, "Classificado particular (negociação padrão em Portugal)"

def calculate_negotiated_offer(price: float, discount_pct: float = 0.20) -> float:
    """
    Calculates a 20% discount offer price.
    In Portuguese classifieds, rounding to natural increments (multiples of 5€ if >= 50€)
    makes the bargaining proposal feel realistic, polite, and human.
    """
    discounted = price * (1.0 - discount_pct)
    if discounted >= 50:
        return float(round(discounted / 5.0) * 5)
    return float(round(discounted))

def compose_negotiation_message(
    laptop: Dict[str, Any],
    offer_price: float,
    method: str = "dinheiro_imediato",
    custom_template: Optional[str] = None
) -> str:
    """
    Generates a high-conversion Portuguese negotiation message.
    Supports strategies: dinheiro_imediato, tecnico_hardware, estudante_orcamento, personalizado, ctt, presencial.
    """
    title = laptop.get("title") or "portátil"
    loc = laptop.get("location") or "a sua zona"
    orig_price = float(laptop.get("price") or laptop.get("original_price") or offer_price)
    discount_val = int(round(orig_price - offer_price))

    if custom_template and custom_template.strip():
        return (
            custom_template.replace("{title}", title)
            .replace("{price}", f"{orig_price:.0f}")
            .replace("{offer_price}", f"{offer_price:.0f}")
            .replace("{discount_eur}", f"{discount_val}")
        )

    source = (laptop.get("source") or "").lower()

    if method == "tecnico_hardware":
        return (
            f"Olá! Analisei as especificações do portátil {title}. Tendo em conta o tempo de uso do equipamento "
            f"e o mercado atual de usados, consegue aceitar {offer_price:.0f}€? "
            f"Posso fechar negócio rapidamente. Obrigado!"
        )
    elif method == "estudante_orcamento":
        return (
            f"Olá! Tenho muito interesse no portátil {title} para fins de estudo/trabalho, mas o meu orçamento "
            f"máximo disponível é de {offer_price:.0f}€. Seria viável fechar negócio por esse valor? Obrigado!"
        )
    elif method == "ctt":
        shipping_desc = "via CTT Expresso (à cobrança com verificação de conteúdo)" if "facebook" in source else "via CTT Expresso (via Entregas OLX ou à cobrança com verificação de conteúdo)"
        return (
            f"Olá! Tenho muito interesse no portátil {title}. Como resido na Marinha Grande, "
            f"aceita fechar por {offer_price:.0f}€ com envio {shipping_desc}? "
            f"Assumo eu a totalidade dos portes de envio e fecho o negócio de imediato. Muito obrigado!"
        )
    elif method in ("dinheiro_imediato", "presencial"):
        return (
            f"Olá! Tenho muito interesse no portátil {title}. Consegue fazer por {offer_price:.0f}€ com levantamento "
            f"presencial em mãos e pagamento imediato em dinheiro ou MBWay? Posso deslocar-me a {loc} para testar e fechar. Obrigado!"
        )
    else:
        return (
            f"Olá! Vi o anúncio do portátil {title} por {orig_price:.0f}€. Proponho fechar negócio por {offer_price:.0f}€ "
            f"(-{discount_val}€ de desconto). Tem interesse em fechar por este valor? Obrigado!"
        )

def classify_seller_response(response_text: str) -> Dict[str, Any]:
    """
    Deterministically parses seller response in Portuguese to determine if
    they agreed to the discounted price, made a counter-offer, or declined.
    Ensures negative phrases like 'não aceito' are never confused with 'aceito'.
    """
    text_clean = response_text.lower().strip()

    # Explicit negative prefixes overriding agreement
    negations = [
        r"\bnão aceito\b", r"\bnao aceito\b", r"\bnão concordo\b", r"\bnao concordo\b",
        r"\bnão posso\b", r"\bnao posso\b", r"\bnão dá\b", r"\bnao da\b", r"\bmuito baixo\b",
        r"\bnem pensar\b", r"\bjá vendi\b", r"\bja vendi\b", r"\bpreço fixo\b", r"\bpreco fixo\b",
        r"\bnão tenho interesse\b", r"\bnao tenho interesse\b", r"\bsem margem\b",
        r"\bproposta ridícula\b", r"\bnão obrigado\b", r"\bnao obrigado\b"
    ]

    has_negation = any(re.search(p, text_clean) for p in negations)

    # 1. Check positive agreement first if seller explicitly accepts (e.g. "aceito", "aceito os 280€", "combinado", etc.)
    # Exception: if text contains negative negation ("não aceito", "não dá", etc), it will be caught in step 2.
    if not has_negation:
        for p in AGREED_PHRASES:
            if re.search(p, text_clean):
                return {
                    "status": "agreed",
                    "agreed": True,
                    "counter_offer": False,
                    "declined": False,
                    "confidence": 0.95,
                    "matched_pattern": p
                }

    # 2. Check for counter-offer prices (e.g. "só faço por 420", "só deixo por 450€", "mínimo que faço é 430€", "faço 400€")
    m_counter = re.search(r'(?:só faço|faço por|só deixo|deixo por|mínimo que faço|mínimo é|o mínimo|só vendo por|só aceito|menos de)\s*(\d{2,4})\s*(?:€|eur)?', text_clean)
    if not m_counter and has_negation:
        m_counter = re.search(r'(?:mínimo|menos de|abaixo de)\s*(\d{2,4})\s*(?:€|eur)?', text_clean)
    
    if m_counter:
        try:
            val = float(m_counter.group(1))
            if 50 <= val <= 2500:
                return {
                    "status": "counter_offer",
                    "agreed": False,
                    "counter_offer": True,
                    "counter_price": val,
                    "declined": False,
                    "confidence": 0.88,
                    "matched_price": val
                }
        except ValueError:
            pass

    # 3. If it has explicit rejection and no counter-offer, it is DECLINED
    if has_negation:
        return {
            "status": "declined",
            "agreed": False,
            "counter_offer": False,
            "declined": True,
            "confidence": 0.95
        }

    # 4. Inconclusive / General question from seller
    return {
        "status": "inconclusive",
        "agreed": False,
        "counter_offer": False,
        "declined": False,
        "confidence": 0.40
    }

def process_incoming_responses_queue() -> List[Dict[str, Any]]:
    """
    Checks the incoming responses inbox (data/incoming_negotiation_responses.json).
    If a seller agreed, updates the laptop price in data/leads.db to the discounted price,
    recalculates value_score, and records the agreement.
    Archives processed messages.
    """
    if not INCOMING_RESPONSES_FILE.exists():
        # Create empty template file
        INCOMING_RESPONSES_FILE.parent.mkdir(parents=True, exist_ok=True)
        INCOMING_RESPONSES_FILE.write_text("[]", encoding="utf-8")
        return []

    try:
        raw = INCOMING_RESPONSES_FILE.read_text(encoding="utf-8").strip()
        messages = json.loads(raw) if raw else []
    except Exception as e:
        logger.error(f"Error reading incoming responses file: {e}")
        return []

    if not isinstance(messages, list) or len(messages) == 0:
        return []

    processed = []
    archive = []
    if ARCHIVE_RESPONSES_FILE.exists():
        try:
            archive = json.loads(ARCHIVE_RESPONSES_FILE.read_text(encoding="utf-8"))
        except Exception:
            archive = []

    for msg in messages:
        laptop_id = msg.get("laptop_id")
        text = msg.get("response_text") or msg.get("message") or ""
        if not laptop_id or not text:
            continue

        classification = classify_seller_response(text)
        status = classification["status"]

        if status == "agreed":
            counter_p = classification.get("counter_price")
            result = apply_negotiation_agreement(
                laptop_id=laptop_id,
                agreed_price=counter_p,
                response_text=text
            )
            logger.info(f"🎉 [AGREEMENT APPLIED] Laptop #{laptop_id} price updated to {result.get('agreed_price')}€! New Value Score: ★ {result.get('new_value_score')}")
            processed.append({
                "laptop_id": laptop_id,
                "action": "price_updated",
                "old_price": result.get("original_price"),
                "new_price": result.get("agreed_price"),
                "value_score": result.get("new_value_score"),
                "status": "agreed",
                "response": text
            })
        elif status == "counter_offer":
            counter_p = classification.get("counter_price")
            record_negotiation_response(laptop_id, response_text=text, agreed=False, counter_price=counter_p)
            logger.info(f"🤝 [COUNTER-OFFER] Laptop #{laptop_id} received counter-offer of {counter_p}€")
            processed.append({
                "laptop_id": laptop_id,
                "action": "counter_offer_recorded",
                "counter_price": counter_p,
                "status": "counter_offer",
                "response": text
            })
        elif status == "declined":
            record_negotiation_response(laptop_id, response_text=text, agreed=False)
            logger.info(f"❌ [DECLINED] Laptop #{laptop_id} seller declined offer")
            processed.append({
                "laptop_id": laptop_id,
                "action": "declined_recorded",
                "status": "declined",
                "response": text
            })
        else:
            logger.info(f"💬 [INCONCLUSIVE] Laptop #{laptop_id} received response: '{text}'")
            processed.append({
                "laptop_id": laptop_id,
                "action": "logged_inconclusive",
                "status": "inconclusive",
                "response": text
            })

        # Archive record
        msg["processed_at"] = datetime.now().isoformat()
        msg["classification"] = classification
        archive.append(msg)

    # Clear incoming file and update archive
    INCOMING_RESPONSES_FILE.write_text("[]", encoding="utf-8")
    ARCHIVE_RESPONSES_FILE.write_text(json.dumps(archive, indent=2, ensure_ascii=False), encoding="utf-8")

    return processed

def propose_20pct_discount_all_negotiable(
    min_value_score: float = 7.0,
    limit: int = 30
) -> List[Dict[str, Any]]:
    """
    Finds top negotiable laptops and registers a 20% discount offer in the database.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM laptops 
        WHERE LOWER(source) IN ('olx', 'facebook', 'custojusto')
          AND (contact_status IS NULL OR contact_status IN ('uncontacted', 'none'))
          AND (negotiation_status IS NULL OR negotiation_status IN ('none'))
          AND COALESCE(value_score, 0) >= ?
          AND price > 0
        ORDER BY value_score DESC, spec_score DESC, price ASC
        LIMIT ?
    """, (min_value_score, limit))
    candidates = [dict(r) for r in cursor.fetchall()]
    conn.close()

    created_offers = []
    for laptop in candidates:
        is_neg, reason = is_laptop_negotiable(laptop)
        if not is_neg:
            continue

        orig_price = float(laptop["price"])
        offer_price = calculate_negotiated_offer(orig_price, discount_pct=0.20)
        
        # Prefer CTT shipping message if distance > 35km, else local pickup
        dist = laptop.get("travel_distance_km")
        method = "pickup" if (dist is not None and dist <= 35) else "ctt"
        offer_msg = compose_negotiation_message(laptop, offer_price, method=method)

        res = create_or_update_negotiation(
            laptop_id=laptop["id"],
            offer_price=offer_price,
            original_price=orig_price,
            discount_pct=20.0,
            offer_message=offer_msg
        )

        created_offers.append({
            "laptop_id": laptop["id"],
            "title": laptop["title"],
            "source": laptop["source"],
            "location": laptop["location"],
            "original_price": orig_price,
            "offer_price": offer_price,
            "discount_eur": orig_price - offer_price,
            "offer_message": offer_msg,
            "method": method
        })

    return created_offers
