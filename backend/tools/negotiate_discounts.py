#!/usr/bin/env python3
"""
CLI Tool for Bargaining & Negotiation (20% Discount) on Second-Hand Laptops.
Allows generating 20% discount offers, simulating seller agreements,
and checking the incoming response inbox.
"""

import sys
import json
import argparse
from pathlib import Path

# Add project root to sys.path
import types
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
src_module = types.ModuleType("src")
src_module.__path__ = [str(PROJECT_ROOT)]
sys.modules["src"] = src_module

from src.database import (
    get_connection,
    get_laptop_by_id,
    create_or_update_negotiation,
    apply_negotiation_agreement,
    get_pending_negotiations,
    get_negotiations
)
from src.negotiation import (
    is_laptop_negotiable,
    calculate_negotiated_offer,
    compose_negotiation_message,
    classify_seller_response,
    process_incoming_responses_queue,
    propose_20pct_discount_all_negotiable,
    INCOMING_RESPONSES_FILE
)

def list_negotiable_laptops(limit: int = 20, min_value: float = 7.0):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, title, price, original_price, source, location, value_score, spec_score, contact_status
        FROM laptops
        WHERE LOWER(source) IN ('olx', 'facebook', 'custojusto')
          AND COALESCE(value_score, 0) >= ?
          AND price > 0
        ORDER BY value_score DESC, spec_score DESC, price ASC
        LIMIT ?
    """, (min_value, limit))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    print("\n" + "=" * 95)
    print(f" TOP {len(rows)} PORTÁTEIS NEGOCIÁVEIS (Particulares OLX / Facebook | Score >= {min_value})")
    print("=" * 95)
    print(f"{'ID':<5} | {'PREÇO ATUAL':<12} | {'-20% OFERTA':<12} | {'POUPANÇA':<10} | {'VALOR':<8} | {'PLATAFORMA':<10} | {'TÍTULO'}")
    print("-" * 95)

    for r in rows:
        is_neg, _ = is_laptop_negotiable(r)
        if not is_neg:
            continue
        cur_p = float(r["price"])
        offer_p = calculate_negotiated_offer(cur_p, 0.20)
        saving = cur_p - offer_p
        val = r.get("value_score") or 0.0
        src = r.get("source") or "OLX"
        title = (r.get("title") or "")[:35]
        status = f" [{r['contact_status']}]" if r.get("contact_status") and r["contact_status"] != 'uncontacted' else ""

        print(f"#{r['id']:<4} | {cur_p:>6.0f} €      | {offer_p:>6.0f} €      | {saving:>5.0f} €    |  {val:<4.1f} | {src:<10} | {title}{status}")
    print("=" * 95 + "\n")

def apply_offers_for_top(limit: int = 10, discount_pct: float = 0.20):
    print(f"\n A gerar e registar propostas com {int(discount_pct*100)}% de desconto para o Top {limit} negócios...")
    created = propose_20pct_discount_all_negotiable(min_value_score=7.5, limit=limit)
    print(f" Criadas {len(created)} propostas de negociação com {int(discount_pct*100)}% de desconto:")
    for o in created:
        print(f"  • Portátil #{o['laptop_id']} ({o['source']}): {o['original_price']:.0f}€  {o['offer_price']:.0f}€ (-{o['discount_eur']:.0f}€)")
        print(f"     Mensagem: \"{o['offer_message'][:110]}...\"\n")

def simulate_reply(laptop_id: int, response_text: str):
    laptop = get_laptop_by_id(laptop_id)
    if not laptop:
        print(f" Portátil #{laptop_id} não encontrado.")
        return

    print(f"\n A simular receção de resposta do vendedor do Portátil #{laptop_id}:")
    print(f"   Título: {laptop['title']}")
    print(f"   Preço atual: {laptop['price']}€")
    print(f"   Mensagem do vendedor: \"{response_text}\"")

    classification = classify_seller_response(response_text)
    print(f"   Classificação NLP: {classification}")

    if classification["status"] == "agreed":
        target_p = laptop.get("negotiated_price") or calculate_negotiated_offer(laptop["price"], 0.20)
        res = apply_negotiation_agreement(laptop_id, agreed_price=target_p, response_text=response_text)
        print("\n O REMETENTE/VENDEDOR CONCORDOU COM A PROPOSTA!")
        print(f"   Preço atualizado no banco de dados: {res['original_price']}€  {res['agreed_price']}€ (-20%)")
        print(f"   Novo Value Score (Preço/Qualidade):  {res['new_value_score']} ({res['deal_rating']})")
        print("   Estado atualizado para: 'agreed'\n")
    else:
        print(f"   Status: {classification['status']} (preço mantido em {laptop['price']}€)\n")

def add_to_inbox(laptop_id: int, response_text: str):
    inbox = []
    if INCOMING_RESPONSES_FILE.exists():
        try:
            inbox = json.loads(INCOMING_RESPONSES_FILE.read_text(encoding="utf-8"))
        except Exception:
            inbox = []
    inbox.append({
        "laptop_id": laptop_id,
        "response_text": response_text
    })
    INCOMING_RESPONSES_FILE.write_text(json.dumps(inbox, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f" Resposta adicionada à fila de entrada ({INCOMING_RESPONSES_FILE.name}) para o Portátil #{laptop_id}.")
    print("   O daemon de 5 minutos irá processá-la no próximo ciclo!\n")

def check_inbox_now():
    print(f"\n A verificar caixa de entrada de respostas agora...")
    processed = process_incoming_responses_queue()
    if processed:
        print(f" Processadas {len(processed)} respostas:")
        for p in processed:
            print(f"   • Portátil #{p['laptop_id']}: {p['action']} | Status: {p['status']}")
            if p.get("new_price"):
                print(f"     Novo Preço: {p['old_price']}€  {p['new_price']}€ (Score:  {p['value_score']})")
    else:
        print(" Nenhuma resposta pendente no ficheiro de inbox.")

def main():
    parser = argparse.ArgumentParser(description="Script de Regateio / Negociação de Portáteis (-20%)")
    parser.add_argument("--list", action="store_true", help="Listar melhores portáteis negociáveis")
    parser.add_argument("--propose", type=int, nargs="?", const=10, help="Gerar propostas de 20%% de desconto para o Top N portáteis")
    parser.add_argument("--simulate-reply", type=int, metavar="LAPTOP_ID", help="Simular receção de resposta para um portátil")
    parser.add_argument("--text", type=str, default="Olá! Aceito os 280€ com envio por CTT Expresso. Como prefere pagar?", help="Texto da resposta do vendedor")
    parser.add_argument("--inbox-add", type=int, metavar="LAPTOP_ID", help="Adicionar mensagem à fila do daemon de 5 minutos")
    parser.add_argument("--check-now", action="store_true", help="Executar imediatamente a verificação do daemon de 5 minutos")

    args = parser.parse_args()

    if args.list:
        list_negotiable_laptops(limit=25)
    elif args.propose is not None:
        apply_offers_for_top(limit=args.propose)
    elif args.simulate_reply is not None:
        simulate_reply(args.simulate_reply, args.text)
    elif args.inbox_add is not None:
        add_to_inbox(args.inbox_add, args.text)
    elif args.check_now:
        check_inbox_now()
    else:
        list_negotiable_laptops(limit=15)
        print(" Dicas de utilização:")
        print("   python tools/negotiate_discounts.py --propose 10             # Gerar propostas de -20% para o top 10")
        print("   python tools/negotiate_discounts.py --simulate-reply 292    # Simular resposta do vendedor a concordar")
        print("   python tools/negotiate_discounts.py --check-now             # Forçar ciclo de verificação imediato")

if __name__ == "__main__":
    main()
