import json
from pathlib import Path
import sys

backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from geo_utils import calculate_travel_specs
from laptop_scraper import extract_laptop_specs
from database import insert_or_update_laptops_batch

temp_file = backend_dir / "data" / "olx_temp.json"
if not temp_file.exists():
    print("Error: olx_temp.json does not exist")
    sys.exit(1)

with open(temp_file, "r", encoding="utf-8") as f:
    data = json.load(f)

items = data.get("data", [])
deals = []
for item in items:
    title = item.get("title", "")
    if not title:
        continue
    price = 0.0
    for p in item.get("params", []):
        if p.get("key") == "price":
            val_obj = p.get("value", {})
            price = float(val_obj.get("value") or 0.0)
            break
    if price <= 0:
        price = float(item.get("price", {}).get("regularPrice", {}).get("value") or 0.0)

    link = item.get("url", "")
    img_url = None
    photos = item.get("photos", [])
    if photos:
        p0 = photos[0]
        raw_link = p0.get("link", "") if isinstance(p0, dict) else str(p0)
        if raw_link:
            img_url = raw_link.replace(":443", "").replace("{width}x{height}", "1000x750")

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

    deals.append({
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
        "ram_type": specs["ram_type"],
        "ram_display": specs["ram_display"],
        "storage_gb": specs["storage_gb"],
        "storage_type": specs["storage_type"],
        "storage_display": specs["storage_display"],
        "gpu": specs["gpu"],
        "screen_size": specs["screen_size"],
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

saved = insert_or_update_laptops_batch(deals)
print(f"SUCCESS: Inserted {saved} OLX deals into database!")
