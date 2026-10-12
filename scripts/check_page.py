from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"])
    page = browser.new_page()
    errors = []
    page.on("pageerror", lambda err: errors.append(f"PAGEERROR: {err}"))
    page.on("console", lambda msg: errors.append(f"CONSOLE [{msg.type}]: {msg.text}") if msg.type in ["error", "warn"] else None)
    
    print("Navigating to http://localhost:5173 ...")
    page.goto("http://localhost:5173", wait_until="domcontentloaded", timeout=10000)
    time.sleep(3)
    
    print("Page title:", page.title())
    root_html = page.inner_html("#root")
    print(f"Root innerHTML length: {len(root_html)}")
    if len(root_html) < 200:
        print("Root HTML content:", root_html)
    else:
        print("Root HTML sample:", root_html[:200])
        
    print(f"Total errors/warnings: {len(errors)}")
    for e in errors:
        print("  ->", e)
        
    page.screenshot(path="scripts/screenshot.png")
    print("Screenshot saved to scripts/screenshot.png")
    browser.close()
