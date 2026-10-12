"""
TDD Suite for Warranty and Condition (Second-Hand / Refurbished / New) Identification.
Tests:
1. Deterministic warranty extraction (Official 3-year retail warranty, CeX 5-year, OLX/Facebook date/invoice cues)
2. Negative warranty detection (sem garantia, garantia expirou, etc.)
3. Deterministic condition classification (Usado, Recondicionado, Novo)
4. Database query filtering by condition ('usado', 'recondicionado', 'novo') and has_warranty
"""

import unittest
import sqlite3
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from database import (
    extract_warranty_info,
    extract_condition_info,
    get_connection,
    get_laptops,
    get_laptop_stats
)


class TestWarrantyIdentification(unittest.TestCase):
    """Tests identifying warranty across retail and classified ads."""

    def test_cex_warranty(self):
        has_w, details = extract_warranty_info("Lenovo ThinkPad", "Bom estado", "cex")
        self.assertTrue(has_w)
        self.assertIn("5 Anos", details)

    def test_retail_store_official_warranty(self):
        stores = ["pcdiga", "worten", "pccomponentes", "globaldata"]
        for store in stores:
            has_w, details = extract_warranty_info("ASUS TUF Gaming", "Novo com caixa", store)
            self.assertTrue(has_w, f"Expected {store} to have official warranty")
            self.assertIn("3 Anos", details)

    def test_amazon_renewed_warranty(self):
        has_w, details = extract_warranty_info("MacBook Pro Renewed", "Recondicionado em caixa", "amazon")
        self.assertTrue(has_w)
        self.assertIn("Amazon Renewed", details)

    def test_olx_positive_warranty_with_date(self):
        has_w, details = extract_warranty_info(
            "HP Victus RTX 4050",
            "Comprado há 4 meses, com fatura e garantia até 2026. Pouco uso.",
            "olx"
        )
        self.assertTrue(has_w)
        self.assertIn("2026", details)

    def test_olx_positive_warranty_with_years(self):
        has_w, details = extract_warranty_info(
            "Lenovo Legion 5",
            "Fatura da Worten e garantia de 2 anos ativa.",
            "olx"
        )
        self.assertTrue(has_w)
        self.assertTrue("2 Anos" in details or "Worten" in details or "Fatura" in details)

    def test_olx_negative_warranty(self):
        has_w, details = extract_warranty_info(
            "MacBook Air 2019",
            "Funciona bem, sem garantia nem caixa, marcas de uso.",
            "olx"
        )
        self.assertFalse(has_w)
        self.assertEqual(details, "Sem Garantia")

    def test_facebook_no_mention(self):
        has_w, details = extract_warranty_info(
            "Acer Nitro 5",
            "Vendo por não usar. Preço negociável.",
            "facebook"
        )
        self.assertFalse(has_w)
        self.assertIsNone(details)


class TestConditionClassification(unittest.TestCase):
    """Tests classifying laptops into 'Novo', 'Recondicionado', or 'Usado'."""

    def test_cex_is_refurbished(self):
        cond = extract_condition_info("Lenovo T480", "Grau B", "cex")
        self.assertEqual(cond, "Recondicionado")

    def test_amazon_renewed_is_refurbished(self):
        cond = extract_condition_info("Dell XPS 13 Renewed", "Recondicionado certificado", "amazon")
        self.assertEqual(cond, "Recondicionado")

    def test_olx_sealed_in_box_is_new(self):
        cond = extract_condition_info("MacBook Pro M3", "Novo selado em caixa, nunca usado", "olx")
        self.assertEqual(cond, "Novo (Selado)")

    def test_olx_standard_is_used(self):
        cond = extract_condition_info("Asus ZenBook", "Bom estado geral com carregador", "olx")
        self.assertEqual(cond, "Usado")

    def test_retail_store_is_new(self):
        cond = extract_condition_info("MSI Katana 15", "Teclado PT", "pcdiga")
        self.assertEqual(cond, "Novo")


class TestDatabaseFiltering(unittest.TestCase):
    """Tests SQLite querying by condition and warranty."""

    def setUp(self):
        self.conn = get_connection()
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO laptops (
                    id, url, title, price, source, location, condition_grade, has_warranty, warranty_details
                ) VALUES (88881, 'https://olx.pt/test-88881', 'TDD_FILTER_TARGET_ Usado Sem Garantia', 300, 'olx', 'Leiria', 'Usado', 0, 'Sem Garantia')
            """)
            cursor.execute("""
                INSERT OR REPLACE INTO laptops (
                    id, url, title, price, source, location, condition_grade, has_warranty, warranty_details
                ) VALUES (88882, 'https://cex.pt/test-88882', 'TDD_FILTER_TARGET_ Recondicionado Garantia', 450, 'cex', 'Porto', 'Recondicionado', 1, 'Garantia 5 Anos CeX')
            """)
            cursor.execute("""
                INSERT OR REPLACE INTO laptops (
                    id, url, title, price, source, location, condition_grade, has_warranty, warranty_details
                ) VALUES (88883, 'https://pcdiga.pt/test-88883', 'TDD_FILTER_TARGET_ Novo Loja', 700, 'pcdiga', 'Lisboa', 'Novo', 1, 'Garantia Oficial 3 Anos')
            """)

    def tearDown(self):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM laptops WHERE id IN (88881, 88882, 88883)")
        self.conn.close()

    def test_filter_by_condition_usado(self):
        res = get_laptops(search="TDD_FILTER_TARGET_", condition="usado")
        ids = [l["id"] for l in res["laptops"]]
        self.assertIn(88881, ids)
        self.assertNotIn(88882, ids)
        self.assertNotIn(88883, ids)

    def test_filter_by_condition_recondicionado(self):
        res = get_laptops(search="TDD_FILTER_TARGET_", condition="recondicionado")
        ids = [l["id"] for l in res["laptops"]]
        self.assertIn(88882, ids)
        self.assertNotIn(88881, ids)

    def test_filter_by_has_warranty_only(self):
        res = get_laptops(search="TDD_FILTER_TARGET_", has_warranty=True)
        ids = [l["id"] for l in res["laptops"]]
        self.assertIn(88882, ids)
        self.assertIn(88883, ids)
        self.assertNotIn(88881, ids)


if __name__ == "__main__":
    unittest.main()
