"""
src/browser_lock.py - Cross-process file lock for persistent Playwright profile.
Prevents Chromium SingletonLock conflicts between auto_messenger and sync_chats/negotiation_daemon.
"""

import fcntl
import asyncio
import time
import logging
from pathlib import Path

logger = logging.getLogger("browser_lock")


class BrowserLock:
    """
    Ensures safe, serialized access to the persistent Playwright browser profile directory
    across separate background processes.
    """
    def __init__(self, lockfile: str = None, timeout: int = 60):
        if lockfile is None:
            base_dir = Path(__file__).resolve().parent.parent
            lockfile = str(base_dir / "data" / "browser.lock")
        self.lockfile = lockfile
        self.timeout = timeout
        self.fd = None

    async def __aenter__(self):
        start = time.time()
        Path(self.lockfile).parent.mkdir(parents=True, exist_ok=True)
        self.fd = open(self.lockfile, "w")
        waited = False
        while True:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                if waited:
                    logger.info("🔓 Perfil do browser desbloqueado e adquirido com sucesso.")
                return self
            except (IOError, BlockingIOError):
                if not waited:
                    logger.info("⏳ Perfil do browser em utilização por outro processo. A aguardar libertação...")
                    waited = True
                elapsed = time.time() - start
                if elapsed > self.timeout:
                    logger.warning(f"⚠️ Timeout ao aguardar lock do browser ({self.timeout}s). A avançar...")
                    return self
                await asyncio.sleep(1.5)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.fd:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_UN)
                self.fd.close()
            except Exception:
                pass
