"""
backend/link_verifier.py - Real-time individual link verification engine for laptop listings.
Checks if second-hand ads (OLX, etc.) and store listings are still active or expired/sold.
"""

import urllib.request
import urllib.parse
import urllib.error
import socket
import logging
from typing import Tuple

logger = logging.getLogger("link_verifier")

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Common indicators across Portuguese e-commerce & classifieds that an item is no longer available
INACTIVE_SIGNALS = [
    "este anúncio já não está disponível",
    "este anúncio foi desativado",
    "anúncio desativado",
    "anúncio já não está disponível",
    "não encontramos o que procura",
    "anúncio não encontrado",
    "anúncio expirado",
    "anúncio removido",
    "página não encontrada",
    "artigo esgotado",
    "produto esgotado",
    "produto indisponível",
    "artigo indisponível",
    "este artigo já foi vendido",
    "anuncio-expirado",
    "offer-inactive",
    "item is no longer available",
    "listing has ended",
    "this listing is no longer active",
]

def verify_listing_active(url: str, source: str = "") -> Tuple[bool, str]:
    """
    Verifies if a specific listing URL is still online and active.
    Returns (is_active: bool, reason: str).
    Guarantees zero false-positive deletions for transient bot challenges or temporary network timeouts.
    """
    if not url or not url.strip():
        return False, "url_vazia"
    
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        return False, "url_invalida"
    
    source_lower = (source or "").lower()
    
    # Facebook Marketplace special case: unauthenticated HTTP requests are redirected to login
    # We do NOT mark Facebook listings as dead on login redirection
    if "facebook" in source_lower or "facebook.com" in url:
        return True, "facebook_requer_sessao"

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            final_url = resp.geturl()
            status_code = resp.status
            
            # Check if redirected away from the specific listing to the domain root or search page
            parsed_final = urllib.parse.urlparse(final_url)
            parsed_orig = urllib.parse.urlparse(url)
            
            # E.g. OLX redirected https://www.olx.pt/d/anuncio/... -> https://www.olx.pt/ or https://www.olx.pt/d/
            if parsed_final.path in ["", "/", "/d", "/d/", "/pt", "/pt/"] and parsed_orig.path not in ["", "/", "/d", "/d/"]:
                return False, "redirecionado_para_inicio"
            
            # Read first 100KB of content to detect deactivated message
            raw_content = resp.read(100000).decode("utf-8", errors="ignore").lower()
            
            for signal in INACTIVE_SIGNALS:
                if signal in raw_content:
                    return False, f"sinal_inativo:{signal}"
            
            return True, "ativo"
            
    except urllib.error.HTTPError as e:
        # Definite deletion codes
        if e.code in (404, 410):
            return False, f"http_{e.code}"
        
        # Bot challenge, Captcha or Rate Limit (403, 429, 503):
        # DO NOT delete valid laptops when blocked by cloudflare/rate limit!
        if e.code in (403, 429, 503):
            return True, f"preservado_anti_bot_{e.code}"
            
        # 500, 502, 504 could be temporary server glitch, preserve
        if e.code in (500, 502, 504):
            return True, f"preservado_servidor_{e.code}"
            
        return False, f"http_{e.code}"
        
    except (urllib.error.URLError, socket.timeout, TimeoutError):
        # Transient connection timeout: preserve to avoid false-positive mass deletions
        return True, "preservado_timeout_rede"
        
    except Exception as e:
        return True, f"preservado_excecao:{type(e).__name__}"
