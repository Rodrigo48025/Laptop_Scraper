import math
from typing import Dict, Any, Tuple, Optional

# User's home base: Marinha Grande (Leiria District, Portugal)
DEFAULT_ORIGIN_NAME = "Marinha Grande"
DEFAULT_ORIGIN_COORDS = (39.749, -8.933)

# Exhaustive coordinate mapping for Portuguese parishes, municipalities, and key regions
PORTUGUESE_LOCATIONS: Dict[str, Tuple[float, float]] = {
    # District of Leiria & Central Coast (Immediate proximity)
    "marinha grande": (39.749, -8.933),
    "leiria / marinha grande": (39.749, -8.933),
    "leiria": (39.744, -8.807),
    "batalha": (39.660, -8.824),
    "alcobaça": (39.553, -8.977),
    "nazaré": (39.601, -9.071),
    "pombal": (39.916, -8.629),
    "porto de mós": (39.602, -8.818),
    "fátima": (39.617, -8.652),
    "ourém": (39.642, -8.578),
    "piedade": (39.642, -8.578), # Nossa Senhora da Piedade (Ourém)
    "caldas da rainha": (39.403, -9.136),
    "óbidos": (39.360, -9.157),
    "peniche": (39.355, -9.381),
    "figueira da foz": (40.150, -8.857),

    # Coimbra & Central Inland
    "coimbra": (40.203, -8.410),
    "condeixa": (40.114, -8.497),
    "montemor-o-velho": (40.174, -8.682),
    "catanhede": (40.346, -8.594),
    "lousã": (40.110, -8.246),
    "tomar": (39.603, -8.409),
    "torres novas": (39.479, -8.539),
    "entroncamento": (39.465, -8.468),
    "abrantes": (39.463, -8.198),
    "santarém": (39.236, -8.686),
    "rio maior": (39.336, -8.936),
    "cartaxo": (39.160, -8.787),
    "almeirim": (39.208, -8.629),
    "samora correia": (38.933, -8.871),
    "benavente": (38.981, -8.807),

    # Aveiro & Viseu
    "aveiro": (40.640, -8.653),
    "glória": (40.640, -8.653),
    "vera cruz": (40.640, -8.653),
    "são bernardo": (40.618, -8.636),
    "ílhavo": (40.600, -8.666),
    "águeda": (40.575, -8.444),
    "albergaria": (40.693, -8.480),
    "albergaria-a-velha": (40.693, -8.480),
    "valmaior": (40.693, -8.480),
    "ovar": (40.859, -8.625),
    "estarreja": (40.753, -8.570),
    "oliveira de azeméis": (40.838, -8.476),
    "são joão da madeira": (40.901, -8.491),
    "santa maria da feira": (40.925, -8.542),
    "viseu": (40.657, -7.914),

    # Greater Lisbon (Metropolitana de Lisboa)
    "lisboa": (38.722, -9.139),
    "grande lisboa": (38.722, -9.139),
    "área metropolitana de lisboa": (38.722, -9.139),
    "area metropolitana de lisboa": (38.722, -9.139),
    "lumiar": (38.773, -9.159),
    "areeiro": (38.742, -9.133),
    "olivais": (38.770, -9.112),
    "estrela": (38.713, -9.160),
    "ajuda": (38.709, -9.198),
    "benfica": (38.750, -9.200),
    "alvalade": (38.753, -9.144),
    "campo de ourique": (38.718, -9.165),
    "parque das nações": (38.768, -9.094),
    "odivelas": (38.793, -9.182),
    "ramada": (38.800, -9.190),
    "caneças": (38.810, -9.210),
    "amadora": (38.759, -9.224),
    "alfragide": (38.735, -9.221),
    "águas livres": (38.755, -9.230),
    "damaia": (38.746, -9.217),
    "reboleira": (38.752, -9.224),
    "sintra": (38.803, -9.381),
    "queluz": (38.756, -9.254),
    "belas": (38.776, -9.261),
    "casal de cambra": (38.796, -9.232),
    "cacém": (38.770, -9.300),
    "massamá": (38.755, -9.278),
    "rio de mouro": (38.784, -9.333),
    "algueirão": (38.799, -9.340),
    "mem martins": (38.798, -9.344),
    "oeiras": (38.697, -9.301),
    "algés": (38.700, -9.230),
    "linda-a-velha": (38.714, -9.241),
    "cruz quebrada": (38.701, -9.253),
    "dafundo": (38.703, -9.244),
    "caxias": (38.702, -9.274),
    "paço de arcos": (38.695, -9.294),
    "porto salvo": (38.721, -9.303),
    "barcarena": (38.732, -9.284),
    "carnaxide": (38.727, -9.242),
    "cascais": (38.697, -9.421),
    "estoril": (38.706, -9.397),
    "são domingos de rana": (38.712, -9.336),
    "carcavelos": (38.686, -9.335),
    "parede": (38.688, -9.356),
    "alhabra": (38.730, -9.370),
    "loures": (38.831, -9.167),
    "sacavém": (38.793, -9.106),
    "moscavide": (38.777, -9.102),
    "vila franca de xira": (38.955, -8.990),
    "alverca": (38.898, -9.040),
    "póvoa de santa iria": (38.862, -9.068),
    "mafra": (38.937, -9.327),
    "ericeira": (38.963, -9.417),
    "torres vedras": (39.091, -9.260),

    # South Bay (Margem Sul & Setúbal Peninsula)
    "almada": (38.680, -9.158),
    "cacilhas": (38.686, -9.145),
    "costa da caparica": (38.644, -9.237),
    "laranjeiro": (38.660, -9.158),
    "corroios": (38.643, -9.153),
    "seixal": (38.647, -9.103),
    "amora": (38.629, -9.118),
    "barreiro": (38.663, -9.073),
    "alto do seixalinho": (38.650, -9.065),
    "santo andré": (38.655, -9.060),
    "verderena": (38.655, -9.060),
    "moita": (38.651, -8.990),
    "montijo": (38.706, -8.974),
    "afonsoeiro": (38.695, -8.955),
    "alcochete": (38.756, -8.960),
    "palmela": (38.568, -8.903),
    "setúbal": (38.524, -8.893),
    "sesimbra": (38.444, -9.101),

    # Greater Porto (Grande Porto & Entre Douro e Vouga)
    "porto": (41.157, -8.629),
    "grande porto": (41.157, -8.629),
    "área metropolitana do porto": (41.157, -8.629),
    "area metropolitana do porto": (41.157, -8.629),
    "aldoar": (41.171, -8.674),
    "foz do douro": (41.151, -8.675),
    "foz": (41.151, -8.675),
    "nevogilde": (41.162, -8.680),
    "ramalde": (41.172, -8.643),
    "cedofeita": (41.155, -8.618),
    "bonfim": (41.150, -8.598),
    "paranhos": (41.175, -8.605),
    "campanhã": (41.151, -8.584),
    "gaia": (41.133, -8.617),
    "vila nova de gaia": (41.133, -8.617),
    "santa marinha": (41.130, -8.618),
    "afurada": (41.144, -8.650),
    "santa marinha e são pedro da afurada": (41.130, -8.618),
    "são pedro da afurada": (41.144, -8.650),
    "canidelo": (41.130, -8.658),
    "arcozelo": (41.050, -8.646),
    "mafamude": (41.125, -8.606),
    "canelas": (41.087, -8.599),
    "valadares": (41.096, -8.638),
    "grijó": (41.033, -8.577),
    "matosinhos": (41.182, -8.687),
    "custóias": (41.200, -8.650),
    "leça do balio": (41.210, -8.630),
    "leça da palmeira": (41.190, -8.695),
    "leça": (41.190, -8.640),
    "guifões": (41.196, -8.670),
    "senhora da hora": (41.187, -8.653),
    "são mamede": (41.192, -8.613),
    "são mamede de infesta": (41.192, -8.613),
    "maia": (41.235, -8.621),
    "cidade da maia": (41.235, -8.621),
    "águas santas": (41.208, -8.583),
    "castelo da maia": (41.265, -8.615),
    "moreira": (41.246, -8.665),
    "gondomar": (41.144, -8.532),
    "são cosme": (41.144, -8.532),
    "valbom": (41.130, -8.560),
    "jovim": (41.110, -8.520),
    "rio tinto": (41.178, -8.558),
    "baguim do monte": (41.192, -8.541),
    "valongo": (41.190, -8.498),
    "alfena": (41.235, -8.528),
    "ermesinde": (41.216, -8.553),
    "paredes": (41.208, -8.330),
    "penafiel": (41.206, -8.283),
    "póvoa de varzim": (41.383, -8.761),
    "vila do conde": (41.354, -8.743),
    "santo tirso": (41.343, -8.473),
    "trofa": (41.336, -8.559),
    "amarante": (41.272, -8.077),
    "marco": (41.185, -8.148),
    "marco de canaveses": (41.185, -8.148),

    # Minho (Braga, Guimarães, Viana)
    "famalicão": (41.408, -8.519),
    "vila nova de famalicão": (41.408, -8.519),
    "calendário": (41.400, -8.520),
    "guimarães": (41.442, -8.296),
    "ponte": (41.468, -8.330),
    "creixomil": (41.436, -8.312),
    "urgeses": (41.428, -8.291),
    "braga": (41.550, -8.426),
    "maximinos": (41.545, -8.432),
    "cividade": (41.549, -8.429),
    "sé": (41.550, -8.428),
    "são josé": (41.548, -8.419),
    "são lázaro": (41.548, -8.419),
    "são joão do souto": (41.551, -8.425),
    "barcelos": (41.531, -8.618),
    "esposende": (41.533, -8.783),
    "viana do castelo": (41.694, -8.830),

    # Alentejo & Central Inland
    "évora": (38.571, -7.907),
    "bacelo": (38.583, -7.912),
    "senhora da saúde": (38.571, -7.907),
    "saúde": (38.571, -7.907),
    "beja": (38.015, -7.865),
    "elvas": (38.881, -7.163),
    "portalegre": (39.293, -7.431),
    "castelo branco": (39.822, -7.493),
    "covilhã": (40.283, -7.504),
    "guarda": (40.537, -7.268),

    # Algarve
    "faro": (37.019, -7.930),
    "portimão": (37.138, -8.538),
    "lagos": (37.102, -8.673),
    "albufeira": (37.089, -8.251),
    "olhão": (37.028, -7.841),
    "tavira": (37.126, -7.649),
}

