import re
import json
import asyncio
import logging
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional
from pathlib import Path
from playwright.async_api import async_playwright, Page, Browser

from database import insert_or_update_laptop, insert_or_update_laptops_batch
from power_utils import calculate_power_specs
from geo_utils import calculate_travel_specs

logger = logging.getLogger("laptop_scraper")
logging.basicConfig(level=logging.INFO)

def parse_price(price_str: str) -> Optional[float]:
    """Parse European formatted price strings like '650 €', '699 , 99 €', '1.099,00 €' into float."""
    if not price_str:
        return None
    try:
        clean = price_str.replace("€", "").replace("EUR", "").strip()
        clean = re.sub(r'\s*,\s*', ',', clean)
        if '.' in clean and ',' in clean:
            clean = clean.replace('.', '').replace(',', '.')
        elif ',' in clean:
            clean = clean.replace(',', '.')
        
        m = re.search(r'(\d+(?:\.\d+)?)', clean)
        if m:
            return float(m.group(1))
    except Exception as e:
        logger.debug(f"Failed to parse price '{price_str}': {e}")
    return None

def extract_laptop_specs(
    title: str,
    text: str = "",
    params: Optional[List[Dict[str, Any]]] = None,
    price: Optional[float] = None,
    travel_distance_km: Optional[float] = None,
    travel_label: Optional[str] = None,
    source: Optional[str] = None
) -> Dict[str, Any]:
    """
    100% deterministic rule-based hardware spec extractor.
    Extracts brand, CPU, RAM (with DDR4/DDR5 detection), Storage (NVMe/SSD),
    GPU (with VRAM), Screen size & refresh rate, and calculates Spec Score (1.0 to 10.0)
    with proximity calibration centered on Marinha Grande / Leiria and fast courier delivery.
    Zero LLM dependencies.
    """
    combined = f"{title} {text}".lower().replace('™', '').replace('®', '')

    # 1. Brand Detection
    brand = None
    known_brands = ['asus', 'lenovo', 'hp', 'apple', 'dell', 'acer', 'msi', 'gigabyte', 'samsung', 'huawei', 'toshiba', 'razer', 'microsoft', 'surface']
    for b in known_brands:
        if b in combined:
            if b == 'surface' or b == 'microsoft':
                brand = 'Microsoft Surface'
            elif b in ['hp', 'msi', 'dell']:
                brand = b.upper()
            else:
                brand = b.capitalize()
            break
    if not brand and params:
        for p in params:
            if p.get('name') == 'Marca' or p.get('key') == 'marca':
                val = p.get('value')
                if isinstance(val, dict):
                    brand = val.get('label') or val.get('key')
                elif isinstance(val, str):
                    brand = val
                break
    if isinstance(brand, dict):
        brand = brand.get('label') or brand.get('key') or None
    elif brand:
        brand = str(brand)

    # 2. RAM Generation & Capacity
    ram_gen = ""
    if 'lpddr5x' in combined or 'lpddr5' in combined: ram_gen = "LPDDR5"
    elif 'ddr5' in combined: ram_gen = "DDR5"
    elif 'lpddr4x' in combined or 'lpddr4' in combined: ram_gen = "LPDDR4"
    elif 'ddr4' in combined: ram_gen = "DDR4"
    elif 'ddr3' in combined: ram_gen = "DDR3"

    ram_gb = None
    # Prioritize explicit RAM markers
    ram_patterns = [
        r'ram\s*[:=]?\s*(\d{1,2})\s*(?:gb|g)?\b',
        r'(\d{1,2})\s*(?:gb|g)?\s*(?:ddr[345]|lpddr[45]|ram|mem[oó]ria)\b',
        r'(\d{1,2})\s*(?:gb|g)\s*(?:/|\+)\s*(?:\d{3,4}|1tb|2tb)',
    ]
    for p in ram_patterns:
        m = re.search(p, combined)
        if m:
            val = int(m.group(1))
            if val in (4, 6, 8, 12, 16, 20, 24, 32, 40, 48, 64, 128):
                ram_gb = val
                break

    if not ram_gb:
        # Avoid matching GPU VRAM by stripping GPU phrases first
        cleaned_ram_str = re.sub(r'(?:rtx|gtx|radeon(?:\s*pro)?|grafica|vram|dedicada)[^,.]*?\b\d{1,2}\s*(?:gb|g)\b', '', combined)
        m = re.search(r'\b(\d{1,2})\s*(?:gb|g)\b', cleaned_ram_str)
        if m:
            val = int(m.group(1))
            if val in (4, 6, 8, 12, 16, 20, 24, 32, 40, 48, 64, 128):
                ram_gb = val

    ram_gb = ram_gb or 8
    ram_display = f"{ram_gb} GB {ram_gen}".strip() if ram_gen else f"{ram_gb} GB RAM"

    # 3. Storage Type & Capacity
    storage_type = "SSD"
    if 'nvme' in combined: storage_type = "NVMe SSD"
    elif 'm.2' in combined or 'm2' in combined: storage_type = "M.2 SSD"
    elif 'pcie' in combined: storage_type = "PCIe SSD"
    elif 'hdd' in combined and 'ssd' not in combined: storage_type = "HDD"

    storage_gb = None
    m_tb = re.search(r'\b([1-4])\s*(?:tb|t)\b', combined)
    if m_tb:
        storage_gb = int(m_tb.group(1)) * 1000
    else:
        m_ssd = re.search(r'(\d{3,4})\s*(?:gb|g)?\s*(?:ssd|nvme|m\.2|disco|hdd|armazenamento)', combined)
        if not m_ssd:
            m_ssd = re.search(r'(?:ssd|nvme|disco|armazenamento)\s*[:=]?\s*(\d{3,4})\s*(?:gb|g)?', combined)
        if m_ssd:
            val = int(m_ssd.group(1))
            if val in (128, 240, 250, 256, 480, 500, 512, 960, 1000, 1024, 2000):
                storage_gb = val
    storage_gb = storage_gb or 512
    storage_display = f"{storage_gb / 1000:.0f} TB {storage_type}" if storage_gb >= 1000 else f"{storage_gb} GB {storage_type}"

    # 4. CPU Extraction
    cpu = None
    is_apple_context = any(x in combined for x in ['apple', 'macbook', 'mac ', 'macos', 'imac'])
    if is_apple_context:
        if 'm3 max' in combined or 'm3 pro' in combined: cpu = 'Apple M3 Pro/Max'
        elif re.search(r'\bm3\b', combined): cpu = 'Apple M3'
        elif 'm2 pro' in combined or 'm2 max' in combined: cpu = 'Apple M2 Pro'
        elif re.search(r'\bm2\b', combined): cpu = 'Apple M2'
        elif 'm1 pro' in combined or 'm1 max' in combined: cpu = 'Apple M1 Pro'
        elif re.search(r'\bm1\b', combined): cpu = 'Apple M1'
    
    if not cpu:
        m_ryzen = re.search(r'\b(?:ryzen|ryz|r)\s*([3579])\s*(?:pro)?\s*([0-9]{4}[a-z]{0,2})?', combined)
        if m_ryzen:
            r_tier = m_ryzen.group(1)
            r_model = m_ryzen.group(2) or ''
            cpu = f"AMD Ryzen {r_tier} {r_model}".strip()

    if not cpu:
        m_ultra = re.search(r'core\s*ultra\s*([579])\s*([0-9]{3}[a-z]{0,2})?', combined)
        if m_ultra:
            cpu = f"Intel Core Ultra {m_ultra.group(1)} {m_ultra.group(2) or ''}".strip()

    if not cpu:
        m_intel_hyphen = re.search(r'i([3579])[\s\-](\d{4,5}[a-z]{0,2})', combined)
        m_intel_dense = re.search(r'\bi([3579])(\d{4,5}[a-z]{0,2})\b', combined)
        if m_intel_hyphen:
            cpu = f"Intel Core i{m_intel_hyphen.group(1)}-{m_intel_hyphen.group(2)}".upper()
        elif m_intel_dense:
            cpu = f"Intel Core i{m_intel_dense.group(1)}-{m_intel_dense.group(2)}".upper()
        else:
            m_intel_simple = re.search(r'\b(i[3579])\b', combined)
            if m_intel_simple:
                cpu = f"Intel Core {m_intel_simple.group(1).upper()}"

    if not cpu and 'snapdragon x' in combined:
        cpu = "Snapdragon X Elite/Plus"
    elif not cpu and 'xeon' in combined:
        m_xeon = re.search(r'xeon\s*([eew0-9\-]+(?:\s*v\d)?)', combined)
        cpu = f"Intel Xeon {m_xeon.group(1).upper()}" if m_xeon else "Intel Xeon"

    cpu = cpu or "Intel/AMD Multi-Core"

    # 5. GPU & VRAM Extraction
    gpu = None
    vram = ""
    m_vram = re.search(r'(?:vram|dedicada|gddr\d|grafica[^,.]*?)\b(\d{1,2})\s*(?:gb|g)\b', combined)
    if not m_vram:
        m_vram = re.search(r'(?:rtx|gtx|radeon(?:\s*pro)?|quadro)\s+[a-z0-9\s]{0,15}?\b(\d{1,2})\s*(?:gb|g)\b', combined)
    if m_vram:
        vram = f" {m_vram.group(1)}GB"

    m_rtx = re.search(r'(?:rtx\s*|geforce\s+rtx\s*|\brtx\b|\brtx)(\d{4})(?:\s*ti)?', combined)
    if not m_rtx:
        m_rtx = re.search(r'\b(40[5-9]0|30[5-9]0|20[5-8]0)(?:\s*ti)?\b', combined)
    if m_rtx:
        model = m_rtx.group(1)
        is_ti = 'ti' in combined[m_rtx.start():m_rtx.end()+6] or 'ti' in m_rtx.group(0)
        ti_str = " Ti" if is_ti else ""
        gpu = f"NVIDIA RTX {model}{ti_str}{vram}".strip()
    elif 'gtx' in combined:
        m_gtx = re.search(r'gtx\s*(\d{3,4}(?:\s*ti)?)', combined)
        gpu = f"NVIDIA GTX {m_gtx.group(1).upper()}{vram}" if m_gtx else f"NVIDIA GTX{vram}"
    elif 'quadro' in combined:
        m_quadro = re.search(r'quadro\s*([a-z0-9]+)', combined)
        gpu = f"NVIDIA Quadro {m_quadro.group(1).upper()}{vram}" if m_quadro else f"NVIDIA Quadro{vram}"
    elif re.search(r'\b(?:amd|radeon)\s*pro\s*(\d{3,4}[a-z]?)', combined):
        m_pro = re.search(r'\b(?:amd|radeon)\s*pro\s*(\d{3,4}[a-z]?)', combined)
        gpu = f"AMD Radeon Pro {m_pro.group(1).upper()}{vram}"
    elif 'radeon 680m' in combined or 'radeon 780m' in combined:
        gpu = "AMD Radeon 680M/780M"
    elif 'radeon 610m' in combined or 'radeon 760m' in combined:
        gpu = "AMD Radeon Graphics"
    elif 'radeon' in combined:
        gpu = f"AMD Radeon Graphics{vram}"
    elif 'iris xe' in combined:
        gpu = "Intel Iris Xe"
    elif 'arc' in combined and 'intel' in combined:
        gpu = "Intel Arc Graphics"
    elif 'apple' in combined and any(x in combined for x in ['m1', 'm2', 'm3']):
        gpu = "Apple Silicon GPU"

    gpu = gpu or "Integrated Graphics"

    # 6. Screen Size & Refresh Rate
    screen_hz = ""
    m_hz = re.search(r'(\d{2,3})\s*hz\b', combined)
    if m_hz:
        screen_hz = f" {m_hz.group(1)}Hz"

    screen = None
    m_screen = re.search(r'(\d{2}(?:[.,]\d)?)\s*(?:\"|\'\'|\s*pol|\s*inch)', combined)
    if m_screen:
        screen = f"{m_screen.group(1).replace(',', '.')}\"{screen_hz}"
    elif params:
        for p in params:
            if 'tamanho' in p.get('name', '').lower() or 'screendiagonal' in p.get('key', ''):
                s_val = p.get('value')
                if isinstance(s_val, dict):
                    screen = f"{s_val.get('label') or s_val.get('key')}{screen_hz}"
                else:
                    screen = f"{s_val}{screen_hz}"
                break
    screen = screen or f"15.6\"{screen_hz}"

    # 7. Calibrated Spec Score Calculation (Strictly normalized to 10.0 Benchmark)
    is_apple = (brand or '').lower() == 'apple' or any(x in combined for x in ['macbook', 'macos', 'apple m1', 'apple m2', 'apple m3'])
    is_arm = 'snapdragon' in combined or 'qualcomm' in combined
    is_ancient_cpu = bool(re.search(r'\bi[357]-?[678]\d{3}', combined) or any(x in combined for x in ['e3-1505', 'xeon', '7820hq', '8850h']))

    if is_apple:
        spec_score = 1.8
        value_score = 1.8
        deal_rating = "Disqualified: Apple / Mac"
    elif is_arm:
        spec_score = 1.5
        value_score = 1.5
        deal_rating = "Disqualified: Snapdragon ARM"
    elif is_ancient_cpu:
        spec_score = 3.2
        value_score = 3.0
        deal_rating = "Potato / Ancient CPU (Pre-2019)"
    else:
        # Base points for standard modern x86_64 Linux machine
        pts = 1.0

        # CPU Generation & Multi-core power (Freshness & modern instruction sets)
        if any(x in combined for x in ['13620', '13700', '13800', '14700', '7840', '7735', '8845', 'ultra 7', 'ultra 5', '13500']):
            pts += 3.2
        elif any(x in combined for x in ['5800h', '5825u', '5700u', '7730u', '7730', '6800h', '6800hs', '6800u', 'ryzen 7 pro', '12700', '12500', '12450', '11800']):
            pts += 2.6
        elif any(x in combined for x in ['5600h', '5500u', '7535', '7530', '7520', '11400', '1165g', 'ryzen 7', 'i7']):
            pts += 1.9
        elif any(x in combined for x in ['ryzen 5', 'i5']):
            pts += 1.4
        else:
            pts += 0.8

        # GPU Acceleration & CUDA / Steam Proton / AI Models
        gpu_u = (gpu + ' ' + title).upper()
        if '4060' in gpu_u:
            pts += 2.2
        elif '4050' in gpu_u:
            pts += 1.9
        elif '3060' in gpu_u:
            pts += 1.8
        elif '3050 TI' in gpu_u or '3050TI' in gpu_u:
            pts += 1.4
        elif '3050' in gpu_u:
            pts += 1.2
        elif any(x in gpu_u for x in ['2060', '2070', '2080']):
            pts += 1.2
        elif '2050' in gpu_u:
            pts += 0.9
        elif '680M' in gpu_u or '780M' in gpu_u:
            pts += 0.9
        elif 'GTX' in gpu_u or 'QUADRO' in gpu_u:
            pts += 0.5
        elif 'IRIS XE' in gpu_u:
            pts += 0.4
        else:
            pts += 0.1

        # RAM (Capacity & Multi-VM Headroom)
        if '32gb' in combined or '32 gb' in combined or ram_gb >= 32:
            pts += 2.5
        elif '24gb' in combined or '24 gb' in combined or ram_gb >= 24:
            pts += 2.1
        elif '16gb' in combined or '16 gb' in combined or ram_gb >= 16:
            pts += 1.6
        else:
            pts += 0.4

        if ram_gen in ["DDR5", "LPDDR5"] or any(x in combined for x in ['ddr5', 'lpddr5']):
            pts += 0.4

        # Storage
        if '2tb' in combined or '2 tb' in combined or storage_gb >= 2000:
            pts += 1.0
        elif '1tb' in combined or '1 tb' in combined or storage_gb >= 1000:
            pts += 0.7
        elif storage_gb >= 512:
            pts += 0.4
        else:
            pts += 0.1

        # Condition bonus (New in open box)
        if any(x in combined for x in ['novo', 'caixa aberta', 'embalado']):
            pts += 0.5

        # Price vs Value bonus for modern hardware
        if price:
            if price <= 520 and ('3050' in gpu_u or 'ryzen 7' in combined or '11800' in combined):
                pts += 0.7
            elif price <= 620 and ('4050' in gpu_u or '3060' in gpu_u or '32gb' in combined):
                pts += 0.7
            elif price <= 700 and ('13620' in combined or '7840' in combined or 'ultra' in combined):
                pts += 0.6

        # Scale relative to max raw points (9.20 pts = 10.0 Benchmark)
        spec_score = round(min(10.0, max(1.0, (pts / 9.20) * 10.0)), 1)

        # Preço / Qualidade (Value Score: 1.0 to 10.0 normalized against 550€ budget midpoint)
        if price and price > 0:
            ratio = (550.0 / float(price)) ** 0.70
            value_score = round(min(10.0, max(1.0, spec_score * ratio)), 1)
        else:
            value_score = spec_score

        # Balanced Deal Rating tiers combining hardware tier and price/quality efficiency
        if spec_score >= 8.8 and value_score >= 8.8:
            deal_rating = "★ The Benchmark 10"
        elif value_score >= 8.5 and spec_score >= 7.0:
            deal_rating = "Top Value Deal"
        elif spec_score >= 8.2:
            deal_rating = "Elite Engineering Rig"
        elif spec_score >= 7.0:
            deal_rating = "High Performance"
        elif spec_score >= 5.8:
            deal_rating = "Solid Dev Machine"
        elif spec_score >= 4.5:
            deal_rating = "Budget Daily Driver"
        else:
            deal_rating = "Entry Level"

    power = calculate_power_specs(cpu, gpu, brand)

    return {
        "brand": brand or "Laptop",
        "cpu": cpu,
        "ram_gb": ram_gb,
        "ram_type": ram_gen,
        "ram_display": ram_display,
        "storage_gb": storage_gb,
        "storage_type": storage_type,
        "storage_display": storage_display,
        "gpu": gpu,
        "screen_size": screen,
        "spec_score": spec_score,
        "value_score": value_score if not (is_apple or is_arm or is_ancient_cpu) else (1.8 if is_apple else (1.5 if is_arm else 3.0)),
        "deal_rating": deal_rating,
        **power
    }

