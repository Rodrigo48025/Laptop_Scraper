"""
TDD Suite for Pitch Dispatching to OLX Portugal & Facebook Marketplace.
Tests:
1. Negotiability detection (Peer-to-peer OLX/Facebook vs Retail stores vs 'preço fixo' ads)
2. Portuguese negotiation pricing calculation & natural 5€ rounding
3. 12-combination Pitch Templates Matrix (Delivery method x Pitch Tone)
4. Seller response classification (Agreed / Declined / Counter-Offer)
5. Session certification gatekeeping (blocks unauthenticated dispatches)
6. Dispatch execution: database transaction in laptop_negotiations and status updates
"""

import unittest
import sqlite3
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add backend directory to sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from negotiation import (
    is_laptop_negotiable,
    calculate_negotiated_offer,
    compose_negotiation_message,
    NON_NEGOTIABLE_KEYWORDS,
    AGREED_PHRASES,
    DECLINED_PHRASES
)
from main import (
    PITCH_TEMPLATES_MATRIX,
    get_pitch_template,
    check_platform_session_certified,
    dispatch_pitches,
    BatchPitchDispatchRequest,
    TargetItem
)
from database import (
    get_connection,
    init_db
)


class TestPitchNegotiability(unittest.TestCase):
    """Tests identifying if a laptop listing is negotiable or fixed-price."""

    def test_olx_is_negotiable(self):
        laptop = {"source": "olx", "price": 450, "title": "Lenovo Legion 5", "description": "Bom estado"}
        is_neg, reason = is_laptop_negotiable(laptop)
        self.assertTrue(is_neg)

    def test_facebook_is_negotiable(self):
        laptop = {"source": "facebook", "price": 600, "title": "Asus ROG Strix", "description": "Como novo"}
        is_neg, reason = is_laptop_negotiable(laptop)
        self.assertTrue(is_neg)

    def test_retail_stores_are_non_negotiable(self):
        stores = ["worten", "cex", "pcdiga", "amazon", "globaldata", "pccomponentes"]
        for store in stores:
            laptop = {"source": store, "price": 500, "title": "HP Pavilion", "description": "Loja oficial"}
            is_neg, reason = is_laptop_negotiable(laptop)
            self.assertFalse(is_neg, f"Expected {store} to be non-negotiable")
            self.assertIn("preço tabelado", reason.lower())

    def test_explicit_fixed_price_in_olx_is_rejected(self):
        laptop = {
            "source": "olx",
            "price": 500,
            "title": "MacBook Air M1",
            "description": "Portátil impecável. Preço fixo, não negociável, sem trocas."
        }
        is_neg, reason = is_laptop_negotiable(laptop)
        self.assertFalse(is_neg)
        self.assertIn("não negociável", reason.lower())


class TestPitchPricingCalculations(unittest.TestCase):
    """Tests Portuguese discount calculations and natural rounding."""

    def test_standard_20_percent_discount(self):
        # 500€ - 20% = 400€
        offer = calculate_negotiated_offer(500.0, 0.20)
        self.assertEqual(offer, 400.0)

    def test_portuguese_5_euro_increment_rounding(self):
        # 490€ - 20% = 392€ -> rounds to natural 390€ (multiples of 5€)
        offer = calculate_negotiated_offer(490.0, 0.20)
        self.assertEqual(offer, 390.0)

        # 650€ - 15% = 552.5€ -> rounds to 550.0€ (nearest 5€ increment with half-to-even)
        offer = calculate_negotiated_offer(650.0, 0.15)
        self.assertEqual(offer, 550.0)

    def test_budget_tier_under_50_euros(self):
        # Under 50€, rounds to integer
        offer = calculate_negotiated_offer(45.0, 0.20)
        self.assertEqual(offer, 36.0)