def haversine_distance(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
    """Calculates great-circle distance in kilometers."""
    R = 6371.0 # Earth radius in km
    lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
    lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2.0)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

def get_origin_coords_for_location(loc_name: Optional[str]) -> Tuple[Tuple[float, float], str]:
    if not loc_name:
        return DEFAULT_ORIGIN_COORDS, DEFAULT_ORIGIN_NAME
    loc_clean = loc_name.lower().strip()
    for key, coords in sorted(PORTUGUESE_LOCATIONS.items(), key=lambda x: len(x[0]), reverse=True):
        if key in loc_clean or loc_clean in key:
            return coords, key.title()
    return DEFAULT_ORIGIN_COORDS, DEFAULT_ORIGIN_NAME

def calculate_travel_specs(
    location_str: Optional[str],
    source: str = "OLX",
    origin_coords: Tuple[float, float] = DEFAULT_ORIGIN_COORDS,
    origin_name: str = DEFAULT_ORIGIN_NAME
) -> Dict[str, Any]:
    """
    Computes road distance, driving time, tier, and formatted label from user origin.
    Accounts for Portuguese highway network (A1, A8, A17, A29, A2) routing factor (~1.25x Haversine).
    """
    source_lower = (source or "").lower()
    loc_lower = (location_str or "").lower().strip()

    # Worten delivers nationwide or offers pickup at local Worten stores (e.g. Worten Marinha Grande)
    if "worten" in source_lower or "worten" in loc_lower:
        return {
            "travel_distance_km": 0.0,
            "travel_time_min": 0,
            "travel_label": "Worten Store / Entrega ao Domicílio",
            "travel_tier": "delivery",
            "matched_zone": "Worten Marinha Grande / Leiria",
            "shipping_label": "Envio Grátis / Loja Worten",
            "supports_shipping": 1,
            "shipping_cost_eur": 0.0
        }

    # PCDIGA: online warehouse delivery or pickup if not physically in stock at Leiria store
    if "pcdiga" in source_lower or "pcdiga" in loc_lower:
        if "em stock" not in loc_lower or "online" in loc_lower:
            return {
                "travel_distance_km": 0.0,
                "travel_time_min": 0,
                "travel_label": "PCDIGA Online (Entrega 24h / Loja)",
                "travel_tier": "delivery",
                "matched_zone": "PCDIGA Online",
                "shipping_label": "Envio 24h PCDiga (Garantia 3 Anos)",
                "supports_shipping": 1,
                "shipping_cost_eur": 0.0
            }

    # CeX: nationwide courier delivery with 5-year warranty if available online
    if "cex" in source_lower or "webuy" in loc_lower:
        if "leiria" not in loc_lower:
            return {
                "travel_distance_km": 0.0,
                "travel_time_min": 0,
                "travel_label": "CeX Envio Nacional (5 Anos Garantia)",
                "travel_tier": "delivery",
                "matched_zone": "CeX Portugal (Online)",
                "shipping_label": "Envio Nacional (5 Anos Garantia CeX)",
                "supports_shipping": 1,
                "shipping_cost_eur": 0.0
            }

    if not location_str:
        return {
            "travel_distance_km": 999.0,
            "travel_time_min": 999,
            "travel_label": "Localização não indicada",
            "travel_tier": "unknown",
            "matched_zone": "Unknown",
            "shipping_label": "Envio a Combinar",
            "supports_shipping": 1,
            "shipping_cost_eur": 5.90
        }

    # Match location against Portuguese locations dict
    matched_key: Optional[str] = None
    matched_coords: Optional[Tuple[float, float]] = None

    # Check exact substring match (longest matching key wins)
    for key, coords in sorted(PORTUGUESE_LOCATIONS.items(), key=lambda x: len(x[0]), reverse=True):
        if key in loc_lower:
            matched_key = key
            matched_coords = coords
            break

    if not matched_coords:
        # Default fallback if unknown parish
        return {
            "travel_distance_km": 120.0,
            "travel_time_min": 80,
            "travel_label": f"{location_str} (~1h 20m)",
            "travel_tier": "regional",
            "matched_zone": location_str,
            "shipping_label": "Envio CTT Expresso / Entregas OLX (~5.90€)" if "olx" in source_lower else "Envio CTT a Combinar",
            "supports_shipping": 1,
            "shipping_cost_eur": 5.90
        }

    # Compute road distance and drive time
    h_dist = haversine_distance(origin_coords, matched_coords)
    road_km = round(h_dist * 1.25, 1)

    if road_km <= 8.0:
        drive_mins = 5
        label = f"Local ({origin_name} / < 10 min)"
        tier = "local"
    elif road_km <= 35.0:
        drive_mins = max(10, round(road_km / 75.0 * 60))
        label = f"{int(road_km)} km ({drive_mins} min)"
        tier = "local"
    elif road_km <= 90.0:
        drive_mins = round(road_km / 90.0 * 60)
        h = drive_mins // 60
        m = drive_mins % 60
        time_str = f"{h}h {m:02d}m" if h > 0 else f"{m}m"
        label = f"{int(road_km)} km ({time_str})"
        tier = "regional"
    else:
        drive_mins = round(road_km / 100.0 * 60)
        h = drive_mins // 60
        m = drive_mins % 60
        label = f"{int(road_km)} km ({h}h {m:02d}m)"
        tier = "trip"

    # Shipping determination
    if "cex" in source_lower:
        if "leiria" in loc_lower:
            ship_label = "Loja CeX LeiriaShopping (Pronta Entrega)"
        else:
            ship_label = "Envio Nacional (5 Anos Garantia CeX)"
        ship_cost = 0.0
    elif "pcdiga" in source_lower:
        if "leiria" in loc_lower or "em stock" in loc_lower:
            ship_label = "Loja PCDiga Leiria (Stock Imediato)"
        else:
            ship_label = "Envio 24h PCDiga (Garantia 3 Anos)"
        ship_cost = 0.0
    elif "worten" in source_lower:
        ship_label = "Envio Grátis / Loja Worten"
        ship_cost = 0.0
    elif "olx" in source_lower:
        if road_km <= 20.0:
            ship_label = f"Recolha em Mão ({int(road_km)} km) ou Envio CTT"
        else:
            ship_label = "Envio CTT Expresso / Entregas OLX (~5.90€)"
        ship_cost = 5.90
    else: # Facebook or generic
        if road_km <= 20.0:
            ship_label = f"Recolha em Mão ({int(road_km)} km) ou CTT"
        else:
            ship_label = "Envio CTT a Combinar com Vendedor"
        ship_cost = 5.90

    return {
        "travel_distance_km": road_km,
        "travel_time_min": drive_mins,
        "travel_label": label,
        "travel_tier": tier,
        "matched_zone": matched_key.title() if matched_key else location_str,
        "shipping_label": ship_label,
        "supports_shipping": 1,
        "shipping_cost_eur": ship_cost
    }
