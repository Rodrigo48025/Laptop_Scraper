import asyncio
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from laptop_scraper import LaptopDealScraper

async def main():
    print("Testing OLX scraper...")
    scraper = LaptopDealScraper(headless=True)
    deals = await scraper.scrape_olx(min_price=200, max_price=800, search="portatil", limit=10)
    print(f"OLX scraper returned {len(deals)} deals!")
    for d in deals[:3]:
        print(" -", d.get("title"), "|", d.get("price"), "€ |", d.get("location"), "| img:", bool(d.get("image_url")))

if __name__ == "__main__":
    asyncio.run(main())