class LaptopDealScraper:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.is_aborted = False
        self._active_browsers: List[Browser] = []

    async def abort(self):
        """Immediately abort any active scrape and close all open browser instances."""
        self.is_aborted = True
        for b in list(self._active_browsers):
            try:
                await b.close()
            except Exception:
                pass
        self._active_browsers.clear()

    async def _get_browser_page(self, playwright_instance, platform: Optional[str] = None) -> tuple[Browser, Page]:
        browser = await playwright_instance.chromium.launch(
            headless=self.headless,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-extensions"
            ]
        )
        self._active_browsers.append(browser)
        context_kwargs: Dict[str, Any] = {
            "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "locale": "pt-PT",
            "viewport": {"width": 1440, "height": 900}
        }
        if platform:
            profile_path = Path(__file__).resolve().parent / "data" / "playwright_profile" / f"storage_state_{platform.lower()}.json"
            if profile_path.exists():
                context_kwargs["storage_state"] = str(profile_path)
        context = await browser.new_context(**context_kwargs)
        page = await context.new_page()
        return browser, page

    def _scrape_olx_api_sync(self, min_price: float = 200, max_price: float = 800, search: str = "portatil", limit: int = 60) -> List[Dict[str, Any]]:
        """Direct, high-speed extraction from OLX Portugal's official REST API."""
        results: List[Dict[str, Any]] = []
        try:
            import subprocess, urllib.parse
            q_enc = urllib.parse.quote_plus(search)
            api_url = f"https://www.olx.pt/api/v1/offers/?query={q_enc}&filter_float_price:from={int(min_price)}&filter_float_price:to={int(max_price)}&offset=0&limit={min(limit, 50)}"
            logger.info(f"Querying OLX Portugal REST API: {api_url}")
            res = subprocess.run([
                "curl", "-s", api_url,
                "-H", "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "-H", "Accept: application/json"
            ], capture_output=True, text=True, timeout=12)

            if res.returncode == 0 and res.stdout:
                data = json.loads(res.stdout)
                items = data.get("data", [])
                logger.info(f"OLX API returned {len(items)} offers")
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

                    deal_rating = specs["deal_rating"]
                    if deal_rating not in ["★ The Benchmark 10", "God-Tier VM Host"] and specs["spec_score"] >= 7.5 and price <= (min_price + 150):
                        deal_rating = "Top Value Deal"

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
                        "ram_type": specs["ram_type"],
                        "ram_display": specs["ram_display"],
                        "storage_gb": specs["storage_gb"],
                        "storage_type": specs["storage_type"],
                        "storage_display": specs["storage_display"],
                        "gpu": specs["gpu"],
                        "screen_size": specs["screen_size"],
                        "spec_score": specs["spec_score"],
                        "deal_score": specs.get("deal_score") or specs.get("spec_score"),
                        "deal_rating": deal_rating,
                        "raw_snippet": f"{price}€ | OLX Portugal | {location}",
                        "query": search,
                        "travel_distance_km": travel.get("travel_distance_km"),
                        "travel_time_min": travel.get("travel_time_min"),
                        "travel_label": travel.get("travel_label"),
                        "supports_shipping": 1,
                        "contact_status": "uncontacted",
                        "description": desc
                    })
        except Exception as e:
            logger.warning(f"OLX API error, falling back to Playwright: {e}")
        return results

    async def scrape_olx(self, min_price: float = 400, max_price: float = 700, search: str = "portatil", limit: int = 60, playwright_instance = None) -> List[Dict[str, Any]]:
        """Scrapes second-hand and refurbished laptops from OLX Portugal with high-res photos and full specs."""
        api_deals = await asyncio.to_thread(self._scrape_olx_api_sync, min_price, max_price, search, limit)
        if api_deals:
            return api_deals

        results: List[Dict[str, Any]] = []
        encoded_search = search.replace(" ", "+")
        url = (
            f"https://www.olx.pt/tecnologia-e-informatica/computadores-informatica/portateis/q-{encoded_search}/"
            f"?search%5Bfilter_float_price:from%5D={int(min_price)}"
            f"&search%5Bfilter_float_price:to%5D={int(max_price)}"
        )
        logger.info(f"Scraping OLX via Playwright fallback: {url}")

        owns_playwright = playwright_instance is None
        p_cm = None
        if owns_playwright:
            p_cm = async_playwright()
            p = await p_cm.__aenter__()
        else:
            p = playwright_instance

        browser = None
        try:
            browser, page = await self._get_browser_page(p, platform="olx")
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(1500)

            # Progressive Python-driven scroll down to guarantee all cards hydrate lazy-loaded photos
            for i in range(1, 15):
                await page.evaluate(f'window.scrollTo(0, {i * 800});')
                await page.wait_for_timeout(160)

            # Primary: Extract rich SSR data from window.__PRERENDERED_STATE__
            ads_data = await page.evaluate('''() => {
                if (window.__PRERENDERED_STATE__) {
                    try {
                        const parsed = typeof window.__PRERENDERED_STATE__ === 'string' ? JSON.parse(window.__PRERENDERED_STATE__) : window.__PRERENDERED_STATE__;
                        const ads = parsed?.listing?.listing?.ads;
                        if (ads && Array.isArray(ads) && ads.length > 0) {
                            return ads.map(a => {
                                let photo = '';
                                if (a.photos && a.photos.length > 0) {
                                    const p0 = a.photos[0];
                                    photo = typeof p0 === 'string' ? p0 : (p0?.link || p0?.url || '');
                                }
                                return {
                                    title: a.title || '',
                                    price: a.price?.regularPrice?.value || 0,
                                    price_text: a.price?.displayValue || '',
                                    link: a.url || '',
                                    img: photo,
                                    location: a.location?.cityName || a.location?.regionName || 'Portugal',
                                    description: a.description || '',
                                    params: a.params || []
                                };
                            });
                        }
                    } catch(e) {}
                }

                // Fallback: extract from DOM
                const cards = Array.from(document.querySelectorAll('[data-cy="l-card"]'));
                return cards.map(c => {
                    const titleEl = c.querySelector('h6, h4');
                    const priceEl = c.querySelector('[data-testid="ad-price"]');
                    const linkEl = c.querySelector('a');
                    const imgEl = c.querySelector('img');
                    const locEl = c.querySelector('[data-testid="location-date"]');
                    let img = '';
                    if (imgEl) {
                        const src = imgEl.src || '';
                        const dataSrc = imgEl.getAttribute('data-src') || '';
                        const srcset = imgEl.getAttribute('srcset') || '';
                        if (srcset && srcset.includes('apollo.olxcdn.com')) {
                            const parts = srcset.split(',');
                            img = parts[parts.length - 1].trim().split(' ')[0];
                        } else if (src && src.includes('apollo.olxcdn.com')) {
                            img = src;
                        } else if (dataSrc && dataSrc.includes('apollo.olxcdn.com')) {
                            img = dataSrc;
                        } else if (src && !src.includes('no_thumbnail')) {
                            img = src;
                        }
                    }
                    return {
                        title: titleEl ? titleEl.innerText.trim() : '',
                        price_text: priceEl ? priceEl.innerText.trim() : '',
                        link: linkEl ? linkEl.href : '',
                        img: img,
                        location: locEl ? locEl.innerText.trim() : 'Portugal',
                        description: '',
                        params: []
                    };
                });
            }''')

            logger.info(f"Extracted {len(ads_data)} OLX ads with photos")

            for item in ads_data[:limit]:
                try:
                    title = item.get("title", "")
                    if not title:
                        continue

                    price = item.get("price")
                    if not price or price <= 0:
                        price = parse_price(item.get("price_text", ""))
                    if not price or price < (min_price - 50) or price > (max_price + 50):
                        if not price:
                            price = (min_price + max_price) / 2.0

                    link = item.get("link", "")
                    if link and not link.startswith('http'):
                        link = f"https://www.olx.pt{link}"

                    img_url = item.get("img") or None
                    if img_url:
                        if 'no_thumbnail' in img_url:
                            img_url = None
                        elif 'apollo.olxcdn.com' in img_url:
                            img_url = img_url.replace(':443', '')
                            if ';s=' in img_url:
                                img_url = re.sub(r';s=[^&]+', ';s=1000x750', img_url)
                            else:
                                img_url = f"{img_url};s=1000x750"

                    loc_text = item.get("location") or "Portugal"
                    location = loc_text.split(" - ")[0] if " - " in loc_text else loc_text

                    desc = item.get("description", "")
                    params = item.get("params", [])
                    travel = calculate_travel_specs(location, source="OLX")
                    specs = extract_laptop_specs(
                        title, f"{desc} {loc_text}", params, price=price,
                        travel_distance_km=travel.get("travel_distance_km"),
                        travel_label=travel.get("travel_label"),
                        source="OLX"
                    )

                    deal_rating = specs["deal_rating"]
                    if deal_rating not in ["★ The Benchmark 10", "God-Tier VM Host"] and specs["spec_score"] >= 7.5 and price <= (min_price + 150):
                        deal_rating = "Top Value Deal"

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
                        "ram_type": specs["ram_type"],
                        "ram_display": specs["ram_display"],
                        "storage_gb": specs["storage_gb"],
                        "storage_type": specs["storage_type"],
                        "storage_display": specs["storage_display"],
                        "gpu": specs["gpu"],
                        "screen_size": specs["screen_size"],
                        "spec_score": specs["spec_score"],
                        "deal_rating": deal_rating,
                        "raw_snippet": item.get("price_text", ""),
                        "query": search,
                        "cpu_tdp_watts": specs.get("cpu_tdp_watts"),
                        "gpu_tgp_watts": specs.get("gpu_tgp_watts"),
                        "power_peak_watts": specs.get("power_peak_watts"),
                        "power_avg_watts": specs.get("power_avg_watts"),
                        "power_efficiency": specs.get("power_efficiency"),
                        "monthly_cost_eur": specs.get("monthly_cost_eur"),
                        "travel_distance_km": travel.get("travel_distance_km"),
                        "travel_time_min": travel.get("travel_time_min"),
                        "travel_label": travel.get("travel_label"),
                        "contact_status": "uncontacted",
                        "description": desc
                    })
                except Exception as item_err:
                    logger.debug(f"Error parsing OLX card: {item_err}")
        except Exception as e:
            logger.error(f"Error fetching OLX laptops: {e}")
        finally:
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass
            if owns_playwright and p_cm:
                await p_cm.__aexit__(None, None, None)

        return results

    async def scrape_worten(self, min_price: float = 400, max_price: float = 700, search: str = "portatil", limit: int = 50, playwright_instance = None) -> List[Dict[str, Any]]:
        """Scrapes retail, outlet, and refurbished laptops from Worten Portugal with product photos."""
        results: List[Dict[str, Any]] = []
        encoded_search = search.replace(" ", "+")
        url = f"https://www.worten.pt/search?query={encoded_search}&price_from={int(min_price)}&price_to={int(max_price)}"
        logger.info(f"Scraping Worten: {url}")

        owns_playwright = playwright_instance is None
        p_cm = None
        if owns_playwright:
            p_cm = async_playwright()
            p = await p_cm.__aenter__()
        else:
            p = playwright_instance

        browser = None
        try:
            browser, page = await self._get_browser_page(p)
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(3500)

            items_data = await page.evaluate('''() => {
                const list = [];
                const links = Array.from(document.querySelectorAll('a'))
                    .filter(a => a.href.includes('/produtos/portatil-') || a.href.includes('/informatica/computadores/portateis/'));
                
                const seen = new Set();
                links.forEach(a => {
                    const cleanHref = a.href.split('?')[0];
                    if (seen.has(cleanHref)) return;
                    seen.add(cleanHref);
                    
                    const card = a.closest('article, li, .product-card') || a;
                    const text = card.innerText || '';
                    const img = card.querySelector('img');
                    list.push({
                        href: cleanHref,
                        text: text,
                        img: img ? img.src : ''
                    });
                });
                return list;
            }''')

            logger.info(f"Found {len(items_data)} Worten products")

            for item in items_data[:limit]:
                try:
                    raw_text = item.get("text", "")
                    href = item.get("href", "")
                    img_url = item.get("img") or None

                    title = ""
                    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
                    for line in lines:
                        if "portátil" in line.lower() or "laptop" in line.lower():
                            title = line
                            break
                    
                    if not title:
                        slug = href.split("/produtos/")[-1].split("?")[0].replace("-", " ").title()
                        title = slug[:100]

                    price = None
                    m_price = re.search(r'€\s*(\d+)\s*,\s*(\d{2})', raw_text)
                    if m_price:
                        price = float(f"{m_price.group(1)}.{m_price.group(2)}")
                    else:
                        price = parse_price(raw_text)

                    if not price or price < (min_price - 50) or price > (max_price + 50):
                        continue

                    condition = "Novo"
                    if "recondicionado" in raw_text.lower() or "outlet" in raw_text.lower():
                        condition = "Recondicionado"

                    travel = calculate_travel_specs("Worten Portugal", source="Worten")
                    specs = extract_laptop_specs(
                        title, f"{raw_text} {href}", price=float(price),
                        travel_distance_km=travel.get("travel_distance_km"),
                        travel_label=travel.get("travel_label"),
                        source="Worten"
                    )

                    deal_rating = specs["deal_rating"]
                    if deal_rating not in ["★ The Benchmark 10", "God-Tier VM Host"] and specs["spec_score"] >= 7.5 and price <= 650:
                        deal_rating = "Top Value Deal"

                    results.append({
                        "title": title,
                        "price": float(price),
                        "currency": "EUR",
                        "condition": condition,
                        "source": "Worten",
                        "url": href,
                        "image_url": img_url,
                        "location": "Worten Portugal",
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
                        "deal_rating": deal_rating,
                        "raw_snippet": raw_text[:200],
                        "query": search,
                        "cpu_tdp_watts": specs.get("cpu_tdp_watts"),
                        "gpu_tgp_watts": specs.get("gpu_tgp_watts"),
                        "power_peak_watts": specs.get("power_peak_watts"),
                        "power_avg_watts": specs.get("power_avg_watts"),
                        "power_efficiency": specs.get("power_efficiency"),
                        "monthly_cost_eur": specs.get("monthly_cost_eur"),
                        "travel_distance_km": travel.get("travel_distance_km"),
                        "travel_time_min": travel.get("travel_time_min"),
                        "travel_label": travel.get("travel_label"),
                        "contact_status": "uncontacted",
                        "description": raw_text.strip()
                    })
                except Exception as parse_err:
                    logger.debug(f"Error parsing Worten item: {parse_err}")
        except Exception as e:
            logger.error(f"Error fetching Worten laptops: {e}")
        finally:
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass
            if owns_playwright and p_cm:
                await p_cm.__aexit__(None, None, None)

        return results

    async def scrape_facebook_marketplace(
        self,
        min_price: float = 400,
        max_price: float = 700,
        search: str = "portatil",
        cities: Optional[List[str]] = None,
        playwright_instance: Optional[Any] = None,
        limit_per_city: int = 15
    ) -> List[Dict[str, Any]]:
        """Scrapes Facebook Marketplace Portugal for laptop listings across key regional hubs."""
        if cities is None:
            # Primary hub: Leiria (bordering Marinha Grande), followed by Lisbon and Coimbra
            cities = ["leiria", "lisbon", "coimbra"]

        results: List[Dict[str, Any]] = []
        owns_playwright = False
        p_cm = None
        if playwright_instance is None:
            owns_playwright = True
            p_cm = async_playwright()
            p = await p_cm.__aenter__()
        else:
            p = playwright_instance

        browser = None
        try:
            browser, page = await self._get_browser_page(p, platform="facebook")

            for city in cities:
                try:
                    url = f"https://www.facebook.com/marketplace/{city}/search?query={search}"
                    logger.info(f"Scanning Facebook Marketplace: {city} -> {url}")
                    await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    await page.wait_for_timeout(2000)

                    # Dismiss Facebook Cookie Banner if present
                    consent = page.locator('button:has-text("Permitir todos os cookies"), button:has-text("Allow all cookies"), [aria-label*="cookies"], [data-cookiebanner="accept_button"]').first
                    if await consent.count() > 0 and await consent.is_visible():
                        try:
                            await consent.click()
                            await page.wait_for_timeout(1000)
                        except Exception:
                            pass

                    # Scroll down to hydrate photos & listings
                    for _ in range(3):
                        await page.mouse.wheel(0, 1500)
                        await page.wait_for_timeout(350)

                    # Extract listings from DOM
                    items_raw = await page.evaluate('''() => {
                        const anchors = Array.from(document.querySelectorAll('a[href*="/marketplace/item/"]'));
                        return anchors.map(a => {
                            const text = a.innerText || '';
                            const href = a.href || '';
                            const img = a.querySelector('img')?.src || '';
                            return { text, href, img };
                        });
                    }''')

                    logger.info(f"Facebook Marketplace ({city}): Found {len(items_raw)} candidates")

                    city_added = 0
                    for raw in items_raw:
                        if city_added >= limit_per_city:
                            break
                        try:
                            text = raw.get("text", "")
                            lines = [l.strip() for l in text.split("\n") if l.strip()]
                            if len(lines) < 2:
                                continue

                            # Filter metadata/timestamp lines
                            filtered = [l for l in lines if not any(x in l.lower() for x in ['publicado', 'recentemente', 'horas', 'dias', 'grátis', 'disponível'])]

                            # Extract price
                            prices = []
                            for l in filtered:
                                m = re.search(r'(\d+[\d\s.,]*)\s*€', l)
                                if m:
                                    clean = m.group(1).replace(' ', '').replace('.', '').replace(',', '.')
                                    try:
                                        prices.append(float(clean))
                                    except Exception:
                                        pass
                            price = prices[-1] if prices else None
                            if not price or price < (min_price - 50) or price > (max_price + 50):
                                continue

                            # Extract title & location
                            non_prices = [l for l in filtered if not re.search(r'^\d+[\d\s.,]*\s*€$', l)]
                            if not non_prices:
                                continue
                            title = non_prices[0]
                            location = non_prices[-1] if len(non_prices) > 1 else city.title()

                            # Ignore non-laptop items
                            title_lower = title.lower()
                            if any(x in title_lower for x in ['ventilador', 'calha', 'ar condicionado', 'fogão', 'parrilla', 'mochila', 'bolsa']):
                                continue

                            link = raw.get("href", "")
                            if link and "?" in link:
                                link = link.split("?")[0]

                            img_url = raw.get("img") or None

                            travel = calculate_travel_specs(location, source="Facebook")
                            specs = extract_laptop_specs(
                                title, f"{title} {location} Facebook Marketplace", price=price,
                                travel_distance_km=travel.get("travel_distance_km"),
                                travel_label=travel.get("travel_label"),
                                source="Facebook"
                            )

                            deal_rating = specs["deal_rating"]
                            if deal_rating not in ["★ The Benchmark 10", "God-Tier VM Host"] and specs["spec_score"] >= 7.5 and price <= (min_price + 150):
                                deal_rating = "Top Value Deal"

                            results.append({
                                "title": title,
                                "price": float(price),
                                "currency": "EUR",
                                "condition": "Usado",
                                "source": "Facebook",
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
                                "deal_rating": deal_rating,
                                "raw_snippet": text[:200],
                                "description": f"Anúncio no Facebook Marketplace ({location}):\n{text}",
                                "query": search,
                                "cpu_tdp_watts": specs.get("cpu_tdp_watts"),
                                "gpu_tgp_watts": specs.get("gpu_tgp_watts"),
                                "power_peak_watts": specs.get("power_peak_watts"),
                                "power_avg_watts": specs.get("power_avg_watts"),
                                "power_efficiency": specs.get("power_efficiency"),
                                "monthly_cost_eur": specs.get("monthly_cost_eur"),
                                "travel_distance_km": travel.get("travel_distance_km"),
                                "travel_time_min": travel.get("travel_time_min"),
                                "travel_label": travel.get("travel_label"),
                                "contact_status": "uncontacted"
                            })
                            city_added += 1
                        except Exception as item_err:
                            logger.debug(f"Error parsing FB item: {item_err}")
                except Exception as city_err:
                    logger.warning(f"Error scanning Facebook Marketplace for city {city}: {city_err}")
        except Exception as e:
            logger.error(f"Error in Facebook Marketplace scraper: {e}")
        finally:
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass
            if owns_playwright and p_cm:
                await p_cm.__aexit__(None, None, None)

        return results

    def _scrape_cex_sync(
        self,
        min_price: float = 400,
        max_price: float = 700,
        search: str = "portatil",
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Synchronous worker for CeX Portugal Algolia API."""
        results: List[Dict[str, Any]] = []
        url = "https://search.webuy.io/1/indexes/*/queries?x-algolia-agent=Algolia%20for%20JavaScript%20(4.22.1)%3B%20Browser&x-algolia-api-key=bf79f2b6699e60a18ae330a1248b452c&x-algolia-application-id=LNNFEEWZVA"
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Origin": "https://pt.webuy.com",
            "Referer": "https://pt.webuy.com/",
            "Content-Type": "application/json"
        }

        q_clean = (search or "").strip().lower()
        q_param = "" if q_clean in ["portatil", "portateis", "portáteis", "laptop", "computador"] else search.strip()

        # Prioritize Windows category 1051 unless query specifically mentions Apple/Mac
        if any(x in q_clean for x in ["macbook", "apple", "mac "]):
            categories = ["categoryId:850"]
        else:
            categories = ["categoryId:1051", "categoryId:850"]

        facet_filters = [categories, ["availability:Disponível em loja", "availability:Disponível online"]]
        params_str = f"query={q_param}&hitsPerPage={min(limit, 100)}&facetFilters={json.dumps(facet_filters)}&numericFilters=[\"sellPrice>={int(min_price)}\",\"sellPrice<={int(max_price)}\"]"

        payload = {
            "requests": [
                {
                    "indexName": "prod_cex_pt",
                    "params": params_str
                }
            ]
        }

        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                hits = data.get("results", [{}])[0].get("hits", [])
                logger.info(f"CeX API returned {len(hits)} matching laptops")

                for hit in hits:
                    try:
                        box_name = hit.get("boxName", "")
                        price = float(hit.get("sellPrice", 0))
                        box_id = hit.get("boxId", "")
                        if not box_name or price <= 0 or not box_id:
                            continue

                        stores = hit.get("stores", [])
                        in_online = bool(hit.get("inStockOnline", 0))
                        if not stores and not in_online:
                            continue

                        img_urls = hit.get("imageUrls", {})
                        img_url = img_urls.get("large") or img_urls.get("medium") or img_urls.get("small")
                        link = f"https://pt.webuy.com/product-detail?id={box_id}"

                        # Condition grading
                        grade = hit.get("gradeId", "")
                        if "/A" in box_name or grade == "A":
                            condition = "Recondicionado Grade A"
                        elif "/B" in box_name or grade == "B":
                            condition = "Recondicionado Grade B"
                        elif "/C" in box_name or grade == "C":
                            condition = "Recondicionado Grade C"
                        else:
                            condition = "Recondicionado (Garantia 5 Anos)"

                        # Location & stock determination
                        if any("leiria" in s.lower() for s in stores):
                            location = "Leiria (Loja CeX LeiriaShopping)"
                        elif in_online:
                            stores_hint = f" ({stores[0]})" if stores else ""
                            location = f"CeX Online / Loja{stores_hint}"
                        elif stores:
                            location = f"CeX {stores[0]}"
                        else:
                            location = "CeX Portugal (Online)"

                        travel = calculate_travel_specs(location, source="CeX")
                        specs = extract_laptop_specs(
                            box_name, f"{box_name} CeX Portugal Recondicionado Garantia 5 Anos", price=price,
                            travel_distance_km=travel.get("travel_distance_km"),
                            travel_label=travel.get("travel_label"),
                            source="CeX"
                        )

                        deal_rating = specs["deal_rating"]
                        if deal_rating not in ["★ The Benchmark 10", "God-Tier VM Host"] and specs["spec_score"] >= 7.5 and price <= (min_price + 150):
                            deal_rating = "Top Value Deal"

                        stores_str = ", ".join(stores) if stores else "Envio Central CeX"
                        online_str = "Sim (24-48h Envio Nacional)" if in_online else "Apenas em Loja Física"
                        desc = f"Artigo Recondicionado CeX Portugal com 5 Anos de Garantia Total.\nDisponibilidade em Loja: {stores_str}\nEntrega Online: {online_str}\nReferência CeX: {box_id}"

                        results.append({
                            "title": box_name,
                            "price": price,
                            "currency": "EUR",
                            "condition": condition,
                            "source": "CeX",
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
                            "deal_rating": deal_rating,
                            "raw_snippet": f"{price}€ | Garantia 5 Anos CeX | {location}",
                            "query": search,
                            "cpu_tdp_watts": specs.get("cpu_tdp_watts"),
                            "gpu_tgp_watts": specs.get("gpu_tgp_watts"),
                            "power_peak_watts": specs.get("power_peak_watts"),
                            "power_avg_watts": specs.get("power_avg_watts"),
                            "power_efficiency": specs.get("power_efficiency"),
                            "monthly_cost_eur": specs.get("monthly_cost_eur"),
                            "travel_distance_km": travel.get("travel_distance_km"),
                            "travel_time_min": travel.get("travel_time_min"),
                            "travel_label": travel.get("travel_label"),
                            "contact_status": "uncontacted",
                            "description": desc
                        })
                    except Exception as item_err:
                        logger.debug(f"Error parsing CeX hit: {item_err}")
        except Exception as e:
            logger.error(f"Error querying CeX Algolia API: {e}")

        return results

    async def scrape_cex(
        self,
        min_price: float = 400,
        max_price: float = 700,
        search: str = "portatil",
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Scrapes CeX Portugal (pt.webuy.com) for refurbished laptops with 5-year warranty."""
        return await asyncio.to_thread(self._scrape_cex_sync, min_price, max_price, search, limit)

    def _scrape_pcdiga_sync(
        self,
        min_price: float = 400,
        max_price: float = 700,
        search: str = "portatil",
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Synchronous worker for PCDiga Typesense cluster API."""
        results: List[Dict[str, Any]] = []
        url = "https://kjvn6r1caotq07dlp.a1.typesense.net/multi_search?use_cache=true&x-typesense-api-key=SLlLtgm4Ot1cFCnJZunQlKbN4O6ln3tt"
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Origin": "https://www.pcdiga.com",
            "Referer": "https://www.pcdiga.com/",
            "Content-Type": "application/json"
        }

        q_clean = (search or "").strip().lower()
        q_param = "*" if q_clean in ["portatil", "portateis", "portáteis", "laptop", "computador"] else search.strip()
        filter_by = f"categories.name:=[`Computadores Portáteis`] && final_price.minimum_price.final_price.value:>={int(min_price)} && final_price.minimum_price.final_price.value:<={int(max_price)} && visibility:=[true]"

        payload = {
            "searches": [
                {
                    "collection": "productCollectionProd",
                    "q": q_param,
                    "query_by": "name,sku,description",
                    "filter_by": filter_by,
                    "per_page": min(limit, 50)
                }
            ]
        }

        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                hits = data.get("results", [{}])[0].get("hits", [])
                logger.info(f"PCDiga Typesense API returned {len(hits)} matching laptops")

                for hit in hits:
                    try:
                        doc = hit.get("document", {})
                        name = doc.get("name", "")
                        price_obj = doc.get("final_price", {}).get("minimum_price", {}).get("final_price", {})
                        price = float(price_obj.get("value", 0)) if price_obj else 0.0

                        if not name or price <= 0:
                            continue

                        # Filter out accessories or non-laptops if any slipped through
                        name_lower = name.lower()
                        if any(x in name_lower for x in ["projetor", "painel solar", "mochila", "bolsa", "carregador", "docking", "suporte"]):
                            continue

                        url_key = doc.get("url_key", "")
                        link = f"https://www.pcdiga.com/{url_key}" if url_key else "https://www.pcdiga.com"

                        # Image extraction
                        thumb = doc.get("thumbnail") or {}
                        img_url = thumb.get("url")
                        if not img_url:
                            media = doc.get("media_gallery") or []
                            if media and isinstance(media, list) and len(media) > 0:
                                img_url = media[0].get("url")

                        # Warehouse & store stock detection
                        warehouses = doc.get("warehouses", [])
                        leiria_in_stock = False
                        wh_in_stock = []
                        for w in warehouses:
                            slug = w.get("warehouseSlug", "")
                            status = w.get("status", "")
                            w_name = w.get("warehouseName", slug)
                            if status == "IN_STOCK":
                                wh_in_stock.append(w_name)
                                if slug == "loja-leiria":
                                    leiria_in_stock = True

                        if leiria_in_stock:
                            location = "Leiria (Loja PCDIGA - Em Stock)"
                        else:
                            location = "PCDIGA Online (Envio 24h / Encomenda)"

                        travel = calculate_travel_specs(location, source="PCDIGA")

                        condition = "Novo (Garantia 3 Anos)"
                        if "recondicionado" in name_lower or "outlet" in name_lower:
                            condition = "Recondicionado"

                        desc_html = doc.get("longdescription", "")
                        desc_clean = re.sub(r'<[^>]+>', ' ', desc_html).strip()
                        desc_clean = re.sub(r'\s+', ' ', desc_clean)

                        specs = extract_laptop_specs(
                            name, f"{name} {desc_clean}", price=price,
                            travel_distance_km=travel.get("travel_distance_km"),
                            travel_label=travel.get("travel_label"),
                            source="PCDIGA"
                        )

                        deal_rating = specs["deal_rating"]
                        if deal_rating not in ["★ The Benchmark 10", "God-Tier VM Host"] and specs["spec_score"] >= 7.5 and price <= (min_price + 150):
                            deal_rating = "Top Value Deal"

                        stock_status_str = "EM STOCK na Loja de Leiria (Estrada da Estação - ~11 min de Marinha Grande)" if leiria_in_stock else "Disponível online para entrega ou levantamento em loja"
                        stores_list_str = ", ".join(wh_in_stock) if wh_in_stock else "Armazém Central"
                        description = f"Artigo PCDIGA Portugal (Garantia Oficial 3 Anos).\nDisponibilidade: {stock_status_str}\nLojas com stock imediato: {stores_list_str}\n\nEspecificações Técnicas:\n{desc_clean[:1200]}"

                        results.append({
                            "title": name,
                            "price": price,
                            "currency": "EUR",
                            "condition": condition,
                            "source": "PCDIGA",
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
                            "deal_rating": deal_rating,
                            "raw_snippet": f"{price}€ | PCDIGA Portugal | {location}",
                            "query": search,
                            "cpu_tdp_watts": specs.get("cpu_tdp_watts"),
                            "gpu_tgp_watts": specs.get("gpu_tgp_watts"),
                            "power_peak_watts": specs.get("power_peak_watts"),
                            "power_avg_watts": specs.get("power_avg_watts"),
                            "power_efficiency": specs.get("power_efficiency"),
                            "monthly_cost_eur": specs.get("monthly_cost_eur"),
                            "travel_distance_km": travel.get("travel_distance_km"),
                            "travel_time_min": travel.get("travel_time_min"),
                            "travel_label": travel.get("travel_label"),
                            "contact_status": "uncontacted",
                            "description": description
                        })
                    except Exception as item_err:
                        logger.debug(f"Error parsing PCDIGA hit: {item_err}")
        except Exception as e:
            logger.error(f"Error querying PCDIGA Typesense API: {e}")

        return results

    async def scrape_pcdiga(
        self,
        min_price: float = 400,
        max_price: float = 700,
        search: str = "portatil",
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Scrapes PCDIGA Portugal for laptops, detecting Leiria store stock."""
        return await asyncio.to_thread(self._scrape_pcdiga_sync, min_price, max_price, search, limit)

    def _scrape_amazon_sync(
        self,
        min_price: float = 300,
        max_price: float = 800,
        search: str = "portatil",
        limit: int = 40
    ) -> List[Dict[str, Any]]:
        """Scrapes Amazon.es for laptops and warehouse deals with free shipping to Portugal."""
        results: List[Dict[str, Any]] = []
        try:
            from bs4 import BeautifulSoup
            query_encoded = urllib.parse.quote(search)
            min_cents = int(min_price * 100)
            max_cents = int(max_price * 100)
            url = f"https://www.amazon.es/s?k={query_encoded}&rh=p_36%3A{min_cents}-{max_cents}"
            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.8",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as response:
                html = response.read().decode("utf-8", errors="replace")
                soup = BeautifulSoup(html, "html.parser")
                items = soup.select("div[data-asin]")
                for it in items:
                    asin = it.get("data-asin", "").strip()
                    if not asin:
                        continue
                    title_elem = it.select_one("h2 span")
                    if not title_elem:
                        continue
                    title = title_elem.get_text(strip=True)
                    price_whole = it.select_one(".a-price-whole")
                    price_fraction = it.select_one(".a-price-fraction")
                    if not price_whole:
                        continue
                    raw_p = price_whole.get_text(strip=True).replace(".", "").replace(",", "")
                    if price_fraction:
                        raw_p = f"{raw_p}.{price_fraction.get_text(strip=True)}"
                    try:
                        price = float(raw_p)
                    except ValueError:
                        continue
                    if price < min_price or price > max_price:
                        continue

                    link_elem = it.select_one("h2 a")
                    link = f"https://www.amazon.es/dp/{asin}" if not link_elem else f"https://www.amazon.es{link_elem.get('href', '')}"
                    img_elem = it.select_one("img.s-image")
                    img_url = img_elem.get("src") if img_elem else None

                    specs = extract_laptop_specs(title, title, price=price, source="Amazon")
                    results.append({
                        "title": title,
                        "price": float(price),
                        "currency": "EUR",
                        "condition": "Novo / Recondicionado",
                        "source": "Amazon",
                        "url": link,
                        "image_url": img_url,
                        "location": "Amazon Prime / Portugal",
                        "brand": specs.get("brand", "Generic"),
                        "cpu": specs.get("cpu", "Multi-Core"),
                        "ram_gb": specs.get("ram_gb", 16),
                        "ram_type": specs.get("ram_type", "DDR4"),
                        "ram_display": specs.get("ram_display", "16 GB"),
                        "storage_gb": specs.get("storage_gb", 512),
                        "storage_type": specs.get("storage_type", "SSD"),
                        "storage_display": specs.get("storage_display", "512 GB SSD"),
                        "gpu": specs.get("gpu", "Integrated"),
                        "screen_size": specs.get("screen_size", "15.6\""),
                        "spec_score": specs.get("spec_score", 7.0),
                        "deal_rating": specs.get("deal_rating") or "Amazon Value",
                        "description": f"Amazon.es Deal (ASIN: {asin})"
                    })
                    if len(results) >= limit:
                        break
        except Exception as e:
            logger.warning(f"Amazon scrape notice: {e}")
        return results

    async def scrape_amazon(
        self,
        min_price: float = 300,
        max_price: float = 800,
        search: str = "portatil",
        limit: int = 40
    ) -> List[Dict[str, Any]]:
        """Scrapes Amazon.es for laptops and deals."""
        return await asyncio.to_thread(self._scrape_amazon_sync, min_price, max_price, search, limit)

    def _scrape_globaldata_sync(
        self,
        min_price: float = 400,
        max_price: float = 700,
        search: str = "portatil",
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Scrapes GlobalData Portugal (globaldata.pt) using Demandware product catalog."""
        results: List[Dict[str, Any]] = []
        try:
            from bs4 import BeautifulSoup
            url = "https://www.globaldata.pt/on/demandware.store/Sites-Globaldata-Site/pt_PT/Search-UpdateGrid?cgid=computadores-portateis"
            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.8",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                html = resp.read().decode("utf-8", errors="replace")
                soup = BeautifulSoup(html, "html.parser")
                tiles = soup.select(".product")
                for t in tiles:
                    link_el = t.select_one(".pdp-link a")
                    if not link_el:
                        continue
                    title = link_el.get_text(strip=True)
                    href = link_el.get("href", "")
                    if href.startswith("/"):
                        href = f"https://www.globaldata.pt{href}"

                    price_el = t.select_one(".sales .value")
                    if not price_el:
                        continue
                    raw_p = price_el.get_text(strip=True)
                    clean_p = re.sub(r"[^\d,.]", "", raw_p).replace(".", "").replace(",", ".")
                    try:
                        price = float(clean_p)
                    except ValueError:
                        continue

                    if price < min_price or price > max_price:
                        continue

                    img_el = t.select_one("img.tile-image, img")
                    img_url = img_el.get("src") or img_el.get("data-src") if img_el else None
                    if img_url and img_url.startswith("/"):
                        img_url = f"https://www.globaldata.pt{img_url}"

                    specs = extract_laptop_specs(title, title, price=price, source="GlobalData")
                    results.append({
                        "title": title,
                        "price": float(price),
                        "currency": "EUR",
                        "condition": "Novo (Garantia Oficial 3 Anos)",
                        "source": "GlobalData",
                        "url": href,
                        "image_url": img_url,
                        "location": "GlobalData PT (Envio Nacional)",
                        "brand": specs.get("brand", "Outro"),
                        "cpu": specs.get("cpu", "Multi-Core"),
                        "ram_gb": specs.get("ram_gb", 16),
                        "ram_type": specs.get("ram_type", "DDR4"),
                        "ram_display": specs.get("ram_display", "16 GB"),
                        "storage_gb": specs.get("storage_gb", 512),
                        "storage_type": specs.get("storage_type", "SSD"),
                        "storage_display": specs.get("storage_display", "512 GB SSD"),
                        "gpu": specs.get("gpu", "Integrated"),
                        "screen_size": specs.get("screen_size", "15.6\""),
                        "spec_score": specs.get("spec_score", 7.0),
                        "deal_rating": specs.get("deal_rating") or "GlobalData Deal",
                        "description": f"Artigo novo GlobalData PT. Link oficial: {href}"
                    })
                    if len(results) >= limit:
                        break
        except Exception as e:
            logger.warning(f"GlobalData scrape notice: {e}")
        return results

    async def scrape_globaldata(
        self,
        min_price: float = 400,
        max_price: float = 700,
        search: str = "portatil",
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Scrapes GlobalData Portugal (globaldata.pt) for laptops."""
        return await asyncio.to_thread(self._scrape_globaldata_sync, min_price, max_price, search, limit)

    async def scrape_pccomponentes(
        self,
        min_price: float = 400,
        max_price: float = 700,
        search: str = "portatil",
        limit: int = 50,
        playwright_instance = None
    ) -> List[Dict[str, Any]]:
        """Scrapes PcComponentes Portugal (pccomponentes.pt) with Playwright & Cloudflare bypass."""
        results: List[Dict[str, Any]] = []
        owns_pw = playwright_instance is None
        p_cm = None
        if owns_pw:
            p_cm = async_playwright()
            p = await p_cm.__aenter__()
        else:
            p = playwright_instance

        browser = None
        try:
            browser, page = await self._get_browser_page(p, platform="pccomponentes")
            url = f"https://www.pccomponentes.pt/portateis?price_from={int(min_price)}&price_to={int(max_price)}"
            await page.goto(url, wait_until="domcontentloaded", timeout=25000)
            await page.wait_for_timeout(2000)

            cards = await page.evaluate('''() => {
                const items = document.querySelectorAll('article[data-product-id], .product-card, a[data-product-name]');
                return Array.from(items).map(el => {
                    const title = el.getAttribute('data-product-name') || el.querySelector('h3, .title, .product-card__title')?.innerText || '';
                    const price = el.getAttribute('data-product-price') || el.querySelector('.price, .product-card__price')?.innerText || '';
                    const link = el.querySelector('a')?.href || el.getAttribute('href') || '';
                    const img = el.querySelector('img')?.src || '';
                    return { title, price, link, img };
                });
            }''')

            for c in cards:
                title = c.get("title", "").strip()
                if not title:
                    continue
                raw_p = re.sub(r"[^\d,.]", "", c.get("price", "")).replace(".", "").replace(",", ".")
                try:
                    price = float(raw_p)
                except ValueError:
                    continue
                if price < min_price or price > max_price:
                    continue

                link = c.get("link", "")
                if link and not link.startswith("http"):
                    link = f"https://www.pccomponentes.pt{link}"

                specs = extract_laptop_specs(title, title, price=price, source="PcComponentes")
                results.append({
                    "title": title,
                    "price": float(price),
                    "currency": "EUR",
                    "condition": "Novo / Recondicionado",
                    "source": "PcComponentes",
                    "url": link or f"https://www.pccomponentes.pt/search?query={title}",
                    "image_url": c.get("img"),
                    "location": "PcComponentes (Envio 24h Portugal)",
                    "brand": specs.get("brand", "Outro"),
                    "cpu": specs.get("cpu", "Multi-Core"),
                    "ram_gb": specs.get("ram_gb", 16),
                    "ram_type": specs.get("ram_type", "DDR4"),
                    "ram_display": specs.get("ram_display", "16 GB"),
                    "storage_gb": specs.get("storage_gb", 512),
                    "storage_type": specs.get("storage_type", "SSD"),
                    "storage_display": specs.get("storage_display", "512 GB SSD"),
                    "gpu": specs.get("gpu", "Integrated"),
                    "screen_size": specs.get("screen_size", "15.6\""),
                    "spec_score": specs.get("spec_score", 7.0),
                    "deal_rating": specs.get("deal_rating") or "PcComponentes Deal",
                    "description": f"Artigo PcComponentes. Link oficial: {link}"
                })
                if len(results) >= limit:
                    break
        except Exception as e:
            logger.warning(f"PcComponentes scrape notice: {e}")
        finally:
            if browser:
                await browser.close()
            if owns_pw and p_cm:
                await p_cm.__aexit__(None, None, None)
        return results

    async def run_scrape_job(
        self,
        min_price: float = 400,
        max_price: float = 700,
        search: str = "portatil",
        sources: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Runs scrape across configured sources with parallel fast API execution and low-latency browser extraction."""
        if sources is None:
            sources = ["olx", "facebook", "amazon", "worten", "cex", "pcdiga", "pccomponentes", "globaldata"]

        all_deals: List[Dict[str, Any]] = []

        if self.is_aborted:
            return {"total_found": 0, "saved_count": 0, "sources": sources}

        # 1. Fast API & HTTP sources running in PARALLEL via asyncio.gather (~1.5s - 2.5s total)
        fast_tasks = []
        if "olx" in sources:
            fast_tasks.append(("olx", self.scrape_olx(min_price=min_price, max_price=max_price, search=search)))
        if "amazon" in sources:
            fast_tasks.append(("amazon", self.scrape_amazon(min_price=min_price, max_price=max_price, search=search)))
        if "cex" in sources:
            fast_tasks.append(("cex", self.scrape_cex(min_price=min_price, max_price=max_price, search=search)))
        if "pcdiga" in sources:
            fast_tasks.append(("pcdiga", self.scrape_pcdiga(min_price=min_price, max_price=max_price, search=search)))
        if "globaldata" in sources:
            fast_tasks.append(("globaldata", self.scrape_globaldata(min_price=min_price, max_price=max_price, search=search)))
        if "pccomponentes" in sources:
            fast_tasks.append(("pccomponentes", self.scrape_pccomponentes(min_price=min_price, max_price=max_price, search=search)))

        if fast_tasks:
            logger.info(f"Running {len(fast_tasks)} fast API sources in parallel...")
            fast_results = await asyncio.gather(*(t[1] for t in fast_tasks), return_exceptions=True)
            for (source_name, _), res in zip(fast_tasks, fast_results):
                if isinstance(res, Exception):
                    logger.error(f"Error scraping {source_name}: {res}")
                elif isinstance(res, list):
                    all_deals.extend(res)
                    logger.info(f"{source_name.upper()} returned {len(res)} deals")

        if self.is_aborted:
            return {"total_found": len(all_deals), "saved_count": 0, "sources": sources}

        # 2. Browser-rendered sources: Worten, Facebook Marketplace (and OLX only if REST API returned 0 deals)
        olx_needs_browser = "olx" in sources and not any(d.get("source") == "OLX" for d in all_deals)
        browser_sources = [s for s in sources if s in ["worten", "facebook"]]
        if olx_needs_browser:
            browser_sources.append("olx")

        if browser_sources and not self.is_aborted:
            async def _execute_browser_scrape():
                async with async_playwright() as p:
                    if "olx" in browser_sources and not self.is_aborted:
                        olx_deals = await self.scrape_olx(min_price=min_price, max_price=max_price, search=search, playwright_instance=p)
                        all_deals.extend(olx_deals)

                    if "worten" in browser_sources and not self.is_aborted:
                        worten_deals = await self.scrape_worten(min_price=min_price, max_price=max_price, search=search, playwright_instance=p)
                        all_deals.extend(worten_deals)

                    if "facebook" in browser_sources and not self.is_aborted:
                        fb_deals = await self.scrape_facebook_marketplace(min_price=min_price, max_price=max_price, search=search, playwright_instance=p)
                        all_deals.extend(fb_deals)

            try:
                # 25-second maximum browser timeout to prevent system freezes
                await asyncio.wait_for(_execute_browser_scrape(), timeout=25)
            except asyncio.TimeoutError:
                logger.warning("[!] 25-second timeout reached in browser scraper. Continuing with gathered deals.")
            except asyncio.CancelledError:
                logger.info("Browser scrape task cancelled.")
                raise
            except Exception as err:
                logger.error(f"[!] Error during browser scrape execution: {err}")

        saved_count = 0
        if all_deals and not self.is_aborted:
            try:
                saved_count = await asyncio.to_thread(insert_or_update_laptops_batch, all_deals)
            except Exception as e:
                logger.error(f"Failed to batch save laptops: {e}")

        logger.info(f"Laptop scrape complete. Found {len(all_deals)}, successfully saved {saved_count}")
        return {
            "total_found": len(all_deals),
            "saved_count": saved_count,
            "min_price": min_price,
            "max_price": max_price,
            "sources": sources
        }
