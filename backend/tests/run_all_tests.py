"""
Test Runner for Laptop Scraper Backend Test Suites
"""
import unittest
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = TESTS_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.discover(str(TESTS_DIR), pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