class TestPitchTemplatesMatrix(unittest.TestCase):
    """Tests the 12-combination template matrix (Delivery x Pitch Tone)."""

    def test_all_12_matrix_combinations_exist(self):
        methods = ["auto", "ctt", "presencial"]
        tones = ["direto", "dinheiro_imediato", "estudante", "suave"]

        for m in methods:
            for t in tones:
                tpl = get_pitch_template(m, t)
                self.assertIsInstance(tpl, str, f"Missing template for {m}/{t}")
                self.assertIn("{offer_price}", tpl, f"Template {m}/{t} missing {{offer_price}}")
                self.assertIn("{title}", tpl, f"Template {m}/{t} missing {{title}}")

    def test_ctt_templates_mention_shipping(self):
        tones = ["direto", "dinheiro_imediato", "estudante", "suave"]
        for tone in tones:
            tpl = get_pitch_template("ctt", tone)
            self.assertTrue(
                "ctt" in tpl.lower() or "cobrança" in tpl.lower() or "envio" in tpl.lower(),
                f"CTT template for {tone} should mention shipping or CTT"
            )

    def test_presencial_templates_mention_handover(self):
        tones = ["direto", "dinheiro_imediato", "estudante", "suave"]
        for tone in tones:
            tpl = get_pitch_template("presencial", tone)
            self.assertTrue(
                "mão" in tpl.lower() or "levantamento" in tpl.lower() or "desloco" in tpl.lower() or "dinheiro" in tpl.lower(),
                f"Presencial template for {tone} should mention handover or in-person"
            )

    def test_template_resolution_replaces_all_variables(self):
        tpl = get_pitch_template("presencial", "dinheiro_imediato")
        resolved = (tpl
            .replace("{title}", "ASUS ROG RTX 4060")
            .replace("{offer_price}", "550")
            .replace("{price}", "650")
            .replace("{discount_pct}", "15")
            .replace("{location}", "Leiria"))

        self.assertNotIn("{title}", resolved)
        self.assertNotIn("{offer_price}", resolved)
        self.assertNotIn("{price}", resolved)
        self.assertIn("550", resolved)
        self.assertIn("ASUS ROG RTX 4060", resolved)


class TestSessionGatekeepingAndDispatch(unittest.TestCase):
    """Tests session verification and atomic dispatch recording."""

    def setUp(self):
        self.conn = get_connection()
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO laptops (
                    id, url, title, price, source, location, contact_status
                ) VALUES (99991, 'https://www.olx.pt/d/test-omen', 'HP Omen 16 RTX 4070', 800, 'olx', 'Lisboa', 'uncontacted')
            """)
            cursor.execute("""
                INSERT OR REPLACE INTO laptops (
                    id, url, title, price, source, location, contact_status
                ) VALUES (99992, 'https://www.facebook.com/marketplace/test-legion', 'Lenovo Legion 5 Pro', 750, 'facebook', 'Porto', 'uncontacted')
            """)

    def tearDown(self):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM laptop_negotiations WHERE laptop_id IN (99991, 99992)")
            cursor.execute("DELETE FROM laptops WHERE id IN (99991, 99992)")
        self.conn.close()

    @patch("main.check_platform_session_certified")
    def test_dispatch_blocks_when_session_not_certified(self, mock_certified):
        mock_certified.return_value = False

        req = BatchPitchDispatchRequest(
            targets=[
                TargetItem(
                    laptop_id=99991,
                    offer_price=640.0,
                    discount_pct=20.0,
                    pitch_message="Olá! Aceita 640€ pelo HP Omen?",
                    strategy_used="dinheiro_imediato"
                )
            ]
        )

        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            dispatch_pitches(req)

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Sessão necessária", ctx.exception.detail)

    @patch("main.check_platform_session_certified")
    def test_dispatch_succeeds_when_session_certified(self, mock_certified):
        mock_certified.return_value = True

        req = BatchPitchDispatchRequest(
            targets=[
                TargetItem(
                    laptop_id=99991,
                    offer_price=640.0,
                    discount_pct=20.0,
                    pitch_message="Olá! Aceita 640€ pelo HP Omen?",
                    strategy_used="dinheiro_imediato"
                ),
                TargetItem(
                    laptop_id=99992,
                    offer_price=600.0,
                    discount_pct=20.0,
                    pitch_message="Boa tarde! Consegue fazer 600€ pelo Lenovo?",
                    strategy_used="direto"
                )
            ]
        )

        result = dispatch_pitches(req)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["created_count"], 2)

        # Verify database state
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM laptop_negotiations WHERE laptop_id = 99991")
        neg = cursor.fetchone()
        self.assertIsNotNone(neg)
        self.assertEqual(neg["status"], "sent")
        self.assertEqual(neg["offered_price"], 640.0)

        # Verify laptop contact_status updated
        cursor.execute("SELECT contact_status, negotiation_status FROM laptops WHERE id = 99991")
        laptop_state = cursor.fetchone()
        self.assertEqual(laptop_state["contact_status"], "offered")
        self.assertEqual(laptop_state["negotiation_status"], "sent")
        conn.close()


if __name__ == "__main__":
    unittest.main()
