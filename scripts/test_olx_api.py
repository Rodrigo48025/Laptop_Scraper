import asyncio
import json
import urllib.request
import re
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from geo_utils import calculate_travel_specs
from laptop_scraper import extract_laptop_specs, parse_price

def fetch_olx_api(min_price=200, max_price=800, search="portatil", limit=40):
    url = f"https://www.olx.pt/api/v1/offers/?query={urllib.parse.quote_plus(search)}&filter_float_price:from={int(min_price)}&filter_float_price:to={int(max_price)}&offset=0&limit={limit}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json"
        }
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        
    items = data.get("data", [])
    results = []
    for item in items:
        title = item.get("title", "")
        if not title:
            continue
            
        # Price extraction from params or direct object
        price = 0.0
        for p in item.get("params", []):
            if p.get("key") == "price":
                val_obj = p.get("value", {})
                price = float(val_obj.get("value") or 0.0)
                break
        if price <= 0:
            price = float(item.get("price", {}).get("regularPrice", {}).get("value") or 0.0)
            
        link = item.get("url", "")
        
        # High-res photo extraction
        img_url = None
        photos = item.get("photos", [])
        if photos:
            p0 = photos[0]
            raw_link = p0.get("link", "") if isinstance(p0, dict) else str(p0)
            if raw_link:
                img_url = raw_link.replace(":443", "").replace("{width}x{height}", "1000x750")
                
        # Location
        loc_data = item.get("location", {})
        city = loc_data.get("city", {}).get("name", "") if isinstance(loc_data, dict) else ""
        region = loc_data.get("region", {}).get("name", "") if isinstance(loc_data, dict) else ""
        location = f"{city}, {region}".strip(", ") if city else region or "Portugal"
        
        desc = item.get("description", "")
        params = item.get("params", [])
        
        travel = calculate_travel_specs(location, source="OLX")
        specs = extract_laptop_specs(
            title, f"{desc} {location}", params, price=price,
            travel_distance_km=travel.get("travel_distance_km"),
            travel_label=travel.get("travel_label"),
            source="OLX"
        )
        
        results.append({
            "title": title,
            "price": float(price),
            "currency": "EUR",
            "condition": "Usado",
            "source": "OLX",
            "url": link,
            "image_url": img_url,
            "location": location,
            "brand": specs["brand"],
            "cpu": specs["cpu"],
            "ram_gb": specs["ram_gb"],
            "ram_display": specs["ram_display"],
            "storage_gb": specs["storage_gb"],
            "storage_display": specs["storage_display"],
            "gpu": specs["gpu"],
            "spec_score": specs["spec_score"],
            "deal_score": specs.get("deal_score") or specs.get("spec_score"),
            "deal_rating": specs["deal_rating"],
            "travel_distance_km": travel.get("travel_distance_km"),
            "travel_time_min": travel.get("travel_time_min"),
            "travel_label": travel.get("travel_label"),
            "supports_shipping": 1,
            "contact_status": "uncontacted",
            "description": desc
        })
    return results

if __name__ == "__main__":
    deals = fetch_olx_api(min_price=200, max_price=800, search="portatil", limit=15)
    print(f"Extracted {len(deals)} OLX laptop deals successfully!")
    for d in deals[:5]:
        print(f" -> [{d['source']}] {d['title'][:45]} | {d['price']}€ | {d['cpu']} | {d['ram_display']} | {d['location']} | Img: {bool(d['image_url'])}")
